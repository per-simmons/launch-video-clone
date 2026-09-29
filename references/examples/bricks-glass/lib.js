// ---------------------------------------------------------------- core helpers (all values are pure functions of the frame F)
const FPS = 30, NFRAMES = 833, DURATION = NFRAMES / FPS;
const $ = (id) => document.getElementById(id);
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const E = {
  lin: (t) => t,
  out: (t) => 1 - Math.pow(1 - t, 3),
  out2: (t) => 1 - (1 - t) * (1 - t),
  out4: (t) => 1 - Math.pow(1 - t, 4),
  out5: (t) => 1 - Math.pow(1 - t, 5),
  in: (t) => t * t * t,
  in2: (t) => t * t,
  io: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  sine: (t) => 0.5 - 0.5 * Math.cos(Math.PI * t),
  // closed-form damped spring 0->1 over t in [0,1] (w = angular speed over the window, z = damping)
  spring: (t, w = 14, z = 0.6) => { if (t <= 0) return 0; if (t >= 1) t = 1; const wd = w * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t)); },
};
const prog = (F, a, b, ease = E.lin) => ease(clamp((F - a) / (b - a)));
// piecewise keyframes [[f, v, ease?], ...]; ease on a key applies to the segment arriving at it
function kf(F, keys, ease = E.io) {
  if (F <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) if (F <= keys[i][0]) {
    const [f0, v0] = keys[i - 1], [f1, v1, e] = keys[i];
    return lerp(v0, v1, (e || ease)((F - f0) / (f1 - f0)));
  }
  return keys[keys.length - 1][1];
}
function rnd(i) { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }

// ---------------------------------------------------------------- DOM
function el(tag, cls, css, parent, html) {
  const e = document.createElement(tag); if (cls) e.className = cls; if (css) e.style.cssText = css;
  if (html != null) e.innerHTML = html; if (parent) parent.appendChild(e); return e;
}
const div = (cls, css, p, html) => el("div", cls, css, p, html);
function show(e, on) { e.style.display = on ? "block" : "none"; }
// text placed by BASELINE (SF Pro: baseline sits 0.855em below the top of a line-height:1 box)
function T(p, s, x, base, size, css = "", anchor = "l") {
  const t = div("t", `font-size:${size}px;left:${x}px;top:${base - 0.855 * size}px;${css}`, p);
  t.textContent = s;
  if (anchor !== "l") t.style.transform = `translateX(${anchor === "c" ? "-50%" : "-100%"})`;
  return t;
}
function svg(p, vb, inner, css) { return div("ic", css, p, `<svg viewBox="${vb}" width="100%" height="100%" style="display:block;overflow:visible">${inner}</svg>`); }
function img(p, src, css) { const i = el("img", "img", css, p); i.src = src; return i; }

