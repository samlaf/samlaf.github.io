---
title:  Push Ifs Up To Get Rust To Auto-Vectorize
category: programming
---

In this article:
- We optimize a simple function to use memory pre-allocations and SIMD copying, by using Godbolt to look at generated assembly and control-flow-graph.
- We observe actual magic happening by [pushing ifs up and fors down](https://matklad.github.io/2023/11/15/push-ifs-up-and-fors-down.html).
    - if you haven't read this article, stop whatever you are doing and go read it first.
- We explore 2 reasons why Rust iterators are not zero-cost if you don't know what you are doing:
    - not using ExactSizeIterators leads to extra allocations
    - auto-vectorization won't happen... automatically :(


## Function to Optimize and Context

Woke up on saturday, thinking I was going to spend the next 30 minutes cleaning up this simple util [function](https://github.com/Layr-Labs/rust-kzg-bn254/blob/4ad14ea4ce9473e13ed6437140fcbbff3a8ccce1/src/helpers.rs#L70) in our [rust-kzg-bn254](https://github.com/Layr-Labs/rust-kzg-bn254) rust crate and then move on to better things:
```rust
const BYTES_PER_FIELD_ELEMENT: usize = 32;

pub fn remove_empty_byte_from_padded_bytes_unchecked(data: &[u8]) -> Vec<u8> {
    let data_size = data.len();
    let parse_size = BYTES_PER_FIELD_ELEMENT;
    let data_len = data_size.div_ceil(parse_size);

    let put_size = BYTES_PER_FIELD_ELEMENT - 1;
    let mut valid_data = vec![0u8; data_len * put_size];
    let mut valid_len = valid_data.len();

    for i in 0..data_len {
        let start = i * parse_size + 1; // Skip the first byte which is the empty byte
        let mut end = (i + 1) * parse_size;

        // ========= HOT-LOOP BRANCH ========
        if end > data_size {
            end = data_size;
            valid_len = i * put_size + end - start;
        }
        // ==================================

        // Calculate the end of the slice in the output vector
        let output_end = i * put_size + end - start;
        valid_data[i * put_size..output_end].copy_from_slice(&data[start..end]);
    }

    valid_data.truncate(valid_len);
    valid_data
}
```

It takes a slice of bytes, and removes the first byte of every 32-byte chunk. Its purpose is to decode a payload that was encoded as an array of bn254 field elements:
> `[0,1,2,...,31,0,33,...,63,0,65...,73] -> [1,2,...,31,33,...,63,65,...,73]`

Having read the rust book's section comparing [loops and iterators](https://doc.rust-lang.org/book/ch13-04-performance.html) and showing that rust iterators are a [zero-cost abstraction](https://without.boats/blog/zero-cost-abstractions/), I thought I was just going to have to rewrite it in functional form, which would it both cleaner and faster (because of the zero-cost abstraction):
```rust
pub fn remove_empty_byte_from_padded_bytes_unchecked_functional(input: &[u8]) -> Vec<u8> {
    let output: Vec<u8> = input
        .chunks(BYTES_PER_FIELD_ELEMENT)
        .flat_map(|chunk| &chunk[1..])  // Skip leading byte and flatten
        .copied()
        .collect();
    output
}
```

I smirked thinking back to Joe Armstrong's famous quote:
> "Make it work, then make it beautiful, then if you really, really have to, make it fast. 90% of the time, if you make it beautiful, it will already be fast. So really, just make it beautiful!"

Afterall, code typically doesn't get more beautiful than its functional form. And rust was supposed to give me the fast for free as long as I make it beautiful. This had taken me all of 10 minutes so I had a bit of extra time to do what every good engineer should do: benchmark. Even Joe Armstrong would agree that the only real source of truth is CPU time. An hour later (had to learn Criterion...), I realized my functional code is actually 3x slower. What?!

## Cost of the clean functional form

By putting this function in [godbolt](https://godbolt.org/) and looking at the assembly, we can see that it copies one byte at a time:
```armasm
.LBB2_11:                               # Main byte copying loop
        strb    w27, [x0, x21]          # Store byte (w27) to output buffer at offset x21
        add     x21, x21, #1            # Increment output buffer index
        str     x21, [sp, #16]          # Save updated index to stack

.LBB2_12:                               # Chunk boundary check
        cmp     x26, x20                # Compare current input position with chunk end
        b.ne    .LBB2_17                # If not at chunk end, continue copying
.LBB2_17:                               # Byte loading and buffer check
        ldr     x8, [sp]                # Load output buffer size
        ldrb    w27, [x26], #1          # Load next byte and increment input position
        cmp     x21, x8                 # Check if output buffer is full
        b.ne    .LBB2_11                # If not full, continue copying
```

The reasons for this are still not super clear to me. We look at some reasons in a section [below](#Fast-functional-form). But first, it makes more sense to get back to the original function and optimize it gradually, one thing at a time, to understand which features of the code are slowing it down.


## Moving the If outside of the For

One problem with the original function that jumped to my eyes is the if statement inside of the for loop. It goes against matklad's "[push ifs up and fors down](https://matklad.github.io/2023/11/15/push-ifs-up-and-fors-down.html)" aphorism. Now, any human looking at the code can easily see that the branch condition `if end > data_size` only evaluated to true at the very last index of the loop only. So clearly, either the compiler could optimize it away, and if not, then at least modern cpu branch prediction would eat this for breakfast. Right? Right?? Turns out that's not the case. Compilers are still dumb, and [even predictable branches can increase branch mispredictions](https://lemire.me/blog/2019/11/06/adding-a-predictable-branch-to-existing-code-can-increase-branch-mispredictions/). This is also why getting the compiler to [optimize away bound checks](https://nnethercote.github.io/perf-book/bounds-checks.html), or even in certain cases writing unsafe rust when the compiler won't comply, can be very useful.

Here is the optimized version.
```rust
pub fn remove_empty_byte_from_padded_bytes_unchecked_fast(data: &[u8]) -> Vec<u8> {
    let num_fes = data.len() / BYTES_PER_FIELD_ELEMENT;
    let trailing_bytes = if data.len() % BYTES_PER_FIELD_ELEMENT == 0 {
        0
    } else {
        data.len() % BYTES_PER_FIELD_ELEMENT - 1
    };

    let output_chunk_len = BYTES_PER_FIELD_ELEMENT - 1;
    let output_len = num_fes * (BYTES_PER_FIELD_ELEMENT - 1) + trailing_bytes;
    let mut output = vec![0u8; output_len];

    for i in 0..num_fes {
        output[i * output_chunk_len..(i + 1) * output_chunk_len].copy_from_slice(
            &data[i * BYTES_PER_FIELD_ELEMENT + 1..(i + 1) * BYTES_PER_FIELD_ELEMENT],
        );
    }
    // ========== STANDALONE BRANCH ==========
    if trailing_bytes > 0 {
        output[num_fes * output_chunk_len..]
            .copy_from_slice(&data[num_fes * BYTES_PER_FIELD_ELEMENT + 1..]);
    }
    // =======================================
    output
}
```

And here are the benchmark results, also including the functional form
```
remove_empty_byte: 7.2250 µs
remove_empty_byte_fast: 982.93 ns
remove_empty_byte_functional: 27.222 µs
```
So we see a ~7x speedup by moving the branch outside of the for loop! But also surprisingly, the functional form is ~27x slower than the fast version.

## Fast functional form

Applying the learnings we made above, we can massage the functional form to achieve similar speeds! Perhaps "zero-cost abstraction iterators" should be renamed to the more appropriate "zero-cost abstraction iterators, as long as you know what you're doing and don't write the code you would want to write." 

The below function is what I ended up submitting in my [PR](https://github.com/Layr-Labs/rust-kzg-bn254/pull/41).
```rust
pub fn remove_empty_byte_from_padded_bytes_unchecked(data: &[u8]) -> Vec<u8> {
    // pre-allocate vec capacity
    let empty_bytes_to_remove = data.len().div_ceil(BYTES_PER_FIELD_ELEMENT);
    let mut output = Vec::with_capacity(data.len() - empty_bytes_to_remove);
    
    // main loop with equal sized elements to generate SIMD instructions
    for chunk in data.chunks_exact(BYTES_PER_FIELD_ELEMENT) {
        output.extend_from_slice(&chunk[1..]);
    }
    
    // process remainder
    let remainder = data.chunks_exact(BYTES_PER_FIELD_ELEMENT).remainder();
    if !remainder.is_empty() {
        output.extend_from_slice(&remainder[1..]);
    }
    
    output
}
```

There are 2 problems with the original functional function:
1. `collect()` doesn't pre-allocate a vector of the right capacity, which leads to extraneous copies
2. the bytes are copied one at a time, which doesn't make use of modern hardware features

We fixed those by:
1. pre-allocating the correct sized vector instead of using `collect()`
1. use `chunks_exact()` instead of `chunks()` in order to allow the main loop to auto-vectorize and use SIMD instructions to copy 128 (or more) bytes at a time

### SIMD Assembly Output
For completion, we can put the function in [godbolt](https://godbolt.org/) and observed the optimized assembly output for the SIMD copying. The control flow graph shows the main copying loop between`.LBB2_7` and `.LBB2_6`.
![image](/assets/push-ifs-up-to-trigger-auto-vectorization/assembly-loop.png)

And here's the LLM annotated output, clearly showing the [stur and str](https://developer.arm.com/documentation/dui0801/g/A64-Floating-point-Instructions/STUR--SIMD-and-FP-) (store (unscaled) register) SIMD copying.
```armasm
stur    q0, [x8, #15]     # Store with unaligned offset of 15
str     q1, [x8]          # Store with aligned offset (implicit 0)
```
The q prefix indicates the use of NEON 128-bit registers. The stur (u for unaligned) with offset #15 is because we're storing data with a 1-byte shift to remove the empty byte. This offset isn't aligned to the 16-byte boundaries that SIMD usually requires.

```armasm
.LBB2_6:  # Main loop processing 32-byte chunks
    ldur    q0, [x23, #15]    # Load 16 bytes starting at x23+15 into q0
    ldr     q1, [x23], #32    # Load 16 bytes from x23 into q1, then increment x23 by 32
    add     x8, x0, x1        # Calculate destination address (base + offset)
    add     x1, x1, #31       # Increment offset by 31 (31 bytes per chunk after removing leading byte)
    adds    x21, x21, #32     # Add 32 to counter and update flags
    stur    q0, [x8, #15]     # Store 16 bytes from q0 to destination+15 
    str     q1, [x8]          # Store 16 bytes from q1 to destination
    str     x1, [sp, #24]     # Store updated offset to stack
    b.eq    .LBB2_10          # If counter reached target, branch to end processing

.LBB2_7:  # Capacity check and reallocation
    ldr     x8, [sp, #8]      # Load current capacity
    sub     x8, x8, x1        # Calculate remaining space
    cmp     x8, #30           # Check if we have space for another chunk
    b.hi    .LBB2_6           # If enough space, continue main loop
    add     x0, sp, #8        # Prepare args for reserve
    mov     w2, #31           # Amount to reserve
    bl      alloc::raw_vec::RawVec<T,A>::reserve::do_reserve_and_handle # Call reallocation
    ldp     x0, x1, [sp, #16] # Reload base and offset after reallocation
    b       .LBB2_6           # Return to main loop

.LBB2_10:  # Remainder processing
    cbz     x24, .LBB2_15     # If no remainder (x24 = 0), skip to end
    ldr     x8, [sp, #8]      # Load current capacity 
    sub     x21, x24, #1      # Calculate remainder size - 1
    sub     x8, x8, x1        # Calculate remaining space
    cmp     x8, x21           # Check if we have enough space for remainder
    b.hs    .LBB2_14          # If enough space, process remainder
    add     x0, sp, #8        # Prepare args for reserve
    mov     x2, x21           # Amount to reserve
    bl      alloc::raw_vec::RawVec<T,A>::reserve::do_reserve_and_handle # Call reallocation
    ldp     x0, x1, [sp, #16] # Reload base and offset after reallocation
```