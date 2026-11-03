"""
chapter_select_scene.py
------------------------
Ekran "Chwazi Chapit" -- montre lis tout chapit yo (data/chapters.json),
ak yon kadna pou chapit ki poko debloke (chapit jwè a poko rive ladan).
Jwè a ka jwe/rejwe nenpòt chapit ki deja debloke.
"""

import pygame
import json
import os
import settings
from src.audio.audio_manager import audio
from src.save_manager import save_manager

CHAPTERS_PATH = "data/chapters.json"


class ChapterSelectScene:
    def __init__(self, on_select_chapter, on_back):
        """on_select_chapter(chapter_dict) : appele quand le joueur choisit un chapitre debloque
        on_back : retour au menu principal"""
        self.on_select_chapter = on_select_chapter
        self.on_back = on_back
        self.chapters = self._load_chapters()
        self.selected = 0

        self.title_font = pygame.font.Font(None, 70)
        self.item_font = pygame.font.Font(None, 44)
        self.hint_font = pygame.font.Font(None, 28)

    def _load_chapters(self):
        if not os.path.exists(CHAPTERS_PATH):
            print(f"[ChapterSelectScene] {CHAPTERS_PATH} introuvable")
            return []
        with open(CHAPTERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % len(self.chapters)
            audio.play_sfx("menu_select.wav")
        elif event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(self.chapters)
            audio.play_sfx("menu_select.wav")
        elif event.key == pygame.K_ESCAPE:
            self.on_back()
        elif event.key == pygame.K_RETURN:
            chapter = self.chapters[self.selected]
            if save_manager.is_unlocked(chapter["id"]):
                audio.play_sfx("menu_confirm.wav")
                self.on_select_chapter(chapter)
            else:
                audio.play_sfx("menu_select.wav")  # petit "clic" pour indiquer que c'est verrouille

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill(settings.COLOR_GREY)

        title = self.title_font.render("CHWAZI CHAPIT", True, settings.COLOR_WHITE)
        title_rect = title.get_rect(center=(settings.SCREEN_WIDTH // 2, 100))
        surface.blit(title, title_rect)

        start_y = 220
        for i, chapter in enumerate(self.chapters):
            unlocked = save_manager.is_unlocked(chapter["id"])
            label = f"Chapit {chapter['id']} — {chapter['title']}"
            if not unlocked:
                label += "  [ FÈMEN ]"

            if i == self.selected:
                color = settings.COLOR_ACCENT if unlocked else (120, 60, 60)
            else:
                color = settings.COLOR_WHITE if unlocked else (100, 100, 100)

            text = self.item_font.render(label, True, color)
            rect = text.get_rect(center=(settings.SCREEN_WIDTH // 2, start_y + i * 60))
            surface.blit(text, rect)

        hint = self.hint_font.render("ANTRE: chwazi   ECHAP: retounen", True, settings.COLOR_WHITE)
        surface.blit(hint, (30, settings.SCREEN_HEIGHT - 40))
