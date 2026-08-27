# Setup

You need this once, and only if you want to publish from your own machine. If
you are happy letting Cowork do it, skip to [Where files go](#where-files-go),
which is the part that actually bites people.

## The short version

A working machine has three things: a local clone, an **SSH** remote, and an
SSH key registered with your GitHub account. No `gh` CLI, no tokens, no
Cloudflare credentials. There are deliberately no deploy credentials in this
repo, see `CLAUDE.md`.

## 1. Clone it

```bash
git clone git@github.com:ConversionSystem/nearfront-work.git
```

Use that SSH address, not the `https://` one. HTTPS needs a password or token
every time, and an agent running `git push` for you cannot type one.

## 2. If the push fails

**Check this one first.** If the push dies with a git proxy message rather than
a git error:

```
access denied by the git proxy: ConversionSystem/nearfront-work is not in
this session's authorized repository set
```

then git and your credentials are fine and the agent session itself is the
thing blocking you. The session keeps an allowlist of repositories it may push
to, and this repo is not on it. Add it in your own Claude settings, under the
session's authorized repositories or sources. Nobody else can grant this for
you: it is not a GitHub permission, not a setting in this repo, and not
something another person's session can change on your behalf. The commit is
already safe on your machine, so once the repo is allowed, push again and
nothing needs rebuilding.

This bit us for weeks. The web uploader looked like the only way to get a file
into GitHub, when the actual blocker was one allowlist entry.

### Credential problems

This different error means the remote is HTTPS and there is no credential
behind it:

```
fatal: could not read Username for 'https://github.com'
```

Point the remote at SSH instead:

```bash
git remote set-url origin git@github.com:ConversionSystem/nearfront-work.git
```

Then confirm GitHub knows you:

```bash
ssh -T git@github.com
```

You want `Hi <your-username>! You've successfully authenticated`. If you get
`Permission denied`, you have no key on this machine or it is not on your
GitHub account. `ssh-keygen -t ed25519` makes one. Adding the **public** half
to github.com/settings/keys is something you do yourself in your own account.
Never paste a private key anywhere, and never hand one to an agent.

## Where files go

**Cloudflare Pages serves `public/` and nothing else.** A file anywhere else is
invisible on the web.

| What it is | Where it goes | URL |
|---|---|---|
| Marketing draft | `public/<production path>/index.html` | mirrors nearfront.com |
| Client proposal | `public/proposals/<client>/<topic>/index.html` | `/proposals/...` |
| Client report | `public/reports/<slug>/index.html` | `/reports/...` |

Reports and proposals are self contained: inline `<style>`, no shared CSS, no
canonical, no Open Graph. `validate.py` knows this and applies a reduced
contract to those two paths. Put a report anywhere else and it gets judged as a
marketing page, which it will fail.

They must also carry **no GTM container**. That is not just unnecessary, it is
an error (`reports-no-analytics`): client work stays out of Nearfront
analytics, the same rule the client dashboards follow.

Pages must be `<path>/index.html`. A flat `something.html` is an error, because
it produces an ugly URL and bypasses the clean-URL convention.

## Check before you push

```bash
python3 scripts/validate.py --profile work
```

Red must be fixed. `--profile work` matters: without it the validator applies
the production site rules and reports failures that do not apply here.

To check a URL is not already claimed by one of the 755 legacy redirects:

```bash
python3 scripts/validate.py --check-url /services/your-slug/
```

## What happens after you push

Cloudflare builds from Git, live in about 30 seconds. GitHub Actions runs the
same validator you just ran. That job is validate only and holds no secrets, so
do not add a deploy step or a Cloudflare token to it.

## Do not use the GitHub web uploader

Dragging a file into github.com puts it wherever you are browsing, which is
usually the repository root. Root is not served, so the page is unreachable.

Nothing tells you. GitHub accepts the upload, the commit lands, Cloudflare
builds green, and the URL 404s. Two client reports sat unreachable this way,
one of them for a week, and the validator called the repo clean the whole time
because it only ever scanned `public/`.

There is now a `stray-root-html` check that errors on any HTML outside
`public/`, and CI runs it on every push, so this specific mistake cannot repeat
silently. Cloning and pushing is still the better path.
