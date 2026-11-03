"""
level_transition_scene.py
---------------------------
Ecran noir avec un titre (ex: "CHAPIT 1 - ENFILTRASYON") qui joue une
musique d'action pendant TRANSITION_DURATION_MS, avant de lancer le
niveau jouable. Sert de "sas" entre la cinematique narrative et le
gameplay -- change le rythme, signale au joueur que l'action commence.

Le joueur peut aussi appuyer sur une touche pour passer plus vite.

MUSIQUE ATTENDUE : assets/audio/music/<nom donne en parametre>
"""

import pygame
import settings
from src.audio.audio_manager import audio

TRANSITION_DURATION_MS = 2500
FADE_DURATION_MS = 400


class LevelTransitionScene:
    def __init__(self, title, on_finish, music_file=None):
        self.title = title
        self.on_finish = on_finish
        self.music_file = music_file
        self.timer = 0
        self.finished = False

        self.title_font = pygame.font.Font(None, 60)
        self.hint_font = pygame.font.Font(None, 26)

        if self.music_file:
            audio.play_music(self.music_file, loop=False)

    def handle_event(self, event):
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            if not self.finished:
                self.finished = True
                self.on_finish()

    def update(self, dt):
        if self.finished:
            return
        self.timer += dt
        if self.timer >= TRANSITION_DURATION_MS:
            self.finished = True
            self.on_finish()

    def draw(self, surface):
        surface.fill(settings.COLOR_BLACK)

        title_surface = self.title_font.render(self.title, True, settings.COLOR_WHITE)
        title_rect = title_surface.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2))

        # Fondu d'entree/sortie du titre
        alpha = 255
        if self.timer < FADE_DURATION_MS:
            alpha = int(255 * (self.timer / FADE_DURATION_MS))
        elif self.timer > TRANSITION_DURATION_MS - FADE_DURATION_MS:
            remaining = TRANSITION_DURATION_MS - self.timer
            alpha = int(255 * max(0, remaining) / FADE_DURATION_MS)
        title_surface.set_alpha(max(0, min(255, alpha)))

        surface.blit(title_surface, title_rect)

        hint = self.hint_font.render("Peze pou pase", True, settings.COLOR_WHITE)
        hint.set_alpha(120)
        surface.blit(hint, (30, settings.SCREEN_HEIGHT - 40))
