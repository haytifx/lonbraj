"""
splash_scene.py
----------------
Le tout premier ecran qui s'affiche au lancement du jeu. Il reste affiche
INDEFINIMENT tant que le joueur n'a pas appuye sur une touche, clique, ou
tape sur l'ecran (mobile) -- pas de delai automatique. C'est volontaire :
sur mobile en particulier, un timer automatique peut faire "sauter" l'ecran
avant meme que le joueur ait eu le temps de le voir.

IMAGE ATTENDUE :
    assets/ui/splash.png  (1280x720)
"""

import pygame
import os
import math
import settings


FADE_IN_DURATION_MS = 800   # fondu d'entree de l'image
HINT_DELAY_MS = 1000        # le texte "Tape ekran..." attend que l'image soit visible avant d'apparaitre
HINT_PULSE_PERIOD_MS = 1600  # duree d'un cycle complet de pulsation (fade in + fade out)
HINT_MIN_ALPHA = 40          # opacite minimale pendant la pulsation
HINT_MAX_ALPHA = 255          # opacite maximale pendant la pulsation


class SplashScene:
    def __init__(self, on_finish):
        """on_finish : fonction appelee des que le joueur interagit."""
        self.on_finish = on_finish
        self.timer = 0
        self.finished = False

        path = os.path.join(settings.UI_DIR, "splash.png")
        if os.path.exists(path):
            self.image = pygame.image.load(path).convert()
            self.image = pygame.transform.scale(
                self.image, (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
            )
        else:
            self.image = None
            print(f"[SplashScene] Image introuvable : {path} (fond noir utilise en attendant)")

        self.font = pygame.font.Font(None, 40)

    def handle_event(self, event):
        # KEYDOWN = clavier, MOUSEBUTTONDOWN = clic souris (et tap tactile sur
        # la plupart des plateformes), FINGERDOWN = tap tactile explicite (mobile)
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            if not self.finished:
                self.finished = True
                self.on_finish()

    def update(self, dt):
        # Pas de passage automatique -- on attend uniquement une action du joueur.
        self.timer += dt

    def draw(self, surface):
        surface.fill(settings.COLOR_BLACK)

        if self.image:
            surface.blit(self.image, (0, 0))
        else:
            title = self.font.render(settings.GAME_TITLE, True, settings.COLOR_WHITE)
            rect = title.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2))
            surface.blit(title, rect)

        # Fondu d'entree seulement (l'ecran s'eclaircit au debut, mais ne
        # disparait jamais tout seul -- il faut une action du joueur)
        if self.timer < FADE_IN_DURATION_MS:
            alpha = int(255 * (1 - self.timer / FADE_IN_DURATION_MS))
            fade_surface = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
            fade_surface.fill(settings.COLOR_BLACK)
            fade_surface.set_alpha(alpha)
            surface.blit(fade_surface, (0, 0))

        hint = self.font.render("Tape ekran an pou kontinye", True, settings.COLOR_WHITE)

        # Le texte n'apparait qu'apres HINT_DELAY_MS (pour capter l'attention
        # sur l'image d'abord), puis pulse en boucle (fade in/out doux) pour
        # attirer l'oeil du joueur vers l'action a faire.
        time_since_hint_start = self.timer - HINT_DELAY_MS
        if time_since_hint_start >= 0:
            cycle_position = (time_since_hint_start % HINT_PULSE_PERIOD_MS) / HINT_PULSE_PERIOD_MS
            pulse = (math.sin(cycle_position * 2 * math.pi - math.pi / 2) + 1) / 2  # 0 -> 1 -> 0 en douceur
            alpha = int(HINT_MIN_ALPHA + pulse * (HINT_MAX_ALPHA - HINT_MIN_ALPHA))
            hint.set_alpha(alpha)
            surface.blit(hint, (30, settings.SCREEN_HEIGHT - 50))
