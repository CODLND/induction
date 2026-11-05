"""Turn a Gemini 4x4 magenta sprite sheet into a clean, aligned, transparent 4x4 PNG sheet.

Usage: python3 tools/build_sprites.py <sheet.jpg> <out.png> [<sheet.jpg> <out.png> ...]
Prints the cw/ch/skin values to paste into SPRITES in healthcare.html.

Steps: key out the magenta background, find each character by its outline (connected
components, so overlapping cells are handled), attach small bits (sparkles, "?", sweat drops)
to the nearest character, then line every frame up on the same feet baseline and head centre.
Frames that Gemini cut off at the waist are scaled to match and given legs from a full-body frame.
"""
import sys, json, colorsys, numpy as np
from PIL import Image

ROWS = COLS = 4
CROPPED_RATIO = 0.93        # frame shorter than this x full height (after scaling) = cut off
NEVER_CROPPED = {(3, 3)}    # the jump frame is short on purpose
DONOR_ORDER = [(2, 3), (1, 1), (2, 2), (2, 0), (3, 0), (3, 1), (1, 0)]

# Per-sheet fixes, checked by eye. "cropped": frames Gemini cut off (they get legs from "donor",
# a full-body frame). "via": rebuild a cropped frame on top of another already-repaired frame
# (used when the donor's pose doesn't fit, e.g. a bust cut at the chest).
ALL_ROW = lambda r: [(r, c) for c in range(COLS)]
SPEC = {
    "male-elderly":   dict(cropped=[], donor=(2, 3), cuts={2: 1505, 3: 1503}),
    "female-elderly": dict(cropped=ALL_ROW(0) + ALL_ROW(2), donor=(3, 1), donor_row0=(3, 0)),
    "male-adult":     dict(cropped=ALL_ROW(0), donor=(2, 3)),
    "female-adult":   dict(cropped=ALL_ROW(0), donor=(2, 3)),
    "male-teen":      dict(cropped=ALL_ROW(0) + [(2, 3)], donor=(1, 1), cuts={3: 1438}),
    "female-teen":    dict(cropped=ALL_ROW(0) + [(1, 1), (1, 2), (1, 3)] + ALL_ROW(2) + [(3, 0), (3, 1)],
                           donor=(3, 2), via={(2, 3): (0, 0)}, cuts={0: 1488, 1: 1488, 2: 1410, 3: 1362}),
}


def bgmask(a):
    r, g, b = [a[..., i].astype(int) for i in range(3)]
    m1 = (r > 120) & (b > 120) & (g < np.minimum(r, b) - 60)          # magenta + JPEG fringe
    m2 = (abs(r - b) < 45) & (g < 0.55 * np.minimum(r, b)) & (r > 60)  # darker purple (drop shadows)
    return m1 | m2


def label(mask):
    """4-connected component labels via iterative min-propagation (no scipy needed)."""
    H, W = mask.shape
    lab = np.where(mask, np.arange(H * W).reshape(H, W) + 1, 0).astype(np.int64)
    big = np.iinfo(np.int64).max
    while True:
        m = np.where(mask, lab, big)
        n = m.copy()
        n[1:] = np.minimum(n[1:], m[:-1]); n[:-1] = np.minimum(n[:-1], m[1:])
        n[:, 1:] = np.minimum(n[:, 1:], m[:, :-1]); n[:, :-1] = np.minimum(n[:, :-1], m[:, 1:])
        n = np.where(mask, n, 0)
        # pointer jumping
        flat = n.ravel()
        idx = flat > 0
        flat2 = flat.copy()
        flat2[idx] = np.minimum(flat[idx], lab.ravel()[flat[idx] - 1])
        n = flat2.reshape(H, W)
        if np.array_equal(n, lab): return lab
        lab = n