// ---------------------------------------------------------------- homography (design rect -> screen quad)
function solveH(src, dst) { // 4 points each [x0,y0,...]; returns 3x3 row-major with h22 = 1
  const A = [], b = [];
  for (let i = 0; i < 4; i++) {
    const x = src[2 * i], y = src[2 * i + 1], u = dst[2 * i], v = dst[2 * i + 1];
    A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.push(u);
    A.push([0, 0, 0, x, y, 1, -v * x, -v * y]); b.push(v);
  }
  for (let c = 0; c < 8; c++) { // gaussian elimination with partial pivoting
    let m = c; for (let r = c + 1; r < 8; r++) if (Math.abs(A[r][c]) > Math.abs(A[m][c])) m = r;
    [A[c], A[m]] = [A[m], A[c]]; [b[c], b[m]] = [b[m], b[c]];
    for (let r = c + 1; r < 8; r++) { const k = A[r][c] / A[c][c]; for (let j = c; j < 8; j++) A[r][j] -= k * A[c][j]; b[r] -= k * b[c]; }
  }
  const h = new Array(8);
  for (let r = 7; r >= 0; r--) { let s = b[r]; for (let j = r + 1; j < 8; j++) s -= A[r][j] * h[j]; h[r] = s / A[r][r]; }
  return [h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], 1];
}
const mul3 = (A, B) => { const C = new Array(9); for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) C[3 * i + j] = A[3 * i] * B[j] + A[3 * i + 1] * B[3 + j] + A[3 * i + 2] * B[6 + j]; return C; };
function inv3(m) {
  const [a, b, c, d, e, f, g, h, i] = m, A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g, det = a * A + b * B + c * C;
  return [A / det, -(b * i - c * h) / det, (b * f - c * e) / det, B / det, (a * i - c * g) / det, -(a * f - c * d) / det, C / det, -(a * h - b * g) / det, (a * e - b * d) / det];
}
function applyH(H, x, y) { const w = H[6] * x + H[7] * y + H[8]; return [(H[0] * x + H[1] * y + H[2]) / w, (H[3] * x + H[4] * y + H[5]) / w]; }
const Hquad = (H, q) => { const o = []; for (let i = 0; i < 4; i++) o.push(...applyH(H, q[2 * i], q[2 * i + 1])); return o; };
const R = (x, y, w, h) => [x, y, x + w, y, x + w, y + h, x, y + h];              // rect -> quad (TL TR BR BL)
const lerpQ = (a, b, t) => a.map((v, i) => lerp(v, b[i], t));
function quadAbout(q, cx, cy, s, rotDeg = 0, dx = 0, dy = 0) { // scale/rotate a quad about a point, then shift
  const c = Math.cos(rotDeg * Math.PI / 180), sn = Math.sin(rotDeg * Math.PI / 180), o = [];
  for (let i = 0; i < 4; i++) { const x = (q[2 * i] - cx) * s, y = (q[2 * i + 1] - cy) * s; o.push(cx + x * c - y * sn + dx, cy + x * sn + y * c + dy); }
  return o;
}
function place(e, w, h, q) { // put a w x h design element onto screen quad q
  const H = solveH(R(0, 0, w, h), q);
  e.style.transform = `matrix3d(${H[0]},${H[3]},0,${H[6]},${H[1]},${H[4]},0,${H[7]},0,0,1,0,${H[2]},${H[5]},0,${H[8]})`;
}

// ---------------------------------------------------------------- measured tracks (tools/track.py --mode homography)
function trkH(name, F) {
  const t = TRK[name], n = t.H.length, x = clamp(F - t.a, 0, n - 1), i = Math.floor(x), k = x - i;
  const A = t.H[i], B = t.H[Math.min(i + 1, n - 1)];
  return k === 0 ? A : A.map((v, j) => lerp(v, B[j], k));
}
const trkRange = (name) => [TRK[name].a, TRK[name].a + TRK[name].H.length - 1];
// screen quad at F of something that sat on quad q at frame ref (default: the track's anchor)
function trkQ(name, q, ref) {
  const Hr = ref == null ? null : inv3(trkH(name, ref));
  return (F) => Hquad(Hr ? mul3(trkH(name, F), Hr) : trkH(name, F), q);
}
// pose: segments {a, b, q: quad | F=>quad, e}; between segments the corners interpolate with the next segment's ease
function pose(F, segs) {
  const Q = (s, f) => (typeof s.q === "function" ? s.q(f) : s.q);
  if (F <= segs[0].a) return Q(segs[0], segs[0].a);
  for (let i = 0; i < segs.length; i++) {
    const s = segs[i]; if (F >= s.a && F <= s.b) return Q(s, F);
    const n = segs[i + 1];
    if (n && F > s.b && F < n.a) return lerpQ(Q(s, s.b), Q(n, n.a), (n.e || E.io)((F - s.b) / (n.a - s.b)));
  }
  const l = segs[segs.length - 1]; return Q(l, l.b);
}
// background plates: keep only centre + uniform scale of the measured motion (smooth gradients make full homographies
// shear), and overscan so the plate edge never shows
function plateQ(fn, W, H, over = 1.22) {
  return (F) => { const q = fn(F), cx = (q[0] + q[2] + q[4] + q[6]) / 4, cy = (q[1] + q[3] + q[5] + q[7]) / 4;
    const s = ((Math.hypot(q[2] - q[0], q[3] - q[1]) + Math.hypot(q[4] - q[6], q[5] - q[7])) / (2 * W)) * over;
    return R(cx - (W * s) / 2, cy - (H * s) / 2, W * s, H * s); };
}
const K = (f, q, e) => ({ a: f, b: f, q, e });                 // a single hand key
const S = (a, b, q, e) => ({ a, b, q, e });                    // a span

