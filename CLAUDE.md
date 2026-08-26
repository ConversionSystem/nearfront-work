# CLAUDE.md

Guidance for Claude Code / Claude Cowork working in this repository.

## What this is

**The work lane for Nearfront.** Two kinds of page live here:

1. **Client proposals** at `public/proposals/<client>/<topic>/index.html`. Sent to clients and prospects. Self-contained. Never promoted anywhere.
2. **Marketing drafts** at the **exact path the page will occupy on nearfront.com**, so promoting is a file copy with no edits.

Served at **lp.nearfront.com** (Cloudflare Pages project `nearfront-work`, native Git integration, no build step). Proposals and landing pages both live on this host; the path tells them apart.

**Every page on this host is noindexed, and this host can never publish to nearfront.com.** There are no deploy credentials in this repo by design.

## Deploy

Push to `main`, Cloudflare builds from Git, live in about 30 seconds. Every branch also gets a preview at `https://<branch>.nearfront-work.pages.dev/`.

**Do not add a GitHub Actions deploy workflow and do not add any Cloudflare secret here.** A Cloudflare Pages token is account-scoped and could deploy over the production site. Keeping this repo credential-free is what makes autonomous publishing safe.

## The noindex contract, do not "fix" it

- `public/_headers` sets `X-Robots-Tag: noindex, nofollow` on `/*`. Do not remove, narrow, or reorder it.
- `public/robots.txt` says `Allow: /` **on purpose**. **Never add `Disallow: /`.** Blocking the crawl does not deindex: it stops Google fetching the page, so Google never reads the noindex, and URLs found via links get indexed URL-only. That failure is already open in Search Console for nearfront.com.
- Every page also carries `<meta name="robots" content="noindex,nofollow">`.
- There is no `sitemap.xml` here and there must not be one.

## Building a marketing draft

1. **Check the URL first.** `reference/_redirects` is a read-only copy of production's 755 legacy 301s. Cloudflare applies them before serving files, so a page at a claimed URL is unreachable in production. 222 top-level slugs are taken, including `/contact-us/`, `/webinars/`, and `/google-maps-pack/`.
   ```bash
   python3 scripts/validate.py --check-url /services/your-slug/
   ```
   Refresh the copy first if it looks stale (`reference/REFRESH.md`).
2. Create `public/<exact production path>/index.html` from `templates/landing-page.html` and replace every `{{TOKEN}}`.
3. The canonical is the **production** URL (`https://nearfront.com/<path>/`), not a work URL. That is deliberate: it makes promotion a zero-edit copy, and on a noindexed host it consolidates to the real domain.
4. Keep `/assets/site.css?v=4` and `/assets/site.js?v=4` root-relative. This repo carries its own copy of both.
5. Validate before pushing:
   ```bash
   python3 scripts/validate.py --profile work
   ```

## Building a client proposal

Copy `templates/proposal.html` to `public/proposals/<client>/<topic>/index.html` and fill the tokens. It is self-contained: inline `<style>`, no shared CSS or JS, no canonical, no Open Graph, no JSON-LD, `noindex,nofollow`. Add a link to it from `public/index.html`. **Never promote a proposal into the production repo.**

## Tags and pixels: one container, no exceptions

The site uses a single Google Tag Manager container, **`GTM-NFLQTMGP`**, and campaign landing pages inherit it from `templates/landing-page.html`. That is how conversions on this host stay measurable.

**Never paste a tag into a page.** Not a `gtag.js` snippet, not a Meta pixel, not Clarity, Hotjar, CallRail, or anything a vendor's "install our pixel" page hands you. Two tags double-count every event and split the reporting, and a hard-coded tag skips the rule that a new tracker ships with its privacy-policy disclosure. Every tag goes **inside** the existing container instead. `scripts/validate.py` blocks this (`gtm-foreign`, `tracker-outside-gtm`); if you hit that error, the fix is a container change, not a code change. Ask Steve.

The host index, `/proposals/*`, and the 404 carry no container on purpose: client proposals stay out of our analytics, the same rule the client dashboards follow.

## House rules, inherited from production, non-negotiable

No em dashes anywhere. **No health or efficacy claims**: these are regulated industries, use research-use and compliance framing. Every factual or commercial claim needs a documented source. Primary CTA is **"Get Ranked Free"** linking to `/get-started/` (the funnel captures the lead, then offers the calendar; `/book/` stays live for direct booking links). "Log In" goes to `https://app.nearfront.com/login`. NAP is exactly `550 W B St, 4th Floor, San Diego, CA 92101` and `(760) 829-2735`. **"Nubravo LLC" never appears in public-facing copy**, legal pages only.

## Promoting a page to production

You cannot push to `ConversionSystem/nearfront`. Promotion is a pull request from a fork that only the repo owner can merge. Steps are in `README.md` under "Promote a page". A promoted page ships noindexed; the owner turns indexing on after review.
