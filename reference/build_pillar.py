"""Emit a top-level pillar page by cloning the shipped blog-post shell.

Adapted from build_post.py (2026-08-26). Difference: output lands at
public/<slug>/ rather than under a section, the breadcrumb is two levels
(Home > page), and the JSON-LD carries Article rather than BlogPosting,
since a pillar is a maintained reference page rather than a dated post.

Head, styles, nav, footer, author card and CTA come verbatim from the
production money page's sibling post, so the shell stays byte-identical
and validate.py's SHELL_REF comparison passes.
"""
import json, os, re

REPO = '/Users/steve/NearFront/nearfront-repo'
WORK = '/Users/steve/NearFront/nearfront-work'
BASE = open(os.path.join(REPO, 'public/blog/dispensary-near-me-map-pack/index.html')).read()


def build(a, lane='work'):
    s = BASE
    root = WORK if lane == 'work' else REPO
    url = 'https://nearfront.com/%s/' % a['slug']
    date_iso = a.get('date_iso', '2026-08-26')
    date_h = a.get('date_human', 'August 26, 2026')

    s = re.sub(r'<title>.*?</title>', '<title>%s</title>' % a['title'], s, flags=re.S)
    s = re.sub(r'<meta name="description" content=".*?">',
               '<meta name="description" content="%s">' % a['desc'], s, flags=re.S)
    s = re.sub(r'<link rel="canonical" href=".*?">', '<link rel="canonical" href="%s">' % url, s)
    if lane == 'work':
        s = s.replace('<meta name="robots" content="index,follow">',
                      '<meta name="robots" content="noindex,nofollow">')
    for k, tag in (('og:title', 'property'), ('twitter:title', 'name')):
        s = re.sub(r'<meta %s="%s" content=".*?">' % (tag, k),
                   '<meta %s="%s" content="%s">' % (tag, k, a['title']), s, flags=re.S)
    for k, tag in (('og:description', 'property'), ('twitter:description', 'name')):
        s = re.sub(r'<meta %s="%s" content=".*?">' % (tag, k),
                   '<meta %s="%s" content="%s">' % (tag, k, a['social']), s, flags=re.S)
    s = re.sub(r'<meta property="og:url" content=".*?">',
               '<meta property="og:url" content="%s">' % url, s)
    s = re.sub(r'<meta property="article:published_time" content=".*?">',
               '<meta property="article:published_time" content="%s">' % date_iso, s)

    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Article",
         "image": {"@type": "ImageObject", "url": "https://nearfront.com/assets/guillermo-bravo.jpg",
                   "width": 520, "height": 520},
         "headline": a['h1'], "description": a['desc'], "url": url,
         "datePublished": date_iso, "dateModified": date_iso,
         "author": {"@type": "Person", "name": "Guillermo Bravo", "url": "https://nearfront.com/about-us/"},
         "publisher": {"@type": "Organization", "@id": "https://nearfront.com/#org", "name": "Nearfront",
                       "url": "https://nearfront.com/",
                       "logo": {"@type": "ImageObject", "url": "https://nearfront.com/assets/logo.svg"}},
         "mainEntityOfPage": url,
         "citation": a['citations']},
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}}
            for q, ans in a['faq']]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://nearfront.com/"},
            {"@type": "ListItem", "position": 2, "name": a['crumb'], "item": url}]}]}
    s = re.sub(r'<script type="application/ld\+json">.*?</script>',
               lambda m: '<script type="application/ld+json">\n%s\n</script>'
                         % json.dumps(ld, indent=2, ensure_ascii=False), s, count=1, flags=re.S)

    faqs = "\n".join('  <div class="svc-faq-item"><h3>%s</h3><p>%s</p></div>' % (q, ans)
                     for q, ans in a['faq'])
    body = '''
<div class="post-hero">
  <div class="post-hero-inner fade-up">
    <span class="svc-kicker">%(kicker)s</span>
    <h1>%(h1)s</h1>
    <p class="post-meta">By <a href="/about-us/">Guillermo Bravo</a> &middot; Updated %(date_h)s &middot; %(mins)s min read &middot; <a href="/services/cannabis-dispensary-seo/">&larr; Dispensary SEO service</a></p>
  </div>
</div>

<article class="post-body fade-up">
%(body)s
  <h2 id="faq">Frequently asked questions</h2>
%(faqs)s
</article>

  <div class="post-author">
    <img src="/assets/guillermo-bravo.jpg" alt="Guillermo Bravo" width="56" height="56" loading="lazy">
    <div>
      <div class="pa-name">Guillermo Bravo</div>
      <div class="pa-bio">Founder &amp; CEO of Nearfront. In SEO since 2007. Founded Foottraffik, the first cannabis-focused SEO company, and exited in 2021. Hosts the SEO Rockstars podcast.</div>
    </div>
  </div>

<div class="post-related">
  <div class="svc-related">
%(related)s
  </div>
</div>

<section class="svc-cta">
  <div class="svc-cta-inner fade-up">
    <h2>%(cta_h)s</h2>
    <p>%(cta_p)s</p>
    <a href="/book/" class="btn-primary" style="font-size:15px;padding:16px 40px">Get Ranked Free</a>
  </div>
</section>
''' % dict(h1=a['h1'], mins=a['mins'], body=a['body'].strip(), faqs=faqs,
           kicker=a['kicker'], date_h=date_h,
           cta_h=a['cta_h'], cta_p=a['cta_p'],
           related="\n".join('      <a href="%s">%s</a>' % (u, t) for u, t in a['related']))
    s = re.sub(r'<main id="main">.*?</main>', lambda m: '<main id="main">\n%s\n</main>' % body,
               s, flags=re.S)

    out = os.path.join(root, 'public', a['slug'], 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w').write(s)
    return out, len(s)
