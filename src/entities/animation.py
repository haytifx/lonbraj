"""
animation.py
------------
Charge le spritesheet + son fichier JSON (generes par build_spritesheet.py
dans Spritesheet_builder) et permet de lire une animation frame par frame.

Ce fichier ne connait rien du personnage specifique (James) -- il peut
servir pour n'importe quel personnage qui a un spritesheet + JSON generes
de la meme facon. Ca permet de reutiliser ce code pour un futur PNJ/ennemi.

FORMAT DU JSON (les champs apres "frame_count" sont OPTIONNELS : un ancien
JSON qui ne les a pas continue de fonctionner) :

    {
      "frame_width": 128, "frame_height": 128,
      "animations": {
        "walk": {"row": 0, "frame_count": 12,
                 "fps": 12,            # vitesse de lecture normale
                 "loop": true,         # false = joue une fois et reste sur la derniere frame
                 "stride": 96,         # pixels parcourus au sol pendant UN cycle complet
                                       #   (sert a synchroniser la marche avec la vitesse reelle)
                 "event_frame": 1}     # frame ou un evenement se produit (ex: le coup part, la balle sort)
      }
    }

POURQUOI LE TIMER NE SE REMET PLUS A ZERO :
    L'ancienne version faisait "timer = 0" a chaque changement de frame, ce
    qui perdait le reste de temps (jusqu'a 16 ms a 60 FPS) : l'animation
    tournait plus lentement que prevu et avec un rythme irregulier. Ici on
    GARDE le reste (timer -= duree_frame), donc la cadence est exacte.
"""

import pygame
import json

DEFAULT_FPS = 8


class SpriteSheet:
    def __init__(self, image_path, json_path):
        self.sheet = pygame.image.load(image_path).convert_alpha()
        with open(json_path, "r", encoding="utf-8") as f:
            self.meta = json.load(f)
        self.frame_width = self.meta["frame_width"]
        self.frame_height = self.meta["frame_height"]
        self.animations = self.meta["animations"]  # ex: {"walk": {"row": 0, "frame_count": 8}, ...}
        self._cache = {}  # (anim, frame, flip) -> Surface (on ne decoupe/retourne qu'une fois)

    def has(self, anim_name):
        return anim_name in self.animations

    def get_frame(self, anim_name, frame_index, flip=False):
        """Retourne la frame (Surface partagee : NE PAS la modifier, faire .copy() avant)."""
        key = (anim_name, frame_index, flip)
        frame = self._cache.get(key)
        if frame is None:
            if anim_name not in self.animations:
                raise ValueError(f"Animation '{anim_name}' introuvable dans le spritesheet")
            info = self.animations[anim_name]
            frame_index = max(0, min(frame_index, info["frame_count"] - 1))
            rect = pygame.Rect(
                frame_index * self.frame_width,
                info["row"] * self.frame_height,
                self.frame_width,
                self.frame_height,
            )
            frame = self.sheet.subsurface(rect)
            if flip:
                frame = pygame.transform.flip(frame, True, False)
            self._cache[key] = frame
        return frame

    def frame_count(self, anim_name):
        return self.animations[anim_name]["frame_count"]

    # --- Champs optionnels du JSON ---
    def anim_fps(self, anim_name, default=None):
        return self.animations[anim_name].get("fps", default)

    def anim_loop(self, anim_name, default=True):
        return self.animations[anim_name].get("loop", default)

    def anim_stride(self, anim_name, default=None):
        return self.animations[anim_name].get("stride", default)

    def anim_event_frame(self, anim_name, default=0):
        return self.animations[anim_name].get("event_frame", default)


class AnimationPlayer:
    """Joue une animation en boucle (ou une seule fois) a une vitesse donnee."""

    def __init__(self, spritesheet, fps=DEFAULT_FPS):
        self.spritesheet = spritesheet
        self.fps = fps
        self.speed_scale = 1.0   # multiplicateur de vitesse (1.0 = normal)
        self.current_anim = None
        self.frame_index = 0
        self.timer = 0.0         # ms ecoulees dans la frame courante (le reste est conserve)
        self.loop = True
        self.finished = False
        self.frozen = False

    def play(self, anim_name, loop=None, restart_if_same=False, fps=None):
        """Lance une animation.
        loop=None -> utilise le champ "loop" du JSON (True si absent).
        fps=None  -> utilise le champ "fps" du JSON (sinon garde self.fps)."""
        if self.current_anim == anim_name and not restart_if_same:
            self.frozen = False  # deja en train de jouer : on s'assure juste qu'elle n'est pas figee
            return
        sheet = self.spritesheet
        self.current_anim = anim_name
        self.frame_index = 0
        self.timer = 0.0
        self.finished = False
        self.frozen = False
        self.speed_scale = 1.0
        self.loop = sheet.anim_loop(anim_name, True) if loop is None else loop
        self.fps = sheet.anim_fps(anim_name, self.fps) if fps is None else fps

    def freeze(self, frame_index=0):
        """Fige l'animation sur une frame (ex: pose immobile)."""
        self.frozen = True
        self.frame_index = frame_index
        self.timer = 0.0

    def update(self, dt):
        """dt en millisecondes."""
        if self.current_anim is None or self.finished or self.frozen:
            return
        rate = self.fps * self.speed_scale
        if rate <= 0:
            return
        frame_duration = 1000.0 / rate
        count = self.spritesheet.frame_count(self.current_anim)
        self.timer += dt
        while self.timer >= frame_duration:
            self.timer -= frame_duration   # on GARDE le reste -> cadence exacte
            self.frame_index += 1
            if self.frame_index >= count:
                if self.loop:
                    self.frame_index = 0
                else:
                    self.frame_index = count - 1
                    self.finished = True
                    self.timer = 0.0
                    break

    def get_current_frame(self, flip=False):
        if self.current_anim is None:
            return None
        return self.spritesheet.get_frame(self.current_anim, self.frame_index, flip)