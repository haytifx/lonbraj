#!/usr/bin/env python3
"""
build_spritesheet.py
---------------------
Assemble des frames PNG individuelles (deja sans fond, deja decoupees)
en un spritesheet unique, pret a etre utilise dans Pygame.

STRUCTURE DE DOSSIER ATTENDUE
    frames/
        walk_1.png ... walk_12.png
        sneak_1.png ...
        pistol_walk_1.png ...      <- le nom d'animation est TOUT ce qui precede le dernier "_numero"
        attack_1.png ...

POURQUOI L'ANCIENNE VERSION FAISAIT TREMBLER L'ANIMATION
    Elle redimensionnait CHAQUE frame separement pour qu'elle "remplisse" la case.
    Une frame decoupee un peu plus petite etait donc agrandie davantage : James
    changeait de taille d'une frame a l'autre, et ses pieds changeaient de hauteur.

CE QUE FAIT CETTE VERSION (mode par defaut)
    1. Rogne chaque frame au contour du personnage (bords transparents retires).
    2. Applique UNE SEULE echelle a toutes les frames d'une animation (donc James
       garde exactement la meme taille du debut a la fin), et la meme echelle a
       toutes les animations tant qu'elles viennent du meme "reglage" de dessin :
       l'echelle est calculee pour que James DEBOUT (animation de reference,
       "walk" par defaut) mesure --stand-height pixels.
    3. Pose les PIEDS de chaque frame sur la meme ligne (--ground-margin pixels du bas).
    4. Centre le HAUT DU CORPS (tete + torse) au milieu de la case : le corps ne
       "glisse" pas lateralement quand les jambes bougent, et le retournement
       gauche/droite dans le jeu ne decale pas le personnage.

UTILISATION
    python build_spritesheet.py --input frames --output james_spritesheet.png

    # Si certaines animations ont ete dessinees a une AUTRE echelle que "walk"
    # (ex: generees dans une autre image), normalise-les separement :
    python build_spritesheet.py --input frames --output james_spritesheet.png ^
        --per-anim attack,jump,hurt,dead

    # Une animation accroupie dont la hauteur max vaut 72% de la hauteur debout :
    python build_spritesheet.py ... --per-anim sneak,crouch --ratio sneak=0.72 --ratio crouch=0.72

Genere DEUX fichiers :
    james_spritesheet.png
    james_spritesheet.json   (avec fps / loop / stride par defaut pour chaque animation)

Pour VERIFIER le resultat (tailles, pieds, centrage de chaque frame) :
    python preview_animation.py --check james_spritesheet.png
"""

import argparse
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from PIL import Image

FRAME_RE = re.compile(r"^(?P<name>.+)_(?P<num>\d+)\.(png|jpg|jpeg)$", re.IGNORECASE)

# Valeurs par defaut ecrites dans le JSON (modifiables ensuite a la main dans le JSON).
#   fps          : vitesse de lecture
#   loop         : false = jouee une fois, reste sur la derniere frame
#   stride       : pixels parcourus au sol pendant UN cycle complet (marches seulement)
#   event_frame  : frame ou l'evenement a lieu (la balle part, le garde tombe...)
DEFAULT_META = {
    "idle": {"fps": 6, "loop": True},
    "walk": {"fps": 12, "loop": True, "stride": 96},
    "sneak": {"fps": 10, "loop": True, "stride": 72},
    "crouch": {"fps": 4, "loop": True},
    "jump": {"fps": 10, "loop": False},
    "attack": {"fps": 12, "loop": False},
    "hurt": {"fps": 12, "loop": False},
    "dead": {"fps": 10, "loop": False},
    "takedown": {"fps": 12, "loop": False},
    "pistol_idle": {"fps": 6, "loop": True},
    "pistol_walk": {"fps": 12, "loop": True, "stride": 96},
    "pistol_sneak": {"fps": 10, "loop": True, "stride": 72},
    "pistol_crouch": {"fps": 4, "loop": True},
    "pistol_aim": {"fps": 12, "loop": False},
    "pistol_shoot": {"fps": 12, "loop": False, "event_frame": 1},
}

ROW_ORDER = ["idle", "walk", "sneak", "crouch", "jump", "attack", "takedown", "hurt", "dead",
             "pistol_idle", "pistol_walk", "pistol_sneak", "pistol_crouch", "pistol_aim", "pistol_shoot"]

