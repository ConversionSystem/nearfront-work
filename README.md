# Nearfront Work

Your sandbox. Everything here goes live at **go.nearfront.com** about 30 seconds after you push, and none of it is visible to Google.

**Nothing you do in this repo can affect nearfront.com.**

## Make something

Tell Cowork what you want. It reads `CLAUDE.md` and follows the house rules. Push when you like it. That is the whole loop, and you never need anyone's approval.

## Two kinds of thing

- **A client proposal** goes to `proposals.nearfront.com/proposals/<client>/<topic>/`. Send that link to the client. It stays here permanently.
- **A marketing page that needs to rank on Google** gets built here first, then promoted (below). It only ranks once it is on nearfront.com.

Campaign landing pages for ads, email, or outreach do **not** need promoting. They work perfectly here, and being invisible to Google is usually what you want for a campaign page.

## Before building a marketing page, pick the URL

```bash
python3 scripts/validate.py --check-url /services/your-idea/
```

`FREE` means go ahead. `CLAIMED` means the old WordPress site already used that address, and a page there would be invisible: visitors get redirected away before the page is ever served. 222 addresses are taken, including obvious ones like `/contact-us/` and `/webinars/`.

Sixty seconds here saves rebuilding the page later.

## Check your work

```bash
python3 scripts/validate.py --profile work
```

Red must be fixed. Yellow is worth reading. Ask Cowork to fix anything red.

## Promote a page to nearfront.com

1. Look at it on go.nearfront.com. Happy with it?
2. Ask Cowork: *"promote /services/your-idea/ to production."* It copies the file into your fork of the main repo, adds the sitemap entry, adds the hub-page card and an internal link, runs the checks, and opens a pull request.
3. Steve reviews and merges. Live in about a minute, initially noindexed.
4. Steve turns on indexing once he is happy with it.

You cannot merge that pull request yourself. That is the safety net, not a bug: the main site carries the rankings and the lead form, and one bad file there takes it down.

## If something looks wrong on nearfront.com

Tell Steve. Do not try to fix production. A rollback takes him about ten seconds.