def split_touching(sub, cut=None):
    """Two characters touching vertically: cut along a horizontal line (given, or the thinnest
    row), then move any piece that got cut off from its own body to the other character."""
    ys = np.where(sub.any(1))[0]
    if cut is None:
        lo, hi = ys.min() + 150, min(ys.min() + 280, sub.shape[0] - 1)
        cut = lo + int(np.argmin(sub[lo:hi].sum(1)))
    top = sub.copy(); top[cut:] = False
    bot = sub.copy(); bot[:cut] = False
    def tidy(a, b):
        lab = label(a)
        ids, counts = np.unique(lab[lab > 0], return_counts=True)
        if len(ids) <= 1: return a, b
        keep = ids[np.argmax(counts)]
        stray = (lab > 0) & (lab != keep)
        # only move strays that touch the other part's bounding columns near the cut
        return a & ~stray, b | stray
    top, bot = tidy(top, bot)
    bot, top = tidy(bot, top)
    return [top, bot]


def find_frames(fg, cuts=None, im=None, colorsplit=None):
    H, W = fg.shape
    small = fg[::2, ::2] | fg[1::2, ::2] | fg[::2, 1::2] | fg[1::2, 1::2]
    lab = label(small)
    ids, counts = np.unique(lab[lab > 0], return_counts=True)
    comps = []
    for i, c in zip(ids, counts):
        ys, xs = np.where(lab == i)
        comps.append(dict(id=i, n=c, cy=ys.mean() * 2, cx=xs.mean() * 2, y0=ys.min() * 2, y1=ys.max() * 2))
    bodies = [c for c in comps if c["n"] > 4000]
    # split any body that spans two rows (two characters touching)
    out = []
    for b in bodies:
        if b["y1"] - b["y0"] > 640:
            col = int(b["cx"] // (W / COLS))
            cut = (cuts or {}).get(col)
            parts = split_touching(lab == b["id"], None if cut is None else cut // 2)
            if colorsplit and col in colorsplit and im is not None:
                # in an overlap band, blue (skirt) pixels belong to the upper character
                y0b, y1b = colorsplit[col]
                small_im = im[::2, ::2].astype(int)
                blue = (small_im[..., 2] > small_im[..., 0] + 30) & (small_im[..., 2] > small_im[..., 1])
                band = np.zeros_like(blue); band[y0b // 2:y1b // 2] = True
                move = parts[1] & blue & band
                parts = [parts[0] | move, parts[1] & ~move]
            for m in parts:
                ys, xs = np.where(m)
                out.append(dict(mask=m, cy=ys.mean() * 2, cx=xs.mean() * 2))
        else:
            ys, xs = np.where(lab == b["id"])
            out.append(dict(mask=(lab == b["id"]), cy=b["cy"], cx=b["cx"]))
    assert len(out) == ROWS * COLS, f"expected 16 characters, found {len(out)}"
    # attach small bits to the nearest body
    for c in comps:
        if c["n"] > 4000 or c["n"] < 6: continue
        best = min(out, key=lambda b: (b["cx"] - c["cx"]) ** 2 + (b["cy"] - c["cy"]) ** 2)
        best["mask"] = best["mask"] | (lab == c["id"])
    # grid position: column from x, row = order of y within the column
    frames = {}
    for col in range(COLS):
        colb = sorted([b for b in out if int(b["cx"] // (W / COLS)) == col], key=lambda b: b["cy"])
        assert len(colb) == ROWS, f"column {col}: {len(colb)} characters"
        for row, b in enumerate(colb):
            m = np.repeat(np.repeat(b["mask"], 2, 0), 2, 1)[:H, :W] & fg
            ys, xs = np.where(m)
            frames[(row, col)] = dict(mask=m, top=ys.min(), bottom=ys.max(), left=xs.min(), right=xs.max())
    return frames


def head_metrics(m, top):
    """Head centre x and width, measured on the row 90px below the top of the head."""
    cx = (np.where(m.any(0))[0].min() + np.where(m.any(0))[0].max()) / 2
    # top of the head: topmost pixel within +/-110px of the frame centre
    band = m[:, int(cx) - 110:int(cx) + 110]
    ys = np.where(band.any(1))[0]
    htop = ys[0] if len(ys) else top
    row = m[min(htop + 90, m.shape[0] - 1)]
    xs = np.where(row)[0]
    if not len(xs): return cx, 0, htop
    # contiguous run nearest the centre
    segs, s = [], xs[0]
    for a, b in zip(xs, list(xs[1:]) + [None]):
        if b is None or b != a + 1: segs.append((s, a)); s = b
    seg = min(segs, key=lambda q: abs((q[0] + q[1]) / 2 - cx))
    return (seg[0] + seg[1]) / 2, seg[1] - seg[0], htop


def build(src, out_png, name=None):
    spec = SPEC.get(name)
    im = np.array(Image.open(src).convert("RGB"))
    fg = ~bgmask(im)
    frames = find_frames(fg, (spec or {}).get("cuts"), im, (spec or {}).get("colorsplit"))
    for f in frames.values():
        f["hx"], f["hw"], f["htop"] = head_metrics(f["mask"], f["top"])
    ref_hw = float(np.median([frames[(r, c)]["hw"] for r in (1, 2) for c in range(COLS)]))
    for k, f in frames.items():
        ratio = ref_hw / f["hw"] if f["hw"] else 1
        f["scale"] = ratio if abs(1 - ratio) > 0.04 and 0.8 < ratio < 1.25 else 1.0
        f["h"] = (f["bottom"] - f["htop"]) * f["scale"]
    hs = sorted(f["h"] for k, f in frames.items() if k not in NEVER_CROPPED)
    full_h = float(hs[-2])   # second tallest, robust to one odd frame
    for k, f in frames.items():
        f["cropped"] = (k in spec["cropped"]) if spec else (k not in NEVER_CROPPED and f["h"] < CROPPED_RATIO * full_h)
        if spec and not f["cropped"]: f["scale"] = 1.0
    donor_key = spec["donor"] if spec else next(k for k in DONOR_ORDER if not frames[k]["cropped"])
    base = {}
    for r in range(ROWS):
        bots = [frames[(r, c)]["bottom"] for c in range(COLS) if not frames[(r, c)]["cropped"]]
        base[r] = max(bots) if bots else None

    def piece(f):
        """RGBA crop of one frame, scaled; returns (array, head x, head top) in piece coords."""
        y0, y1, x0, x1 = f["top"], f["bottom"] + 1, f["left"], f["right"] + 1
        p = np.dstack([im[y0:y1, x0:x1], np.where(f["mask"][y0:y1, x0:x1], 255, 0).astype(np.uint8)])
        s = f["scale"]
        if s != 1.0:
            img = Image.fromarray(p, "RGBA")
            p = np.array(img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.NEAREST))
        return p, (f["hx"] - x0) * s, (f["htop"] - y0) * s

    # canvas size: generous, trimmed later
    CW, CH, PAD = 900, 760, 12
    HX = CW // 2
    def stamp(can, p, ox, oy):
        ys, xs = np.where(p[..., 3] > 0)
        ty, tx = ys + oy, xs + ox
        ok = (ty >= 0) & (ty < CH) & (tx >= 0) & (tx < CW)
        can[ty[ok], tx[ok]] = p[ys[ok], xs[ok]]

    def donor_canvas(key):
        d = frames[key]
        dp, dhx, dht = piece(d)
        oy = CH - PAD - (base[key[0]] - d["top"])
        can = np.zeros((CH, CW, 4), np.uint8)
        stamp(can, dp, int(round(HX - dhx)), oy)
        return can, oy + dht
    donors = {donor_key: donor_canvas(donor_key)}
    if spec and spec.get("donor_row0"): donors[spec["donor_row0"]] = donor_canvas(spec["donor_row0"])

    def repair(f, donor_can, donor_head_top, p, phx, pht):
        can = np.zeros((CH, CW, 4), np.uint8)
        oy = int(round(donor_head_top - pht))
        stamp(can, p, int(round(HX - phx)), oy)
        a2 = can[::2, ::2, 3] > 0
        lab = label(a2)
        ids, counts = np.unique(lab[lab > 0], return_counts=True)
        main = lab == ids[np.argmax(counts)]
        fb = np.where(main.any(1))[0].max() * 2 + 1   # bottom of the main body, ignoring stray bits
        seam = fb - 8
        cols = can[seam - 6:seam, :, 3].any(0)
        cols = np.convolve(cols, np.ones(9), "same") > 0
        fill = donor_can[seam:].copy(); fill[:, ~cols] = 0
        can[seam:] = np.where(can[seam:, :, 3:4] > 0, can[seam:], fill)
        return can

    cells = {}
    via = (spec or {}).get("via", {})
    dk0 = (spec or {}).get("donor_row0") or donor_key
    for (r, c), f in sorted(frames.items(), key=lambda kv: kv[0] in via):
        p, phx, pht = piece(f)
        if (r, c) in via:
            src_can = cells[via[(r, c)]]
            ys = np.where(src_can[..., 3].any(1))[0]
            # head top of the source cell: topmost row near the centre column
            cen = src_can[:, HX - 110:HX + 110, 3].any(1)
            cells[(r, c)] = repair(f, src_can, np.where(cen)[0][0], p, phx, pht)
        elif f["cropped"]:
            dc, dht = donors[dk0 if r == 0 else donor_key]
            cells[(r, c)] = repair(f, dc, dht, p, phx, pht)
        else:
            can = np.zeros((CH, CW, 4), np.uint8)
            oy = CH - PAD - (base[r] - f["top"])
            stamp(can, p, int(round(HX - phx)), oy)
            cells[(r, c)] = can

    # trim to the union of all frames (keep head centre in the middle)
    alpha = np.zeros((CH, CW), bool)
    for can in cells.values(): alpha |= can[..., 3] > 0
    ys, xs = np.where(alpha)
    half = max(HX - xs.min(), xs.max() - HX) + PAD
    y_top = max(0, ys.min() - PAD)
    X0, X1 = HX - half, HX + half
    tw, th = X1 - X0, CH - y_top
    sheet = np.zeros((th * ROWS, tw * COLS, 4), np.uint8)
    for (r, c), can in cells.items():
        sheet[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = can[y_top:CH, X0:X1]

    # remove tiny stray specks (JPEG noise / leftovers) from each cell; keep sparkles and other details
    for r in range(ROWS):
        for c in range(COLS):
            cell = sheet[r * th:(r + 1) * th, c * tw:(c + 1) * tw]
            lab = label(cell[..., 3] > 0)
            ids, counts = np.unique(lab[lab > 0], return_counts=True)
            for i, n in zip(ids, counts):
                if n < 90: cell[lab == i] = 0

    # downscale 2x with premultiplied alpha
    scale = 0.5
    a = sheet[..., 3:4].astype(np.float32) / 255
    pm = sheet[..., :3].astype(np.float32) * a
    nw, nh = int(sheet.shape[1] * scale), int(sheet.shape[0] * scale)
    chans = [np.array(Image.fromarray(pm[..., i]).resize((nw, nh), Image.BOX)) for i in range(3)]
    al = np.array(Image.fromarray(a[..., 0]).resize((nw, nh), Image.BOX))
    rgb = np.dstack(chans) / np.maximum(al[..., None], 1e-4)
    al = np.where(al < 0.35, 0, np.where(al > 0.65, 1, al))
    outa = np.dstack([np.clip(rgb, 0, 255), al * 255]).astype(np.uint8)
    outa[al == 0] = 0
    Image.fromarray(outa, "RGBA").quantize(colors=128, method=Image.Quantize.FASTOCTREE,
                                           dither=Image.Dither.NONE).save(out_png, optimize=True)

    # reference skin colour: median of skin-like pixels
    px = im[fg].reshape(-1, 3) / 255.0
    sel = []
    for p in px[:: max(1, len(px) // 40000)]:
        h, l, s = colorsys.rgb_to_hls(*p)
        if 8 / 360 <= h <= 33 / 360 and 0.3 <= l <= 0.8 and 0.25 <= s <= 0.65: sel.append(p)
    ref = (np.median(np.array(sel), 0) * 255).round().astype(int).tolist()
    cropped = sorted(k for k, f in frames.items() if f["cropped"])
    return dict(cw=int(tw * scale), ch=int(th * scale), skin=ref, donor=donor_key, repaired=cropped)


if __name__ == "__main__":
    args = sys.argv[1:]
    meta = {}
    for src, out in zip(args[::2], args[1::2]):
        name = out.split("/")[-1].rsplit(".", 1)[0]
        meta[name] = build(src, out, name)
    print(json.dumps(meta))