// ---------------------------------------------------------------- liquid glass: backdrop blur + SDF edge refraction + rim
const NS = "http://www.w3.org/2000/svg"; let nLens = 0;
function lensMap(w, h, r, band, power) {
  const sc = Math.min(1, 700 / Math.max(w, h)); // maps are smooth: build small, stretch
  const W = Math.max(8, Math.round(w * sc)), H = Math.max(8, Math.round(h * sc)), rr = r * sc, bb = band * sc;
  const c = document.createElement("canvas"); c.width = W; c.height = H;
  const x = c.getContext("2d"), im = x.createImageData(W, H), d = im.data;
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
    const px = i + 0.5 - W / 2, py = j + 0.5 - H / 2, qx = Math.abs(px) - (W / 2 - rr), qy = Math.abs(py) - (H / 2 - rr);
    const ox = Math.max(qx, 0), oy = Math.max(qy, 0), sd = Math.hypot(ox, oy) + Math.min(Math.max(qx, qy), 0) - rr;
    let gx, gy;
    if (qx > 0 && qy > 0) { const L = Math.hypot(ox, oy) || 1; gx = (ox / L) * Math.sign(px); gy = (oy / L) * Math.sign(py); }
    else if (qx > qy) { gx = Math.sign(px); gy = 0; } else { gx = 0; gy = Math.sign(py); }
    const f = Math.pow(Math.max(0, 1 + sd / bb), power), k = (j * W + i) * 4;
    d[k] = 128 + gx * f * 127; d[k + 1] = 128 + gy * f * 127; d[k + 2] = 128; d[k + 3] = 255;
  }
  x.putImageData(im, 0, 0); return c.toDataURL();
}
// o: {blur, disp, band, power, sat, bri, fill, rim, shadow, lens:false}
function glass(p, x, y, w, h, r, o = {}) {
  const g = { w, h, r };
  const blur = o.blur ?? 6, disp = o.disp ?? 40, band = o.band ?? Math.min(h, w) * 0.28;
  let bf = `blur(${blur}px)`;
  if (o.lens !== false && disp > 0) {
    const id = "lens" + nLens++, f = document.createElementNS(NS, "filter");
    f.setAttribute("id", id); f.setAttribute("x", "0"); f.setAttribute("y", "0"); f.setAttribute("width", "100%"); f.setAttribute("height", "100%");
    f.setAttribute("color-interpolation-filters", "sRGB");
    f.innerHTML = `<feImage href="${lensMap(w, h, r, band, o.power ?? 2)}" x="0" y="0" width="${w}" height="${h}" preserveAspectRatio="none" result="m"/>` +
      `<feDisplacementMap in="SourceGraphic" in2="m" scale="${disp}" xChannelSelector="R" yChannelSelector="G"/>`;
    $("defs").appendChild(f); g.fe = f.firstChild; g.dm = f.lastChild;
    bf = `blur(${blur}px) url(#${id})`;
  }
  bf += ` saturate(${o.sat ?? 1.5}) brightness(${o.bri ?? 1})`;
  g.el = div("glass", `left:${x}px;top:${y}px;width:${w}px;height:${h}px;border-radius:${r}px;backdrop-filter:${bf};-webkit-backdrop-filter:${bf};` +
    `background:${o.fill ?? "rgba(255,255,255,.18)"};box-shadow:${o.shadow ?? "0 18px 50px rgba(20,20,40,.16)"};${o.css ?? ""}`, p);
  g.rim = div("rim", `border-radius:inherit;box-shadow:${o.rim ?? RIM}`, g.el);
  g.c = div("gc", "", g.el);                                    // content layer
  g.size = (w2, h2, r2) => {
    g.el.style.width = w2 + "px"; g.el.style.height = h2 + "px"; g.el.style.borderRadius = r2 + "px";
    if (g.fe) { g.fe.setAttribute("width", w2); g.fe.setAttribute("height", h2); }
  };
  g.box = (x2, y2, w2, h2, r2) => { g.el.style.left = x2 + "px"; g.el.style.top = y2 + "px"; g.size(w2, h2, r2 ?? Math.min(w2, h2) / 2); };
  return g;
}
const RIM = "inset 0 0 0 1.5px rgba(255,255,255,.42), inset 1.5px 2.5px 1.5px -1px rgba(255,255,255,.95), inset -1.5px -2.5px 1.5px -1px rgba(255,255,255,.55), inset 0 0 26px rgba(255,255,255,.18)";
const RIM_DARK = "inset 0 0 0 1.5px rgba(255,255,255,.22), inset 1.5px 2.5px 1.5px -1px rgba(255,255,255,.55), inset -1.5px -2.5px 1.5px -1px rgba(255,255,255,.3), inset 0 0 22px rgba(255,255,255,.06)";

