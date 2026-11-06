"""
projectile.py
-------------
La balle du 9mm silencieux.

ANIMATION DE LA BALLE (optionnelle) : une bande horizontale de frames CARREES
    assets/projectiles/bullet.png
Chaque frame est un carre (largeur = hauteur de l'image), donc une image de
64x16 n'est PAS valide ; une bande de 4 frames de 16x16 = 64x16 l'est.
La balle est dessinee VERS LA DROITE ; le jeu la retourne tout seul si elle
part vers la gauche. Sans ce fichier, une petite trainee jaune est dessinee.

Pas de flash de bouche : c'est un silencieux.
"""

import os
import pygame

BULLET_STRIP = "assets/projectiles/bullet.png"
BULLET_SPEED = 1400      # pixels/s
BULLET_RANGE = 900       # pixels avant de disparaitre
BULLET_ANIM_FPS = 24

_strip_cache = {}


def _load_frames(path):
    """Decoupe la bande en frames carrees (retourne [] si le fichier n'existe pas)."""
    if path in _strip_cache:
        return _strip_cache[path]
    frames = []
    if os.path.exists(path):
        strip = pygame.image.load(path).convert_alpha()
        size = strip.get_height()
        for i in range(max(1, strip.get_width() // size)):
            frames.append(strip.subsurface(pygame.Rect(i * size, 0, size, size)))
    _strip_cache[path] = frames
    return frames


class Bullet:
    def __init__(self, x, y, facing_right):
        self.x = float(x)
        self.y = float(y)
        self.facing_right = facing_right
        self.vel_x = BULLET_SPEED if facing_right else -BULLET_SPEED
        self.travelled = 0.0
        self.alive = True
        self.age_ms = 0.0
        self.frames = _load_frames(BULLET_STRIP)

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 8, int(self.y) - 3, 16, 6)

    def update(self, dt_ms):
        step = self.vel_x * dt_ms / 1000
        self.x += step
        self.travelled += abs(step)
        self.age_ms += dt_ms
        if self.travelled >= BULLET_RANGE:
            self.alive = False

    def draw(self, surface, camera_x):
        sx = int(self.x - camera_x)
        sy = int(self.y)
        if self.frames:
            index = int(self.age_ms * BULLET_ANIM_FPS / 1000) % len(self.frames)
            frame = self.frames[index]
            if not self.facing_right:
                frame = pygame.transform.flip(frame, True, False)
            surface.blit(frame, frame.get_rect(center=(sx, sy)))
        else:
            direction = 1 if self.facing_right else -1
            pygame.draw.line(surface, (255, 235, 140), (sx - direction * 22, sy), (sx, sy), 2)
            pygame.draw.circle(surface, (255, 255, 220), (sx, sy), 3)
