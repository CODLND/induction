"""Turn a Gemini 4x4 magenta sprite sheet into a clean, aligned, transparent 4x4 PNG sheet."""
# Usage: python3 tools/build_sprites.py <male-sheet.jpg> <female-sheet.jpg> <male-out.png> <female-out.png>
# Prints the cw/ch/skin values to paste into SPRITES in healthcare.html.
import sys, json, colorsys, numpy as np
from PIL import Image

def bgmask(a):
    r, g, b = [a[..., i].astype(int) for i in range(3)]
    m1 = (r > 120) & (b > 120) & (g < np.minimum(r, b) - 60)          # magenta + JPEG fringe
    m2 = (abs(r - b) < 45) & (g < 0.55 * np.minimum(r, b)) & (r > 60)  # darker purple (drop shadows)
    return m1 | m2

def runs(v, minrun):
    out, s = [], None
    for i, x in enumerate(list(v) + [False]):
        if x and s is None: s = i
        if not x and s is not None:
            if i - s >= minrun: out.append((s, i))
            s = None
    return out

def split_rows(fg_col):
    """Vertical bands for one column of cells; split merged bands at the emptiest row."""
    bands = runs(fg_col.sum(1) > 2, 4)
    out = []
    for (a, b) in bands:
        while b - a > 700:  # two sprites touching: cut near the nominal 500px grid line
            k = round((a + 500) / 500) * 500
            lo, hi = k - 12, min(k + 25, b - 1)
            cut = lo + int(np.argmin(fg_col[lo:hi].sum(1)))
            out.append((a, cut)); a = cut
        out.append((a, b))
    return [x for x in out if x[1] - x[0] > 150]

def head_center(fg, x0, x1, top_hint=None):
    cx = (x0 + x1) // 2
    sub = fg[:, cx - 100:cx + 100]
    ys = np.where(sub.any(1))[0]
    top = ys[0]
    row = fg[top + 70, x0:x1]
    segs = runs(row, 10)
    if not segs: return cx, top
    seg = min(segs, key=lambda s: abs((s[0] + s[1]) / 2 + x0 - cx))
    return x0 + (seg[0] + seg[1]) / 2, top

def build(src, out_png, donors=None):
    donors = donors or {}
    im = np.array(Image.open(src).convert("RGB"))
    H, W, _ = im.shape
    fg = ~bgmask(im)
    rgba = np.dstack([im, (fg * 255).astype(np.uint8)])
    frames = {}
    for c in range(4):
        x0, x1 = c * W // 4, (c + 1) * W // 4
        bands = split_rows(fg[:, x0:x1])
        assert len(bands) == 4, (src, c, bands)
        for r, (y0, y1) in enumerate(bands):
            cell = fg[y0:y1, x0:x1]
            ys, xs = np.where(cell)
            hx, htop = head_center(fg[y0:y1], x0, x1)
            frames[(r, c)] = dict(y0=y0, y1=y1, x0=x0, x1=x1, top=y0 + ys.min(), bottom=y0 + ys.max(),
                                  left=x0 + xs.min(), right=x0 + xs.max(), hx=hx)
    # row baselines from frames that reach the floor
    base = {}
    for r in range(4):
        bots = [frames[(r, c)]["bottom"] for c in range(4)]
        base[r] = max(bots)
    # canvas extents (relative to head centre x, row baseline y)
    up = max(base[r] - f["top"] for (r, c), f in frames.items())
    left = max(f["hx"] - f["left"] for f in frames.values())
    right = max(f["right"] - f["hx"] for f in frames.values())
    half = int(max(left, right)) + 12
    CW, CH = 2 * half, int(up) + 24
    def place(f, r, dy=0):
        can = np.zeros((CH, CW, 4), np.uint8)
        piece = rgba[f["y0"]:f["y1"], f["x0"]:f["x1"]].copy()
        piece[..., 3] = np.where(fg[f["y0"]:f["y1"], f["x0"]:f["x1"]], 255, 0)
        ox = int(round(half - (f["hx"] - f["x0"])))
        oy = int(CH - 12 - (base[r] - f["y0"])) + dy
        ys, xs = np.where(piece[..., 3] > 0)
        ty, tx = ys + oy, xs + ox
        ok = (ty >= 0) & (ty < CH) & (tx >= 0) & (tx < CW)
        can[ty[ok], tx[ok]] = piece[ys[ok], xs[ok]]
        return can
    cells = {}
    for (r, c), f in frames.items():
        if r in donors:
            donor = donors[r]
            d = frames[donor]
            dcan = place(d, donor[0])
            # align cropped frame head-top with donor head-top
            dtop = CH - 12 - (base[donor[0]] - d["top"])
            ftop_if_placed = CH - 12 - (base[r] - f["top"])
            fcan = place(f, r, dy=dtop - ftop_if_placed)
            fbottom = np.where(fcan[..., 3].any(1))[0].max()
            out = fcan.copy()
            seam = fbottom - 8
            # only take donor pixels in columns the cropped frame occupies just above the seam
            cols = fcan[seam - 6:seam, :, 3].any(0)
            cols = np.convolve(cols, np.ones(9), "same") > 0
            fill = dcan[seam:].copy(); fill[:, ~cols] = 0
            out[seam:] = np.where(fcan[seam:, :, 3:4] > 0, fcan[seam:], fill)
            out[seam:, ~cols] = fcan[seam:, ~cols]
            cells[(r, c)] = out
        else:
            cells[(r, c)] = place(f, r)
    sheet = np.zeros((CH * 4, CW * 4, 4), np.uint8)
    for (r, c), cell in cells.items():
        sheet[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = cell
    # downscale 2x with premultiplied alpha
    scale = 0.5
    img = Image.fromarray(sheet, "RGBA")
    a = sheet[..., 3:4].astype(np.float32) / 255
    pm = (sheet[..., :3].astype(np.float32) * a)
    nw, nh = int(sheet.shape[1] * scale), int(sheet.shape[0] * scale)
    chans = [np.array(Image.fromarray(pm[..., i]).resize((nw, nh), Image.BOX)) for i in range(3)]
    al = np.array(Image.fromarray(a[..., 0]).resize((nw, nh), Image.BOX))
    rgb = np.dstack(chans) / np.maximum(al[..., None], 1e-4)
    al = np.where(al < 0.35, 0, np.where(al > 0.65, 1, al))
    outa = np.dstack([np.clip(rgb, 0, 255), al * 255]).astype(np.uint8)
    outa[al == 0] = 0
    Image.fromarray(outa, "RGBA").quantize(colors=128, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(out_png, optimize=True)
    # reference skin colour: median of skin-like pixels
    px = im[fg].reshape(-1, 3) / 255.0
    sel = []
    for p in px[:: max(1, len(px) // 40000)]:
        h, l, s = colorsys.rgb_to_hls(*p)
        if 8 / 360 <= h <= 33 / 360 and 0.3 <= l <= 0.8 and 0.25 <= s <= 0.75: sel.append(p)
    ref = (np.median(np.array(sel), 0) * 255).round().astype(int).tolist()
    return dict(cw=int(CW * scale), ch=int(CH * scale), skin=ref)

if __name__ == "__main__":
    meta = {}
    meta["male-elderly"] = build(sys.argv[1], sys.argv[3])
    meta["female-elderly"] = build(sys.argv[2], sys.argv[4], donors={0: (3, 0), 2: (3, 1)})
    print(json.dumps(meta))
