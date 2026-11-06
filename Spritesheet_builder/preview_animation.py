#!/usr/bin/env python3
"""
preview_animation.py
---------------------
Outil pour VOIR et VERIFIER une animation avant de l'utiliser dans le jeu.

1) VERIFIER un spritesheet (taille, pieds, centrage de chaque frame) -- sans fenetre :
       python preview_animation.py --check james_spritesheet.png
   Affiche, pour chaque animation, la hauteur du personnage, la ligne des pieds et le
   centre horizontal de chaque frame, avec un AVERTISSEMENT si quelque chose varie
   trop (c'est exactement ce qui fait trembler une animation). Utilise-le sur le
   spritesheet venant de Gemini et sur celui du builder pour voir la difference.

2) JOUER l'animation dans une fenetre, comme dans le jeu (le sol defile a la vitesse
   reelle ; si les pieds glissent, ajuste le stride) :
       python preview_animation.py james_spritesheet.png --anim walk --speed 220
   Touches :  HAUT/BAS = vitesse  |  [ et ] = stride -/+  |  ESPACE = pause
              GAUCHE/DROITE = retourner  |  ECHAP = quitter
   Le stride affiche = pixels parcourus au sol pendant UN cycle complet. Quand les pieds
   ne glissent plus, copie cette valeur dans le JSON ("stride") de l'animation.

3) EXPORTER un GIF (a ouvrir ou a m'envoyer) :
       python preview_animation.py james_spritesheet.png --anim walk --speed 220 --gif walk.gif

Le JSON doit se trouver a cote du PNG (meme nom, extension .json).
"""

import argparse
import json
import os
import sys
from PIL import Image, ImageDraw

ALPHA_THRESHOLD = 8


def load(sheet_path, json_path=None):
    json_path = json_path or os.path.splitext(sheet_path)[0] + ".json"
    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return Image.open(sheet_path).convert("RGBA"), meta


def frame_image(sheet, meta, anim, index):
    fw, fh = meta["frame_width"], meta["frame_height"]
    row = meta["animations"][anim]["row"]
    return sheet.crop((index * fw, row * fh, (index + 1) * fw, (row + 1) * fh))


def measure(frame):
    """(hauteur, y_pieds, x_centre_haut_du_corps) ou None si vide."""
    alpha = frame.getchannel("A").point(lambda a: 255 if a > ALPHA_THRESHOLD else 0)
    box = alpha.getbbox()
    if not box:
        return None
    height = box[3] - box[1]
    top = frame.getchannel("A").crop((0, box[1], frame.width, box[1] + max(1, int(height * 0.6))))
    cols = list(top.resize((frame.width, 1), Image.BOX).tobytes())
    total = sum(cols)
    cx = sum((x + 0.5) * a for x, a in enumerate(cols)) / total if total else (box[0] + box[2]) / 2
    return height, box[3], cx


# ----------------------------------------------------------------------
def check(sheet_path, json_path, only=None):
    sheet, meta = load(sheet_path, json_path)
    fw, fh = meta["frame_width"], meta["frame_height"]
    print(f"{sheet_path}: cases {fw}x{fh}, {len(meta['animations'])} animations\n")
    problems = 0
    for name, info in meta["animations"].items():
        if only and name != only:
            continue
        rows = [measure(frame_image(sheet, meta, name, i)) for i in range(info["frame_count"])]
        if any(r is None for r in rows):
            print(f"{name}: une frame est vide !")
            problems += 1
            continue
        heights = [r[0] for r in rows]
        feet = [r[1] for r in rows]
        centers = [round(r[2], 1) for r in rows]
        warn = []
        h_var = (max(heights) - min(heights)) / max(heights) * 100
        # Pour les animations ou le corps change de forme (mort, saut...), la hauteur varie
        # normalement : on n'avertit que pour les animations de marche / pose debout.
        steady = name.replace("pistol_", "") in ("idle", "walk", "sneak", "crouch")
        if steady and h_var > 6:
            warn.append(f"la hauteur varie de {h_var:.0f}% (James change de taille)")
        if steady and max(feet) - min(feet) > 2:
            warn.append(f"les pieds varient de {max(feet) - min(feet)}px en hauteur")
        if max(centers) - min(centers) > 4:
            warn.append(f"le corps se decale de {max(centers) - min(centers):.0f}px lateralement")
        problems += bool(warn)
        flag = "  <-- " + " ; ".join(warn) if warn else ""
        print(f"{name} ({info['frame_count']} frames){flag}")
        print(f"    hauteur : {heights}")
        print(f"    pieds y : {feet}")
        print(f"    centre x: {centers}")
    print("\n" + ("Aucun probleme detecte." if not problems else f"{problems} animation(s) avec avertissement."))
    return problems


