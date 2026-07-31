# Refreshing `reference/_redirects`

This is a **read-only copy** of `public/_redirects` from the production repo
(`ConversionSystem/nearfront`). It exists so `scripts/validate.py --check-url`
can tell you whether a URL is already claimed **before** you build a page.

It is not deployed. It sits outside `public/` on purpose: if it were inside,
this host would start applying 755 legacy WordPress redirects to itself.

## When to refresh

Before starting a batch of new pages, or any time `--check-url` disagrees with
what you see on the live site. The production list changes rarely.

## How

```bash
gh api repos/ConversionSystem/nearfront/contents/public/_redirects \
  -H "Accept: application/vnd.github.raw" > reference/_redirects
```

If you do not have `gh` set up, open the file on GitHub and save the raw view
to the same path.
