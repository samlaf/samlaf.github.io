---
title:  "Why the byte stream won't die"
category: programming
---

[What a terminal emulator actually
is](/programming/what-a-terminal-emulator-actually-is.html) ended by
calling the terminal's design strange, by any modern standard: control
multiplexed in-band with data, capabilities you discover from a static
database instead of negotiating, a protocol accreted over fifty years of
vendor dialects. Strange designs usually get replaced. This one keeps burying
its replacements. This post is about why — and the answer is not nostalgia.

## Two kinds of program on the stack

First, be precise about what runs on this thing. The two posts before this
one mapped the two control planes: termios ioctls on the kernel side, escape
sequences on the emulator side. Programs sort by which planes they touch.

A **shell** touches almost neither. It's a line-oriented client of the cooked
line discipline — it reads lines the kernel assembled, forks things, and gets
its editing, echo and Ctrl-C as kernel services. (A modern shell with
readline-style editing takes back the input plane, as [the tty
post](/programming/your-terminal-has-been-editing-everything-you-type.html)
showed — but it still lives in lines and leaves the screen alone.)

A **TUI** — vim, htop, [gh-dash](https://github.com/dlvhdr/gh-dash) —
seizes both planes at once. Kernel side: cbreak or raw via `tcsetattr`, taking
byte-level ownership of input. Emulator side: alternate screen, cursor
addressing, mouse reporting, colors — taking ownership of the grid. That's the
whole distinction. A TUI is a program that fires both control planes and takes
over the screen model.

And TUIs are having a renaissance —
[Textualize](https://www.textualize.io/) in Python,
[Charm](https://charm.land/) in Go, ratatui in Rust. Their stacks look
different for about two layers, and then:

![every TUI framework bottoms out in the same substrate](/assets/why-the-byte-stream-wont-die/tui-stacks.svg)

Every framework, in every language, bottoms out in the same three things:
the escape-byte protocol, termios, and `SIGWINCH`. Nobody is required to do
this. Everybody does.

## The thought experiment

Because — why bytes? A TUI is a GUI drawn with characters. If you were
designing today you'd give the shell a real API: typed events in, draw calls
out, no parser, no in-band control, no `\x1b[`. Put the two designs side by
side:

![the terminal substrate vs the GUI substrate](/assets/why-the-byte-stream-wont-die/two-substrates.svg)

The right column is *obviously* better engineering. Typed instead of stringly,
discoverable instead of database-mediated, no state machine reverse-engineered
from a 1987 video terminal. People have built it, repeatedly, for forty years.
It keeps losing. The reasons are in the middle boxes.

## The middle box is load-bearing

The byte stream isn't just an aging wire format; it's doing enormous
structural work.

Because the contract is *bytes over a pty*, the shell and the renderer are
decoupled processes talking over a wire format. The shell links no toolkit
and cannot tell whether its bytes go to Ghostty, xterm, tmux, an SSH session,
or a serial console. And a byte stream survives things an API call cannot:

- it **tunnels over ssh** transparently — the remote side just needs a pty
  (the two-pty diagram in [the emulator
  post](/programming/what-a-terminal-emulator-actually-is.html) is the
  entire implementation);
- it gets **multiplexed and persisted** by tmux, which can sit in the middle
  precisely because the middle is just bytes;
- it gets **recorded** by `script` and asciinema, **piped**, **redirected**,
  and **diffed**, because a session and a file have the same type.

The GUI column's contract is an in-process function-call API. It couples the
shell to one toolkit on one machine, and running it remotely needs a
heavyweight remoting layer — X forwarding, RDP, waypipe — that the byte
stream gives you for free, by being nothing.

## The catch that actually sinks it

Suppose you accept the coupling and build the GUI shell anyway. Here's the
trap, and it's fatal: the moment your beautiful typed-API shell needs to run
`vim`, `htop`, or `ssh`, it must host programs that speak the byte protocol —
they want a tty in raw mode and a cell grid to draw on. So your GUI shell
**embeds a terminal emulator anyway**, and now you maintain both worlds and
all their seams.

You cannot escape the protocol while you still have to host the installed
base that was written against it. The byte stream is a [Schelling
point](https://en.wikipedia.org/wiki/Focal_point_(game_theory)): everyone
targets it because everyone targets it. That's not an argument that it's
good. It's an argument that it's *load-bearing*, which is a different and
much more durable property.

## Three ways people try anyway

The escape attempts sort into three strategies, by how much of the contract
they keep:

1. **Incremental** — [Ghostty](https://ghostty.org/) and
   [kitty](https://sw.kovidgoyal.net/kitty/): superb native emulators that
   *extend the protocol's vocabulary* — real graphics, an unambiguous
   keyboard encoding, synchronized output — without breaking it. Everything
   still works; new capabilities degrade gracefully through terminfo-style
   detection. This strategy is winning.
2. **Pragmatic overlay** — [Warp](https://www.warp.dev/): a GPU-rendered GUI
   that wraps command-and-output "blocks," a code-editor input box, and menus
   *around* a pty that still runs an ordinary shell speaking ordinary bytes
   underneath. GUI affordances bolted onto the legacy contract, which stays
   intact one layer down.
3. **Radical** — [Arcan](https://arcan-fe.com/) and its Cat9 shell (and,
   historically, Plan 9): actually replace the contract with typed IPC, and
   relegate the byte protocol to a compatibility target. This is the only
   strategy that builds the right-hand column for real — and it's the one
   that stays niche, precisely because abandoning the contract means
   abandoning the ecosystem until the compatibility bridge is perfect. And a
   perfect bridge is a terminal emulator, which is the thing you were trying
   to leave.

There's a fourth, quieter front: replace the *shell* and keep the wire.
[nushell](https://www.nushell.sh/) pipes typed tables between commands,
xonsh embeds Python — real redesigns of the language, running contentedly
over the same pty. Matklad's ["a better
shell"](https://matklad.github.io/2019/11/16/a-better-shell.html) sketches
how much room there is on this front alone (and his
[abont](https://github.com/matklad/abont) design goes further, unifying
shell, terminal and editor around annotated text). The wire, notably, is not
what anyone is trying to fix.

## Where this leaves us

These posts opened with `Ctrl-V Enter` printing a `^M` at a prompt.
The claim assembled since: your terminal is a kernel byte-editor whose
services are flags with precise names ([the tty
post](/programming/your-terminal-has-been-editing-everything-you-type.html))
— each one yours to switch off and rebuild in userspace
([tty-puzzles](https://github.com/samlaf/tty-puzzles)) — talking to a
userspace codec that turns a protocol into a grid ([the emulator
post](/programming/what-a-terminal-emulator-actually-is.html)). Every part
of it can be switched off, rebuilt, or replaced — except the byte stream in
the middle, which turns out to be the one piece everyone renews their vows
with, because a wire format that decouples everything from everything is
worth more than any improvement that couples something to something.

The terminal isn't here because nobody tried to do better. It's here because
"better" keeps turning out to mean a nicer box, and the terminal was never
the box. It's the wire.

## Further reading

- Alcides Fonseca, [Why TUIs are back](https://wiki.alcidesfonseca.com/blog/why-tuis-are-back/) —
  the renaissance argument made directly.
- [TUIs are easy now](https://hatchet.run/blog/tuis-are-easy-now) and
  [Adventures in TUIs](https://mattorb.com/adventures-in-tuis/) — two
  practitioners' reports from the framework layer.
- Přemysl Janouch, [Writing TUIs](https://p.janouch.name/article-tui.html) —
  the substrate's sharp edges, from someone who built on it anyway.
- [A complete guide to TUIs](https://gist.github.com/MangaD/cd8b8ab9b4f119ac5214fa4f3424ccd7) —
  an encyclopedic gist: history, architecture, and the framework landscape.
- [Rendering engines: Claude Code vs. Super Mario 64](https://spader.zone/engine/) —
  what the byte-stream substrate costs a modern TUI in raw instructions.
- [If OpenSSL were a GUI](https://news.ycombinator.com/item?id=31697636) —
  the mirror-image discussion: what CLI tools would look like as windows.
- [gcloud beta interactive](https://docs.cloud.google.com/sdk/gcloud/reference/beta/interactive) —
  a mainstream CLI quietly growing TUI affordances, strategy 2 in miniature.
