---
title:  "What a terminal emulator actually is"
category: programming
---

[Your terminal has been editing everything you
type](/programming/your-terminal-has-been-editing-everything-you-type.html)
stayed below the fd — inside the kernel, between your program's `read()` and
the tty device — and ended on the question the kernel can't answer: *what can
the thing on the far end of the wire draw, and which bytes drive it?* This
post crosses the wire.

The far end is the terminal emulator — Ghostty, iTerm2, xterm — and it is both
the most visible program on your desktop and the least understood. Start with
what it is *not*. The emulator has no concept of a line of input, a command,
or a shell. Everything you think of as "the terminal being helpful" — echo,
backspace, line editing, Ctrl-C — is the kernel's line discipline or the
application. The emulator knows three things: cells, a cursor, and a byte
protocol.

## It used to be hardware

The word *emulator* is literal. A VT100 was a physical object: a keyboard, a
CRT, and firmware that turned an incoming byte stream into glowing phosphor
and keystrokes into an outgoing byte stream, connected to the computer by a
serial wire. The kernel's tty subsystem was written to talk to that object.

![the terminal migrates from silicon to kernel to userspace](/assets/tty-series/what-a-terminal-emulator-actually-is/history.svg)

The terminal then migrated inward twice. First into the kernel: when machines
grew their own screens, the "terminal" became kernel code driving the video
card — the virtual console you can still visit at Ctrl-Alt-F2. Then out into
userspace: under a windowing system, the terminal is an ordinary GUI program
holding the master end of a pty. That's why old diagrams draw the terminal
inside the kernel and new ones don't — the box moved, and the pty exists
precisely so that everything below it couldn't tell. (The relocation story is
told at length in Linus Åkesson's
[The TTY demystified](https://www.linusakesson.net/programming/tty/).)

## A bidirectional codec

Here is the most precise one-sentence definition I can manage:

> A terminal emulator owns the master end of a pty and implements ECMA-48 in
> both directions: it encodes input events into bytes going in, and interprets
> bytes coming out as a control-sequence language that mutates a
> character-cell grid it renders.

Two independent halves sharing one fd. An **encoder** turning keyboard, mouse
and paste events into escape-encoded bytes; an **interpreter** turning bytes
into grid mutations. Nothing loops directly from input to output — that path
runs through the application, or through the kernel's line discipline when
echo is on. When you see your own typing, the emulator drew it twice removed:
it sent the byte in, the line discipline reflected it back, and the
interpreter half treated the reflection like any other program output.

(ECMA-48 is the standard everyone calls "ANSI escape codes" — it, ANSI X3.64
and ISO 6429 are the same document. Real emulators implement it plus a thick
layer of DEC and xterm extensions; more on that below.)

## The input half: an encoder

The encoder is the smaller half — it's the place where your Return key
becomes `\r`. Keys that are printable characters go in as
themselves; everything else gets an escape encoding, and the encoding is
negotiated. Press the up arrow and the emulator writes `\x1b[A` — unless the
application has switched the terminal into DECCKM "application cursor keys"
mode, in which case the same key sends `\x1bOA`. The application asks for the
encoding it wants; the emulator obliges. Mouse clicks, paste events and focus
changes work the same way: off by default, switched on by the application,
delivered as escape sequences interleaved with the keystrokes.

That interleaving matters. There is one input stream, so a program in raw mode
reads keystrokes, mouse reports and paste bursts all as bytes on the same fd,
and has to parse them apart itself.

## The output half: a parser and a screen model

The output half is where the real work is, and it has two parts.

The first is a **state machine**. Escape sequences arrive interleaved with
text, possibly split across `read()` boundaries, possibly malformed. Every
serious emulator implements something equivalent to Paul Williams'
reverse-engineered [VT500 parser](https://vt100.net/emu/dec_ansi_parser) — a
small automaton with states like *ground*, *escape*, *csi-entry* — that
consumes one byte at a time and emits actions: print this glyph, execute this
control, dispatch this completed sequence.

The second is the **screen model** those actions mutate: a grid of cells, each
holding a character plus attributes — foreground and background color across
three color spaces, bold, italic, underline style and color, strikethrough —
plus a cursor position and a saved cursor, scroll regions, tab stops, a
scrollback ring, and a complete *alternate* screen buffer. The alternate
screen is why vim can take over your whole window and your prompt is still
there when you quit: `:q` doesn't redraw your shell, it switches back to the
buffer that never changed.

Rendering the model to pixels — fonts, ligatures, GPU pipelines — is where
emulators compete, but it's downstream of the protocol. Two emulators that
disagree about pixels still agree about the grid.

## The control plane is in-band

Now the strangest design fact in the whole system, and the most consequential:
**the emulator's program-facing API is in-band.** Control is multiplexed into
the data stream. There is no syscall, no side channel, no capability
negotiation — a program configures the emulator by *printing at it*, and
queries it by printing a question and reading the answer back off its own
input, interleaved with the user's typing.

Compare how configuration reaches each layer of the stack:

| Layer | Control API | What it configures | In-band? |
|---|---|---|---|
| emulator — local | its own config file | font, colors, scrollback depth, the `TERM` it advertises | out-of-band |
| emulator — from the program | **escape sequences in the data stream**: DECSET (`CSI ? Pm h/l`), `OSC`, `DCS` | alt screen (`?1049`), bracketed paste (`?2004`), mouse reporting (`?1006`), cursor visibility (`?25`), synchronized output (`?2026`), kitty keyboard, window title (`OSC 0/2`), clipboard (`OSC 52`), hyperlinks (`OSC 8`), palette (`OSC 4/10/11`), graphics (sixel, kitty) | **in-band** |
| pty + line discipline | `ioctl(2)` on either fd | the whole `termios` struct; window size (`TIOCSWINSZ`); controlling tty; foreground process group; the line-discipline slot itself | out-of-band — never bytes |
| the program | terminfo lookup + syscalls | reads `$TERM`, picks escape bytes; `tcsetattr` for cbreak/raw; `SIGWINCH` handler | out-of-band |

The second row is the interesting one. Those `?`-prefixed numbers are **DEC
private modes** — the extension namespace ECMA-48 reserved for vendors, where
essentially all of the modern terminal lives: the alternate screen, mouse
reporting, bracketed paste, none of it is in the standard. And the queries go
the same way: send `DA1` ("who are you?") or `OSC 11 ?` ("what's your
background color?") down the output stream, and the reply arrives on the
*input* stream, where your parser must fish it out from between keystrokes.

The third row is the only true out-of-band channel, and window size is its
best example. The emulator knows how many rows and columns it has; the
application needs to know too, and the number changes when the user drags a
corner. So the emulator sets it with an ioctl on the master (`TIOCSWINSZ`),
the kernel stores it and raises `SIGWINCH` at the foreground process group,
and the application reads it back with an ioctl of its own. Deliberately left
out of POSIX for decades as windowing-system business, standardized at last in
POSIX.1-2024 as `tcgetwinsize()`/`tcsetwinsize()` — some fifty years after
terminals started having sizes.

## terminfo: the third question

The tty post left a ladder of questions dangling. `isatty(fd)` asks *is this a
terminal at all?* — the kernel answers. termios asks *how does the kernel
process bytes on this channel?* — live kernel state, per fd. The third
question — *what can a terminal of type X draw, and which escape bytes drive
it?* — is answered by neither, because the kernel never interprets the
payload. It's answered by a **static userspace database**: terminfo (the
modern form of termcap).

The protocol is decades of accreted dialects — support for any given DEC
private mode or OSC varies by emulator — so the emulator advertises a name in
`$TERM`, and programs look that name up: `tput smcup` at the shell,
`tigetstr("smcup")` from C, ncurses doing it wholesale underneath. Three
layers, three tools, one rule of thumb: `isatty` for *whether*, termios for
*how the kernel behaves*, terminfo for *what the far end understands*.

## Aside: ssh, or two of everything

One consequence of the emulator being an ordinary userspace program holding a
master fd: anything else can play that role too. `sshd` does. On the remote
host it allocates a pty, runs your shell on the slave, and holds the master
itself — the same seat a terminal emulator occupies locally. So an ssh session
has *two* ptys and two line disciplines:

```
your emulator → local pty → ssh → TCP → sshd → remote pty → remote shell
                raw mode                        cooked mode
```

ssh puts your *local* tty in raw mode precisely so the *remote* line
discipline does the echo and line editing — there must be exactly one cook.
That's why backspace feels laggy on a slow link: the character you erased made
a round trip before the screen changed. tmux and screen are the same trick
one layer deeper — a master-holder that multiplexes several ptys behind one.

## Aside: so where is the shell?

Conspicuously missing from this post — and the omission is the lesson. The
emulator knows cells and bytes but nothing about commands; the shell knows
commands but nothing about cells. Neither ever talks to the other. Each one
talks to the kernel device between them, from opposite sides.

In its plainest form the shell is just a canonical-mode client of that
device: it calls `read()`, receives a line the kernel assembled, runs it.
Everything that feels like "the terminal helping you" at such a prompt —
echo, backspace, `Ctrl-C` — is the line discipline's work. Modern
interactive shells refuse the kernel's help: bash links readline, zsh has
zle, fish rolls its own, and the first thing each does at a prompt is clear
`ICANON` and `ECHO`, switching the kernel's editor off to rebuild it in
userspace with history, completion and highlighting on top — the "who cooks"
diagram in [the tty
post](/programming/your-terminal-has-been-editing-everything-you-type.html)
is exactly this move. Full-screen programs take one more step with curses:
near-raw mode on the kernel's control plane *and* the alternate screen on
the emulator's. That ladder — canonical client, readline, curses — is where
[Why the byte stream won't
die](/programming/why-the-byte-stream-wont-die.html) picks up: you can
classify every terminal program by which control planes it seizes.

## The shape of the thing

So: a byte-stream codec with a state machine on one side, an encoder on the
other, and its entire API multiplexed into its own data. By any modern
standard this is a strange design — in-band control, undiscoverable
capabilities, a static database standing in for feature negotiation. [Why the
byte stream won't die](/programming/why-the-byte-stream-wont-die.html) takes
up the obvious question: why hasn't something better replaced it? The answer
turns out to be the best defense of the byte stream anyone has written, and
nobody wrote it on purpose.

## Try it

The last four [tty-puzzles](https://github.com/samlaf/tty-puzzles) puzzles
cross to this side of the fd: decoding escape sequences, the lone-`ESC`
ambiguity, the alternate screen, and finally a working prompt built on nothing
but what you wrote.

## Further reading

- Martin Balao, [How terminal emulators work on Linux](https://martin.uy/blog/how-terminal-emulators-work-on-linux/index.html) —
  the emulator's event loop, from X events to pty bytes.
- [Terminals, ptys and pyte](https://cefboud.com/posts/terminals-pty-tty-pyte/) —
  drive a pty yourself and let pyte, a Python screen model, interpret the
  output: the two halves of this post as runnable code.
- Orel Fichman, [Terminal escape codes are awesome](https://orelfichman.com/blog/terminal-escape-codes-are-awesome/) —
  a guided tour of what the control-sequence language can actually do.
- Paul Williams' [VT500-series parser](https://vt100.net/emu/dec_ansi_parser) —
  the state machine itself, reverse-engineered from the hardware.
