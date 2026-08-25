"""Find markup classes that no stylesheet defines.

This is the defect class that broke /get-started/: a page rebuild replaced the
<style> block and silently orphaned the classes the old block had styled, so
inputs and buttons fell back to browser defaults. The validator does not catch
it, because the HTML is structurally fine.

Checks every page's classes against its own inline <style> blocks plus the
shared site.css. Classes that appear nowhere in any stylesheet are reported,
with form and button related names called out first since those are the ones
that look obviously broken to a visitor.
"""
import os, re, sys, glob

ROOT = sys.argv[1] if len(sys.argv) > 1 else '/Users/steve/NearFront/nearfront-repo'
PUB = os.path.join(ROOT, 'public')
SITE_CSS = open(os.path.join(PUB, 'assets/site.css')).read()

# Classes that are hooks rather than styling targets.
IGNORE = {
    'js', 'fade-up', 'visible', 'is-active', 'is-done', 'no-js',
}
INTERESTING = re.compile(r'(field|input|form|btn|button|submit|consent|label|'
                         r'card|panel|row|grid|hp|honey|cta|link|nav|foot)', re.I)


def selectors_in(css):
    css = re.sub(r'/\*.*?\*/', ' ', css, flags=re.S)
    return set(re.findall(r'\.([A-Za-z][\w-]*)', css))


def scan(path):
    s = open(path).read()
    inline = "\n".join(re.findall(r'<style>(.*?)</style>', s, re.S))
    defined = selectors_in(inline) | selectors_in(SITE_CSS)
    used = set()
    for attr in re.findall(r'class="([^"]+)"', s):
        for c in attr.split():
            used.add(c)
    orphans = sorted(c for c in used - defined - IGNORE)
    return orphans, len(inline)


rows = []
for path in sorted(glob.glob(os.path.join(PUB, '**/index.html'), recursive=True)
                   + glob.glob(os.path.join(PUB, '*.html'))):
    if '/reports/' in path:
        continue
    orphans, inline_len = scan(path)
    if orphans:
        rows.append((path.replace(PUB + '/', ''), orphans, inline_len))

hot = [(p, o, n) for p, o, n in rows if any(INTERESTING.search(c) for c in o)]
print("pages scanned: %d | pages with orphan classes: %d | of those, form/UI related: %d\n"
      % (len(glob.glob(os.path.join(PUB, '**/index.html'), recursive=True)), len(rows), len(hot)))

if hot:
    print("=== LIKELY VISIBLE BREAKAGE (form/button/layout classes with no rule) ===")
    for p, o, n in hot:
        flagged = [c for c in o if INTERESTING.search(c)]
        print("  %-52s %s" % (p, ", ".join(flagged[:8])))
    print()

rest = [(p, o, n) for p, o, n in rows if not any(INTERESTING.search(c) for c in o)]
if rest:
    print("=== other unstyled classes (often semantic or JS hooks) ===")
    for p, o, n in rest[:15]:
        print("  %-52s %s" % (p, ", ".join(o[:8])))
