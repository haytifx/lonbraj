"""
split_and_clean.py : bann Gemini (fon vet) -> frames/<non>_N.png transparan.
Egzanp : python split_and_clean.py --input gemini_raw\walk_strip_james.jpg --name walk --frames 8
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw


def green_dominance(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return g - np.maximum(r, b)


def estimate_bg_dominance(gd):
    border = np.concatenate([gd[:4].ravel(), gd[:, :4].ravel(), gd[:, -4:].ravel()])
    return float(np.median(border))


def keyed_alpha(rgb, bg_gd):
    gd = green_dominance(rgb)
    lo, hi = 0.25 * bg_gd, 0.70 * bg_gd
    return np.clip(1.0 - (gd - lo) / (hi - lo), 0.0, 1.0)


def despill(rgb, alpha):
    out = rgb.copy()
    cap = np.maximum(out[..., 0], out[..., 2])
    edge = (alpha > 0) & (alpha < 1.0)
    g = out[..., 1]
    g[edge] = np.minimum(g[edge], cap[edge])
    inner = alpha >= 1.0
    over = inner & (g > cap)
    g[over] = cap[over]
    out[..., 1] = g
    return out


def largest_blob_mask(mask):
    try:
        from scipy import ndimage
        lab, n = ndimage.label(mask)
        if n <= 1:
            return mask
        sizes = ndimage.sum(mask, lab, range(1, n + 1))
        return lab == (1 + int(np.argmax(sizes)))
    except Exception:
        return mask


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--frames", type=int, default=8)
    ap.add_argument("--output-dir", default="frames")
    ap.add_argument("--preview", default=None)
    ap.add_argument("--pad", type=int, default=6)
    ap.add_argument("--ignore-bottom", type=int, default=0)
    ap.add_argument("--no-despill", action="store_true")
    ap.add_argument("--anchor", choices=["head", "bbox"], default="head")
    ap.add_argument("--match-height", type=int, default=0)
    ap.add_argument("--scale", type=float, default=0.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    img = Image.open(a.input).convert("RGB")
    rgb = np.asarray(img).astype(np.int32)
    H, W = rgb.shape[:2]
    gd = green_dominance(rgb)
    bg_gd = estimate_bg_dominance(gd)
    if bg_gd < 30:
        sys.exit(f"ERE: fon an pa sanble vet (dominans {bg_gd:.0f}).")

    alpha = keyed_alpha(rgb, bg_gd)
    if a.ignore_bottom:
        alpha[H - a.ignore_bottom:, :] = 0.0

    cell = W / a.frames
    frames = []
    problems = []
    for i in range(a.frames):
        x0, x1 = int(round(i * cell)), int(round((i + 1) * cell))
        al = alpha[:, x0:x1].copy()
        solid = largest_blob_mask(al > 0.5)
        al[~largest_blob_mask(al > 0.2)] = 0.0
        ys, xs = np.where(solid)
        if len(ys) < 500:
            sys.exit(f"ERE: frame {i+1} preske vid. Kantite figi pa {a.frames}?")
        if xs.min() <= 1 or xs.max() >= (x1 - x0 - 2):
            problems.append(f"frame {i+1} touche bo kad li a (figi koupe oswa 2 figi kole).")
        top, bot = ys.min(), ys.max()
        upper = solid[top: top + int(0.45 * (bot - top)), :]
        uy, ux = np.where(upper)
        head_x = x0 + float(ux.mean())
        if a.anchor == "bbox":
            head_x = x0 + (xs.min() + xs.max()) / 2.0
        frames.append((rgb[:, x0:x1], al, head_x - x0, x0, top, bot, xs.min() + x0, xs.max() + x0))

    tops = [f[4] for f in frames]
    bots = [f[5] for f in frames]
    heights = [b - t for t, b in zip(tops, bots)]
    print(f"{a.frames} frame, sous {W}x{H}, dominans vet fon {bg_gd:.0f}")
    print("  otè figi :", [int(h) for h in heights], f"(varyasyon {100*(max(heights)-min(heights))/max(heights):.1f} %)")
    print("  pye (y)  :", [int(b) for b in bots])
    ground = int(np.median(bots))
    print(f"  liy tè chwazi = {ground}")
    lifted = [i + 1 for i, b in enumerate(bots) if abs(b - ground) > 3]
    if lifted:
        print(f"  frame ak pye leve (nòmal nan yon pa): {lifted}")

    top_y = max(0, min(tops) - a.pad)
    bot_y = min(H, ground + a.pad + 1)
    half = 0
    for (_, _, hx, x0, _, _, xl, xr) in frames:
        half = max(half, int(np.ceil(max((x0 + hx) - xl, xr - (x0 + hx)))))
    half += a.pad
    cw, ch = 2 * half, bot_y - top_y
    print(f"  kad final = {cw}x{ch} px")

    if a.dry_run:
        for p in problems:
            print("ATANSYON:", p)
        return

    os.makedirs(a.output_dir, exist_ok=True)
    out_frames = []
    for i, (crgb, cal, hx, x0, *_rest) in enumerate(frames):
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        sx0 = int(round(hx - half))
        sx_lo, sx_hi = sx0, sx0 + cw
        src_lo, src_hi = max(0, sx_lo), min(crgb.shape[1], sx_hi)
        dst_lo = src_lo - sx_lo
        sub_rgb = crgb[top_y:bot_y, src_lo:src_hi].copy()
        sub_al = cal[top_y:bot_y, src_lo:src_hi]
        if not a.no_despill:
            sub_rgb = despill(sub_rgb, sub_al)
        canvas[:, dst_lo:dst_lo + (src_hi - src_lo), :3] = np.clip(sub_rgb, 0, 255)
        canvas[:, dst_lo:dst_lo + (src_hi - src_lo), 3] = (sub_al * 255).astype(np.uint8)
        im = Image.fromarray(canvas, "RGBA")
        out_frames.append(im)
        im.save(os.path.join(a.output_dir, f"{a.name}_{i+1}.png"))

    scale = 1.0
    if a.match_height or a.scale:
        scale = a.scale if a.scale else a.match_height / float(heights[0])
        out_frames = [im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
                      for im in out_frames]
        for i, im in enumerate(out_frames):
            im.save(os.path.join(a.output_dir, f"{a.name}_{i+1}.png"))
        cw, ch = out_frames[0].size
        print(f"  redimansyone x{scale:.3f} (frame 1 = {round(heights[0]*scale)} px), nouvo kad = {cw}x{ch}")

    prev_path = a.preview or os.path.join(a.output_dir, f"_preview_{a.name}.png")
    sheet = Image.new("RGBA", (cw * a.frames, ch), (90, 90, 90, 255))
    for i, im in enumerate(out_frames):
        sheet.alpha_composite(im, (i * cw, 0))
    d = ImageDraw.Draw(sheet)
    gy = int(round((ground - top_y) * scale))
    d.line([(0, gy), (sheet.width, gy)], fill=(255, 60, 60, 255), width=1)
    sheet.convert("RGB").save(prev_path)

    for p in problems:
        print("ATANSYON:", p)
    print(f"OK: {a.frames} frame ekri nan {os.path.join(a.output_dir, a.name)}_1.png ... _{a.frames}.png")
    print(f"Imaj kontwol: {prev_path}")


if __name__ == "__main__":
    main()