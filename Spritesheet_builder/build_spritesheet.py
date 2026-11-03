#!/usr/bin/env python3
"""
build_spritesheet.py
---------------------
Assemble des frames PNG individuelles (deja sans fond, deja decoupees)
en un spritesheet unique, pret a etre utilise dans Pygame.

STRUCTURE DE DOSSIER ATTENDUE
    frames/
        walk_1.png
        walk_2.png
        ...
        attack_1.png
        ...

Les fichiers sont regroupes par prefixe avant le "_" (walk, attack,
jump, hurt, dead...), tries par le numero qui suit.

UTILISATION
    python build_spritesheet.py --input frames --output james_spritesheet.png \
        --frame-width 128 --frame-height 128

Genere DEUX fichiers :
    james_spritesheet.png
    james_spritesheet.json
"""

import argparse
import json
import os
import re
from collections import defaultdict
from PIL import Image


def natural_key(filename):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', filename)]


def group_frames_by_animation(input_dir):
    groups = defaultdict(list)
    for fname in os.listdir(input_dir):
        if not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue
        prefix = fname.split('_')[0]
        groups[prefix].append(fname)

    for prefix in groups:
        groups[prefix].sort(key=natural_key)

    return groups


def fit_frame(img, frame_width, frame_height):
    """Redimensionne en conservant les proportions, aligne en bas et centre
    horizontalement dans un canvas transparent de la taille demandee."""
    img = img.convert("RGBA")
    ratio = min(frame_width / img.width, frame_height / img.height)
    new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    resized = img.resize(new_size, Image.LANCZOS)

    canvas = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
    x = (frame_width - new_size[0]) // 2
    y = frame_height - new_size[1]  # aligne en bas
    canvas.paste(resized, (x, y), resized)
    return canvas


def build_spritesheet(input_dir, output_path, frame_width, frame_height, columns=None):
    groups = group_frames_by_animation(input_dir)
    if not groups:
        raise ValueError(f"Aucune image trouvee dans {input_dir}")

    metadata = {"frame_width": frame_width, "frame_height": frame_height, "animations": {}}

    processed_by_anim = {}
    max_cols = 0
    for anim_name, filenames in groups.items():
        processed = []
        for fname in filenames:
            path = os.path.join(input_dir, fname)
            img = Image.open(path)
            img = fit_frame(img, frame_width, frame_height)
            processed.append(img)
        processed_by_anim[anim_name] = processed
        max_cols = max(max_cols, len(processed))

    if columns:
        max_cols = columns

    total_rows = len(processed_by_anim)
    sheet_width = frame_width * max_cols
    sheet_height = frame_height * total_rows
    sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

    row = 0
    for anim_name, frames in processed_by_anim.items():
        metadata["animations"][anim_name] = {"row": row, "frame_count": len(frames)}
        for col, frame_img in enumerate(frames):
            sheet.paste(frame_img, (col * frame_width, row * frame_height), frame_img)
        row += 1

    sheet.save(output_path)

    json_path = os.path.splitext(output_path)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"OK: Spritesheet sauvegarde : {output_path}")
    print(f"OK: Metadonnees sauvegardees : {json_path}")
    print(f"   Taille : {sheet_width}x{sheet_height}px, {total_rows} lignes, {max_cols} colonnes max")
    for anim_name, info in metadata["animations"].items():
        print(f"   - {anim_name}: {info['frame_count']} frames (ligne {info['row']})")


def main():
    parser = argparse.ArgumentParser(description="Assemble des frames PNG en spritesheet")
    parser.add_argument("--input", required=True, help="Dossier contenant les frames individuelles")
    parser.add_argument("--output", required=True, help="Chemin du spritesheet PNG de sortie")
    parser.add_argument("--frame-width", type=int, required=True, help="Largeur de chaque frame en px")
    parser.add_argument("--frame-height", type=int, required=True, help="Hauteur de chaque frame en px")
    parser.add_argument("--columns", type=int, default=None,
                         help="Forcer un nombre fixe de colonnes (sinon auto = max frames d'une animation)")
    args = parser.parse_args()

    build_spritesheet(
        input_dir=args.input,
        output_path=args.output,
        frame_width=args.frame_width,
        frame_height=args.frame_height,
        columns=args.columns,
    )


if __name__ == "__main__":
    main()
