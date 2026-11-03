"""
menu_scene.py
-------------
Menu principal. Les options changent selon si le joueur a deja une
progression sauvegardee (voir save_manager.py) :

- Nouvelle partie -> "Jwe"
- Partie deja commencee -> "Kontinye"

Toujours presents : "Chwazi Chapit", "Opsyon", "Kite".

DESIGN : le texte est aligne sur le cote droit de l'ecran (pas au centre)
pour laisser voir l'image de fond complete a gauche. L'option selectionnee
devient dore/neon et grossit legerement pour bien se distinguer.

IMAGE ATTENDUE : assets/ui/menu_background.png (1280x720)
MUSIQUE ATTENDUE : assets/audio/music/menu_theme.ogg
SON DE CONFIRMATION ATTENDU : assets/audio/sfx/menu_confirm.wav (joue a chaque selection)
"""

import pygame
import os
import settings
from src.audio.audio_manager import audio
from src.save_manager import save_manager

RIGHT_MARGIN = 100          # distance entre le bord droit de l'ecran et le texte
NORMAL_FONT_SIZE = 42
SELECTED_FONT_SIZE = 56      # l'option selectionnee est plus grande
ITEM_SPACING = 75


class MenuScene:
    def __init__(self, on_play, on_chapter_select):
        self.on_play = on_play
        self.on_chapter_select = on_chapter_select
        self.selected = 0

        path = os.path.join(settings.UI_DIR, "menu_background.png")
        if os.path.exists(path):
            self.background = pygame.image.load(path).convert()
            self.background = pygame.transform.scale(
                self.background, (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
            )
        else:
            self.background = None
            print(f"[MenuScene] Image introuvable : {path} (fond uni utilise en attendant)")

        self.title_font = pygame.font.Font(None, 80)
        self.normal_font = pygame.font.Font(None, NORMAL_FONT_SIZE)
        self.selected_font = pygame.font.Font(None, SELECTED_FONT_SIZE)

        audio.play_music("menu_theme.ogg")
        self._build_options()
        self.option_rects = []  # recalcule a chaque draw(), utilise pour detecter les clics

    def _build_options(self):
        self.options = []
        if save_manager.has_progress():
            self.options.append(("KONTINYE", self._continue))
        else:
            self.options.append(("JWE", self._new_game))
        self.options.append(("CHWAZI CHAPIT", self.on_chapter_select))
        self.options.append(("OPSYON", self._open_options))
        self.options.append(("KITE", self._quit))
        self.selected = 0

    def _new_game(self):
        self.on_play(1)

    def _continue(self):
        self.on_play(save_manager.get_last_chapter())

    def _open_options(self):
        print("[MenuScene] Ecran d'options a implementer plus tard")

    def _quit(self):
        pygame.quit()
        raise SystemExit

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
                audio.play_sfx("menu_select.wav")
            elif event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
                audio.play_sfx("menu_select.wav")
            elif event.key == pygame.K_RETURN:
                audio.play_sfx("menu_confirm.wav")
                _, action = self.options[self.selected]
                action()

        elif event.type == pygame.MOUSEMOTION:
            # Deplace la selection quand la souris survole une option
            for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(event.pos):
                    if self.selected != i:
                        self.selected = i
                        audio.play_sfx("menu_select.wav")
                    break

        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            # Position du clic (FINGERDOWN utilise des coordonnees 0-1, MOUSEBUTTONDOWN des pixels)
            if event.type == pygame.FINGERDOWN:
                pos = (event.x * settings.SCREEN_WIDTH, event.y * settings.SCREEN_HEIGHT)
            else:
                pos = event.pos

            for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(pos):
                    self.selected = i
                    audio.play_sfx("menu_confirm.wav")
                    _, action = self.options[i]
                    action()
                    break

    def update(self, dt):
        pass

    def draw(self, surface):
        if self.background:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill(settings.COLOR_GREY)

        # Titre en haut a droite, aligne avec le bloc d'options
        title = self.title_font.render(settings.GAME_TITLE, True, settings.COLOR_WHITE)
        title_rect = title.get_rect(topright=(settings.SCREEN_WIDTH - RIGHT_MARGIN, 90))
        surface.blit(title, title_rect)

        # Bloc d'options aligne a droite, centre verticalement
        total_height = len(self.options) * ITEM_SPACING
        start_y = (settings.SCREEN_HEIGHT - total_height) // 2 + 60

        self.option_rects = []  # reconstruit a chaque frame

        for i, (label, _) in enumerate(self.options):
            is_selected = (i == self.selected)
            font = self.selected_font if is_selected else self.normal_font
            color = settings.COLOR_NEON_GOLD if is_selected else settings.COLOR_WHITE

            text = font.render(label, True, color)

            # Petite lueur (glow) derriere le texte selectionne, pour renforcer
            # l'effet neon sans avoir besoin d'une image ou d'un shader
            if is_selected:
                glow = font.render(label, True, settings.COLOR_NEON_GOLD)
                glow.set_alpha(80)
                for offset in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                    glow_rect = glow.get_rect(
                        topright=(settings.SCREEN_WIDTH - RIGHT_MARGIN + offset[0],
                                  start_y + i * ITEM_SPACING + offset[1])
                    )
                    surface.blit(glow, glow_rect)

            text_rect = text.get_rect(topright=(settings.SCREEN_WIDTH - RIGHT_MARGIN, start_y + i * ITEM_SPACING))
            surface.blit(text, text_rect)

            # Zone cliquable elargie (couvre toute la largeur du bloc de droite
            # + la hauteur d'un item, meme si le texte affiche est plus petit
            # -- plus facile a cliquer/toucher, et stable meme si la taille
            # de police change entre selectionne/non-selectionne)
            hit_rect = pygame.Rect(0, start_y + i * ITEM_SPACING - 10, settings.SCREEN_WIDTH, SELECTED_FONT_SIZE + 20)
            self.option_rects.append(hit_rect)