ALPHA_THRESHOLD = 8        # alpha <= 8 = considere transparent (ignore le bruit autour du contour)
BODY_FRACTION = 0.6        # le "haut du corps" = les 60% du haut de la silhouette


# ----------------------------------------------------------------------
# Lecture des frames
# ----------------------------------------------------------------------
def natural_key(filename):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', filename)]


def group_frames_by_animation(input_dir):
    groups = defaultdict(list)
    for fname in os.listdir(input_dir):
        m = FRAME_RE.match(fname)
        if not m:
            continue
        groups[m.group("name")].append((int(m.group("num")), fname))
    return {name: [f for _, f in sorted(items)] for name, items in groups.items()}


def trim(img):
    """Retire les bords transparents. Retourne l'image rognee (ou None si vide)."""
    img = img.convert("RGBA")
    mask = img.getchannel("A").point(lambda a: 255 if a > ALPHA_THRESHOLD else 0)
    box = mask.getbbox()
    return img.crop(box) if box else None


def body_center_x(img, mode):
    """Abscisse (dans img) du point d'ancrage horizontal."""
    if mode == "bbox":
        return img.width / 2
    top = img.getchannel("A").crop((0, 0, img.width, max(1, int(img.height * BODY_FRACTION))))
    column_means = list(top.resize((img.width, 1), Image.BOX).tobytes())
    total = sum(column_means)
    if total == 0:
        return img.width / 2
    return sum((x + 0.5) * a for x, a in enumerate(column_means)) / total


# ----------------------------------------------------------------------
# Construction
# ----------------------------------------------------------------------
def compute_scales(trimmed, args):
    """Retourne {nom_animation: echelle}."""
    if args.ref_anim not in trimmed and not args.legacy:
        raise SystemExit(
            f"ERREUR: l'animation de reference '{args.ref_anim}' n'existe pas dans {args.input}.\n"
            f"Animations trouvees : {', '.join(sorted(trimmed))}\n"
            f"Utilise --ref-anim NOM pour en choisir une (une animation ou James est DEBOUT)."
        )
    ref_height = statistics.median(f.height for f in trimmed[args.ref_anim])
    global_scale = args.stand_height / ref_height

    per_anim = {n.strip() for n in args.per_anim.split(",") if n.strip()}
    ratios = {}
    for item in args.ratio:
        name, _, value = item.partition("=")
        ratios[name.strip()] = float(value)

    scales = {}
    for name, frames in trimmed.items():
        if name == args.ref_anim or name not in per_anim:
            scale = global_scale
        else:
            max_height = max(f.height for f in frames)
            scale = args.stand_height * ratios.get(name, 1.0) / max_height

        # Si ca depasse la case, on reduit l'echelle de TOUTE l'animation (pas frame par frame)
        max_w = max(f.width for f in frames) * scale
        max_h = max(f.height for f in frames) * scale
        limit = min((args.frame_width - 2) / max_w, (args.frame_height - args.ground_margin - 1) / max_h, 1.0)
        if limit < 1.0:
            print(f"   ATTENTION: '{name}' depassait la case : echelle reduite de {100*(1-limit):.0f}% "
                  f"pour TOUTE l'animation. Si James parait trop petit, l'animation a probablement "
                  f"ete dessinee a une autre echelle : ajoute-la dans --per-anim.")
            scale *= limit
        scales[name] = scale
    return scales, global_scale


def place_frame(img, scale, args):
    """Redimensionne (echelle commune) et pose sur une case : pieds sur la ligne, corps centre."""
    new_size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    resample = Image.NEAREST if args.pixel_art else Image.LANCZOS
    scaled = img.resize(new_size, resample)

    canvas = Image.new("RGBA", (args.frame_width, args.frame_height), (0, 0, 0, 0))
    anchor_x = body_center_x(scaled, args.anchor)
    x = round(args.frame_width / 2 - anchor_x)
    x = max(0, min(x, args.frame_width - scaled.width))        # reste dans la case
    y = args.frame_height - args.ground_margin - scaled.height
    y = max(0, y)
    canvas.paste(scaled, (x, y), scaled)
    return canvas


