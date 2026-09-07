# code

Submodules for the runnable code behind posts on the site.

Each directory is a standalone repo, cloned here so that prose and code can be
read side by side while drafting. Directories are named after the upstream repo
rather than the post slug, since one repo can back a whole series.

| Directory          | Repo                                         | Used by                                       |
| ------------------ | -------------------------------------------- | --------------------------------------------- |
| `tty-puzzles`      | <https://github.com/samlaf/tty-puzzles>      | the terminal post and the `tty-series` drafts |
| `rust-cuda-aes`    | <https://github.com/samlaf/rust-cuda-aes>    | the single-core AES post                      |
| `koopman-examples` | <https://github.com/samlaf/koopman-examples> | the applied Koopman theory post               |
| `tiny-vmms`        | <https://github.com/samlaf/tiny-vmms>        | the tiny KVM VMM draft                        |

Jekyll excludes this whole directory, so nothing here reaches `_site`. Posts
link to GitHub instead, via front matter that `_layouts/post.html` renders next
to the date:

```yaml
code_url: https://github.com/samlaf/rust-cuda-aes
```

Run `make code` to clone or update every submodule.