// ---------------------------------------------------------------- VO word landing: rise 12px, un-blur, fade over 4-5 f
function landing(F, f0, dur = 5) { const t = clamp((F - f0) / dur); return { t, a: E.out2(t), y: 14 * (1 - E.out(t)), b: 4 * (1 - E.out(t)) }; }
function styleLand(e, F, f0, dur, dy = 14) {
  if (F < f0) { e.style.opacity = 0; return 0; }
  const L = landing(F, f0, dur); e.style.opacity = L.a;
  e.style.transform = `translateY(${(L.y * dy) / 14}px)`; e.style.filter = L.b > 0.05 ? `blur(${L.b.toFixed(2)}px)` : "none";
  return L.t;
}
// a line of words; words = [[text, frame], ...]; align "l" | "c" (centred lines re-centre as words arrive)
function wordLine(p, words, x, base, size, css = "", align = "l", dur = 5) {
  const line = div("wl", `left:${x}px;top:${base - 0.855 * size}px;font-size:${size}px;${css}`, p);
  const spans = words.map(([w, f], i) => { const s = el("span", "w", "", line); s.textContent = w; s.f = f; if (i < words.length - 1) line.appendChild(document.createTextNode(" ")); return s; });
  const o = { line, spans, align, x, dur };
  o.draw = (F) => {
    let vis = 0, tot = 0;
    spans.forEach((s, i) => { const t = styleLand(s, F, s.f, dur); if (align === "c") { const w = s.offsetWidth + (i ? size * 0.26 : 0); tot += w; vis += w * t; } });
    if (align === "c") line.style.transform = `translateX(${-vis / 2 - (tot - vis) * 0}px)`;
  };
  if (align === "c") { line.style.transform = "translateX(-50%)"; }
  return o;
}
// per-character typing: chars[i] lands at frames[i]
function typed(p, text, frames, x, base, size, css = "", dur = 2) {
  const line = div("wl", `left:${x}px;top:${base - 0.855 * size}px;font-size:${size}px;${css}`, p);
  const spans = [...text].map((ch, i) => { const s = el("span", "ch", "white-space:pre", line); s.textContent = ch; s.f = frames[i]; return s; });
  return { line, draw: (F) => spans.forEach((s) => { s.style.opacity = F < s.f ? 0 : clamp((F - s.f + 1) / dur); }) };
}
// soft blob background: base colour + radial blobs [{c: 'r,g,b', a, x, y, rx, ry}] (functions of F allowed)
function blobBG(p, css = "") { const e = div("bg", css, p); return e; }
function paintBlobs(e, F, base, blobs) {
  const v = (x) => (typeof x === "function" ? x(F) : x);
  e.style.background = blobs.map((b) => `radial-gradient(${v(b.rx)}px ${v(b.ry)}px at ${v(b.x)}px ${v(b.y)}px, rgba(${b.c},${v(b.a)}) 0%, rgba(${b.c},${v(b.a) * 0.5}) 45%, rgba(${b.c},0) 100%)`).join(",") + "," + base;
}

// measured gradient field (tools/bgfield.py): 4x3 colours per key, bilinear upsample + blur
function fieldBG(p) {
  const e = div("bg", "overflow:hidden", p);
  const c = el("canvas", "", "position:absolute;left:-96px;top:-54px;width:2112px;height:1188px;filter:blur(46px)", e); c.width = 4; c.height = 3;
  e.cv = c; e.cx = c.getContext("2d"); e.im = e.cx.createImageData(4, 3); return e;
}
function paintField(e, F, name) {
  const B = BGF[name], x = clamp((F - B.a) / B.step, 0, B.k.length - 1), i = Math.floor(x), t = x - i;
  const A = B.k[i], C = B.k[Math.min(i + 1, B.k.length - 1)], d = e.im.data;
  for (let j = 0; j < 12; j++) for (let ch = 0; ch < 3; ch++) d[j * 4 + ch] = lerp(A[j][ch], C[j][ch], E.sine(t));
  for (let j = 0; j < 12; j++) d[j * 4 + 3] = 255;
  e.cx.putImageData(e.im, 0, 0);
}
