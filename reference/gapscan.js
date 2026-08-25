// Reports multi-column grid/flex rows where one column ends well before the
// tallest one, which is what reads as dead space on the page.
(function () {
  var out = [];
  var els = document.querySelectorAll('div,section,main,article,ul');
  for (var i = 0; i < els.length; i++) {
    var el = els[i];
    var cs = getComputedStyle(el);
    if (cs.display !== 'grid' && cs.display !== 'flex') continue;
    if (cs.display === 'grid') {
      var cols = cs.gridTemplateColumns.split(' ').filter(Boolean).length;
      if (cols < 2) continue;
    } else if (cs.flexDirection !== 'row') continue;

    var kids = [];
    for (var k = 0; k < el.children.length; k++) {
      var c = el.children[k];
      var r = c.getBoundingClientRect();
      if (r.height > 0) kids.push({ el: c, h: r.height, top: r.top });
    }
    if (kids.length < 2) continue;

    // Only compare items on the same visual row.
    var rowTop = Math.min.apply(null, kids.map(function (x) { return x.top; }));
    var sameRow = kids.filter(function (x) { return Math.abs(x.top - rowTop) < 24; });
    if (sameRow.length < 2) continue;

    var hs = sameRow.map(function (x) { return x.h; });
    var max = Math.max.apply(null, hs);
    var min = Math.min.apply(null, hs);
    var gap = max - min;
    if (gap < 120) continue;                 // small differences read as fine
    if (max < 200) continue;                 // tiny rows do not create dead space

    var shortest = sameRow.filter(function (x) { return x.h === min; })[0];
    out.push({
      container: el.className || el.tagName,
      cols: sameRow.length,
      tallest: Math.round(max),
      shortest: Math.round(min),
      deadspace: Math.round(gap),
      shortEl: (shortest.el.className || shortest.el.tagName).toString().slice(0, 60)
    });
  }
  out.sort(function (a, b) { return b.deadspace - a.deadspace; });
  return JSON.stringify(out.slice(0, 8));
})();
