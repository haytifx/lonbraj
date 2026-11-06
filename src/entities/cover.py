"""
cover.py
--------
Un obstacle derriere lequel James peut se cacher (caisse, mur bas, barriere...).

REGLE : quand James est ACCROUPI (touche BAS) et que son centre est devant
l'obstacle, les gardes ne le voient plus. Debout, il reste visible.
L'obstacle est dessine PAR-DESSUS James (premier plan), donc James apparait
derriere.

IMAGE : un PNG a fond transparent dans
    assets/props/<nom_du_fichier>.png
Il est redimensionne pour que sa HAUTEUR soit egale a `height` (proportions
conservees) -- donne n'importe quelle taille d'image, regle la hauteur dans
main.py. Pour que ca paraisse juste : James debout fait ~108 px de haut et
accroupi ~75 px, donc un obstacle de ~85-95 px cache un James accroupi mais
laisse depasser un James debout.

Sans image (ou si le fichier n'existe pas encore) : une caisse grise de
remplacement est dessinee.
"""

import os
import pygame

PROPS_DIR = "assets/props"


class Cover:
    def __init__(self, x, ground_y, width=140, height=90, image=None):
        """x = bord gauche ; ground_y = hauteur du sol ; image = nom du fichier PNG (optionnel)."""
        self.image = None
        if image:
            path = os.path.join(PROPS_DIR, image)
            if os.path.exists(path):
                original = pygame.image.load(path).convert_alpha()
                ratio = height / original.get_height()
                size = (max(1, int(original.get_width() * ratio)), height)
                self.image = pygame.transform.smoothscale(original, size)
                width = size[0]
            else:
                print(f"[Cover] Image introuvable : {path} (caisse de remplacement utilisee)")
        self.rect = pygame.Rect(x, ground_y - height, width, height)

    def hides(self, center_x):
        """True si un joueur dont le centre est en center_x est devant l'obstacle."""
        return self.rect.left <= center_x <= self.rect.right

    def draw(self, surface, camera_x):
        screen_rect = self.rect.move(-camera_x, 0)
        if self.image:
            surface.blit(self.image, screen_rect.topleft)
            return
        pygame.draw.rect(surface, (78, 70, 60), screen_rect)
        pygame.draw.rect(surface, (120, 108, 90), screen_rect, 3)
        pygame.draw.line(surface, (120, 108, 90), screen_rect.topleft, screen_rect.bottomright, 2)
        pygame.draw.line(surface, (120, 108, 90), screen_rect.bottomleft, screen_rect.topright, 2)
