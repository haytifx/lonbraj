"""
animation.py
------------
Charge le spritesheet + son fichier JSON (generes par build_spritesheet.py
dans Spritesheet_builder) et permet de lire une animation frame par frame.

Ce fichier ne connait rien du personnage specifique (James) -- il peut
servir pour n'importe quel personnage qui a un spritesheet + JSON generes
de la meme facon. Ca permet de reutiliser ce code pour un futur PNJ/ennemi.
"""

import pygame
import json


class SpriteSheet:
    def __init__(self, image_path, json_path):
        self.sheet = pygame.image.load(image_path).convert_alpha()
        with open(json_path, "r", encoding="utf-8") as f:
            self.meta = json.load(f)
        self.frame_width = self.meta["frame_width"]
        self.frame_height = self.meta["frame_height"]
        self.animations = self.meta["animations"]  # ex: {"walk": {"row": 0, "frame_count": 8}, ...}

    def get_frame(self, anim_name, frame_index):
        if anim_name not in self.animations:
            raise ValueError(f"Animation '{anim_name}' introuvable dans le spritesheet")
        row = self.animations[anim_name]["row"]
        rect = pygame.Rect(
            frame_index * self.frame_width,
            row * self.frame_height,
            self.frame_width,
            self.frame_height,
        )
        return self.sheet.subsurface(rect)

    def frame_count(self, anim_name):
        return self.animations[anim_name]["frame_count"]


class AnimationPlayer:
    """Joue une animation en boucle (ou une seule fois) a une vitesse donnee."""

    def __init__(self, spritesheet, fps=8):
        self.spritesheet = spritesheet
        self.fps = fps
        self.current_anim = None
        self.frame_index = 0
        self.timer = 0
        self.loop = True
        self.finished = False

    def play(self, anim_name, loop=True, restart_if_same=False):
        if self.current_anim == anim_name and not restart_if_same:
            return  # deja en train de jouer cette animation, on ne redemarre pas
        self.current_anim = anim_name
        self.frame_index = 0
        self.timer = 0
        self.loop = loop
        self.finished = False

    def update(self, dt):
        if self.current_anim is None or self.finished:
            return
        self.timer += dt
        frame_duration = 1000 / self.fps
        if self.timer >= frame_duration:
            self.timer = 0
            count = self.spritesheet.frame_count(self.current_anim)
            self.frame_index += 1
            if self.frame_index >= count:
                if self.loop:
                    self.frame_index = 0
                else:
                    self.frame_index = count - 1
                    self.finished = True

    def get_current_frame(self):
        if self.current_anim is None:
            return None
        return self.spritesheet.get_frame(self.current_anim, self.frame_index)