def legacy_fit_frame(img, frame_width, frame_height):
    """ANCIEN comportement (chaque frame est mise a l'echelle seule). Garde pour comparaison."""
    img = img.convert("RGBA")
    ratio = min(frame_width / img.width, frame_height / img.height)
    new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    resized = img.resize(new_size, Image.LANCZOS)
    canvas = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
    canvas.paste(resized, ((frame_width - new_size[0]) // 2, frame_height - new_size[1]), resized)
    return canvas


def build_spritesheet(args):
    groups = group_frames_by_animation(args.input)
    if not groups:
        raise SystemExit(f"ERREUR: aucune image 'nom_numero.png' trouvee dans {args.input}")

    names = sorted(groups, key=lambda n: (ROW_ORDER.index(n) if n in ROW_ORDER else len(ROW_ORDER), n))

    processed = {}
    report = []
    if args.legacy:
        print("MODE ANCIEN (--legacy) : chaque frame est mise a l'echelle separement.")
        for name in names:
            processed[name] = [legacy_fit_frame(Image.open(os.path.join(args.input, f)), args.frame_width,
                                                args.frame_height) for f in groups[name]]
            report.append((name, len(groups[name]), None))
    else:
        trimmed = {}
        for name in names:
            frames = []
            for fname in groups[name]:
                t = trim(Image.open(os.path.join(args.input, fname)))
                if t is None:
                    raise SystemExit(f"ERREUR: {fname} est completement transparente.")
                frames.append(t)
            trimmed[name] = frames
        scales, global_scale = compute_scales(trimmed, args)
        print(f"Echelle de reference ('{args.ref_anim}') : x{global_scale:.3f}  "
              f"-> James debout = {args.stand_height}px dans une case {args.frame_width}x{args.frame_height}")
        for name in names:
            processed[name] = [place_frame(f, scales[name], args) for f in trimmed[name]]
            report.append((name, len(trimmed[name]), scales[name]))

    max_cols = args.columns or max(len(f) for f in processed.values())
    sheet = Image.new("RGBA", (args.frame_width * max_cols, args.frame_height * len(processed)), (0, 0, 0, 0))
    metadata = {"frame_width": args.frame_width, "frame_height": args.frame_height, "animations": {}}
    for row, name in enumerate(processed):
        entry = {"row": row, "frame_count": len(processed[name])}
        entry.update(DEFAULT_META.get(name, {}))
        metadata["animations"][name] = entry
        for col, frame in enumerate(processed[name]):
            sheet.paste(frame, (col * args.frame_width, row * args.frame_height), frame)

    sheet.save(args.output)
    json_path = os.path.splitext(args.output)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"OK: {args.output}  ({sheet.width}x{sheet.height}px, {len(processed)} lignes, {max_cols} colonnes max)")
    print(f"OK: {json_path}")
    for name, count, scale in report:
        extra = f"echelle x{scale:.3f}" if scale else ""
        known = "" if name in DEFAULT_META else "   (nom inconnu du jeu : fps/loop a regler a la main)"
        print(f"   - {name:14s} {count:2d} frames  ligne {metadata['animations'][name]['row']}  {extra}{known}")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Assemble des frames PNG en spritesheet (echelle et ancrage coherents)")
    p.add_argument("--input", required=True, help="Dossier contenant les frames (nom_1.png, nom_2.png...)")
    p.add_argument("--output", required=True, help="Chemin du spritesheet PNG de sortie")
    p.add_argument("--frame-width", type=int, default=128)
    p.add_argument("--frame-height", type=int, default=128)
    p.add_argument("--columns", type=int, default=None, help="Forcer le nombre de colonnes")
    p.add_argument("--stand-height", type=int, default=108, help="Hauteur de James debout en pixels (defaut 108)")
    p.add_argument("--ref-anim", default="walk", help="Animation ou James est debout, sert de reference d'echelle")
    p.add_argument("--per-anim", default="", help="Animations a mettre a l'echelle separement (liste separee par des virgules)")
    p.add_argument("--ratio", action="append", default=[], metavar="NOM=0.75",
                   help="Pour une animation --per-anim : sa hauteur max = ratio x stand-height (repetable)")
    p.add_argument("--ground-margin", type=int, default=4, help="Pixels entre les pieds et le bas de la case")
    p.add_argument("--anchor", choices=["body", "bbox"], default="body",
                   help="Centrage horizontal : haut du corps (defaut) ou centre de la boite")
    p.add_argument("--pixel-art", action="store_true", help="Redimensionne sans lissage (pixel art)")
    p.add_argument("--legacy", action="store_true", help="Ancien comportement (pour comparer)")
    return p.parse_args(argv)


if __name__ == "__main__":
    build_spritesheet(parse_args())