# ----------------------------------------------------------------------
class Simulation:
    """Simule le jeu : la vitesse fait avancer le sol ET l'animation (meme formule que player.py)."""
    def __init__(self, meta, anim, speed, stride):
        self.meta, self.anim = meta, anim
        self.count = meta["animations"][anim]["frame_count"]
        self.speed = speed
        self.stride = stride
        self.index = 0
        self.timer = 0.0
        self.ground = 0.0

    @property
    def fps(self):
        return self.count * abs(self.speed) / self.stride if self.stride > 0 else 0

    def step(self, dt_ms, paused=False):
        if paused:
            return
        self.ground = (self.ground + self.speed * dt_ms / 1000) % 64
        if self.fps <= 0:
            return
        frame_ms = 1000 / self.fps
        self.timer += dt_ms
        while self.timer >= frame_ms:
            self.timer -= frame_ms
            self.index = (self.index + 1) % self.count


def render(sim, sheet, meta, flip=False, scale=2, size=(480, 300)):
    img = Image.new("RGBA", size, (30, 33, 42, 255))
    d = ImageDraw.Draw(img)
    fw, fh = meta["frame_width"], meta["frame_height"]
    ground_y = size[1] - 50
    d.rectangle((0, ground_y, size[0], size[1]), fill=(55, 58, 70, 255))
    # reperes de sol qui defilent (si les pieds glissent, ils ne "collent" pas a ces reperes)
    step = 64 * scale
    offset = (-sim.ground * scale) % step
    x = offset - step
    while x < size[0]:
        d.line((x, ground_y, x, ground_y + 14), fill=(200, 200, 210, 255), width=2)
        x += step
    frame = frame_image(sheet, meta, sim.anim, sim.index)
    frame = frame.resize((fw * scale, fh * scale), Image.NEAREST)
    if flip:
        frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
    img.paste(frame, ((size[0] - frame.width) // 2, ground_y - frame.height + 4 * scale), frame)
    d.text((8, 8), f"{sim.anim}  frame {sim.index + 1}/{sim.count}  vitesse {sim.speed:.0f}px/s  "
                   f"stride {sim.stride:.0f}px  -> {sim.fps:.1f} fps", fill=(235, 235, 240, 255))
    return img.convert("RGB")


def export_gif(sheet, meta, anim, speed, stride, out_path, seconds=2.0):
    sim = Simulation(meta, anim, speed, stride)
    frames = []
    for _ in range(int(seconds * 60)):
        sim.step(1000 / 60)
        frames.append(render(sim, sheet, meta))
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=1000 // 60 * 2,
                   loop=0, optimize=False)
    print(f"GIF ecrit : {out_path} ({len(frames)} images, {seconds:.0f}s simulees a 60 FPS)")


def play_window(sheet, meta, anim, speed, stride):
    import pygame
    pygame.init()
    size = (480, 300)
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption("preview_animation")
    clock = pygame.time.Clock()
    sim = Simulation(meta, anim, speed, stride)
    paused, flip, running = False, False, True
    while running:
        dt = clock.tick(60)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key == pygame.K_UP:
                    sim.speed += 10
                elif e.key == pygame.K_DOWN:
                    sim.speed = max(0, sim.speed - 10)
                elif e.key == pygame.K_LEFTBRACKET:
                    sim.stride = max(8, sim.stride - 4)
                elif e.key == pygame.K_RIGHTBRACKET:
                    sim.stride += 4
                elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    flip = e.key == pygame.K_LEFT
        sim.step(dt, paused)
        img = render(sim, sheet, meta, flip)
        screen.blit(pygame.image.fromstring(img.tobytes(), img.size, "RGB"), (0, 0))
        pygame.display.flip()
    print(f"Dernier reglage : speed={sim.speed:.0f}  stride={sim.stride:.0f}")
    pygame.quit()


def main():
    p = argparse.ArgumentParser(description="Verifier / jouer / exporter une animation de spritesheet")
    p.add_argument("sheet", nargs="?", help="Spritesheet PNG")
    p.add_argument("--check", metavar="SHEET", help="Verifie un spritesheet (sans fenetre)")
    p.add_argument("--json", default=None, help="Chemin du JSON (defaut : meme nom que le PNG)")
    p.add_argument("--anim", default=None, help="Animation a jouer (defaut walk) ou a verifier seule (avec --check)")
    p.add_argument("--speed", type=float, default=220, help="Vitesse au sol en px/s (defaut 220 = WALK_SPEED)")
    p.add_argument("--stride", type=float, default=None, help="Pixels par cycle (defaut : champ 'stride' du JSON, sinon 96)")
    p.add_argument("--gif", default=None, help="Ecrit un GIF au lieu d'ouvrir une fenetre")
    args = p.parse_args()

    if args.check:
        sys.exit(1 if check(args.check, args.json, args.anim) else 0)
    if not args.sheet:
        p.error("donne un spritesheet, ou utilise --check")
    anim = args.anim or "walk"
    sheet, meta = load(args.sheet, args.json)
    if anim not in meta["animations"]:
        sys.exit(f"Animation '{anim}' introuvable. Disponibles : {', '.join(meta['animations'])}")
    stride = args.stride or meta["animations"][anim].get("stride", 96)
    if args.gif:
        export_gif(sheet, meta, anim, args.speed, stride, args.gif)
    else:
        play_window(sheet, meta, anim, args.speed, stride)


if __name__ == "__main__":
    main()
