"""
main.py
-------
Point d'entree du jeu. Volontairement court -- toute la logique vit
dans src/. Les fonctions go_to_* ci-dessous forment la "carte de
navigation" entre les scenes : c'est le seul endroit ou on decide quelle
scene mene a quelle autre.

LANCEMENT :
    python main.py
"""

import json
import sys
import pygame
import settings
from src.save_manager import save_manager
from src.scene_manager import scene_manager
from src.scenes.chapter_select_scene import ChapterSelectScene
from src.scenes.cutscene_scene import CutsceneScene
from src.entities.cover import Cover
from src.entities.guard import Guard
from src.scenes.level_scene import LevelScene, ShadowZone, ExitZone, GROUND_Y
from src.scenes.level_transition_scene import LevelTransitionScene
from src.scenes.menu_scene import MenuScene
from src.scenes.splash_scene import SplashScene

CHAPTERS_PATH = "data/chapters.json"


def _get_chapter(chapter_id):
    with open(CHAPTERS_PATH, "r", encoding="utf-8") as f:
        chapters = json.load(f)
    for ch in chapters:
        if ch["id"] == chapter_id:
            return ch
    return None


def go_to_intro_or_menu():
    if save_manager.has_seen_intro() and not settings.DEBUG_FORCE_REPLAY_INTRO:
        go_to_menu()
    else:
        scene_manager.set_scene(CutsceneScene(
            "intro_narration.json",
            on_finish=_finish_intro,
            background_music="intro_theme.ogg",
        ))


def _finish_intro():
    save_manager.mark_intro_seen()
    go_to_menu()


def go_to_menu():
    scene_manager.set_scene(MenuScene(on_play=go_to_chapter_opening, on_chapter_select=go_to_chapter_select))


def go_to_chapter_select():
    scene_manager.set_scene(ChapterSelectScene(
        on_select_chapter=lambda chapter: go_to_chapter_opening(chapter["id"]),
        on_back=go_to_menu,
    ))


def go_to_chapter_opening(chapter_id):
    chapter = _get_chapter(chapter_id)
    if chapter is None:
        print(f"[main] Chapit {chapter_id} pa egziste, retou nan meni.")
        go_to_menu()
        return
    scene_manager.set_scene(CutsceneScene(
        chapter["opening"],
        on_finish=lambda: go_to_level(chapter_id),
    ))


def go_to_level(chapter_id):
    scene_manager.set_scene(LevelTransitionScene(
        title=f"CHAPIT {chapter_id} — ENFILTRASYON",
        music_file="action_theme.ogg",
        on_finish=lambda: go_to_level_gameplay(chapter_id),
    ))


def go_to_level_gameplay(chapter_id):
    # Zones d'ombre de test pour le chapitre 1 -- a ajuster une fois le vrai
    # decor de la base pret. Format : ShadowZone(x, y, largeur, hauteur)
    test_shadow_zones = [
        ShadowZone(400, 300, 250, 250),
        ShadowZone(1200, 300, 300, 250),
    ]
    # Gardes de test : Guard(x_gauche, x_droite, GROUND_Y) = bornes de patrouille.
    # Ajuste les chiffres (ou ajoute des gardes) pour changer la difficulte.
    test_guards = [
        Guard(700, 1000, GROUND_Y),
        Guard(1650, 2000, GROUND_Y, start_facing_right=False),
    ]
    # Zone de sortie : ExitZone(x, y, largeur, hauteur). Toucher = niveau termine.
    test_exit_zone = ExitZone(2200, GROUND_Y - 200, 180, 200)

    # Obstacles pour se cacher : Cover(x, GROUND_Y, height=hauteur, image="fichier.png").
    # image = PNG a fond transparent dans assets/props/ (optionnel : sans lui, une caisse grise).
    # Accroupi (touche BAS) devant un obstacle, les gardes ne voient plus James.
    test_covers = [
        Cover(1080, GROUND_Y, width=150, height=90, image="cover_crate.png"),
        Cover(1750, GROUND_Y, width=150, height=90, image="cover_crate.png"),
    ]

    scene_manager.set_scene(LevelScene(
        level_folder=f"level{chapter_id}_baz",
        chapter_id=chapter_id,
        on_finish=lambda: _finish_level(chapter_id),
        shadow_zones=test_shadow_zones,
        guards=test_guards,
        exit_zone=test_exit_zone,
        covers=test_covers,
    ))


def _finish_level(chapter_id):
    save_manager.complete_chapter(chapter_id)
    go_to_menu()


def main():
    pygame.init()
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    pygame.display.set_caption(settings.GAME_TITLE)
    clock = pygame.time.Clock()

    scene_manager.set_scene(SplashScene(on_finish=go_to_intro_or_menu))

    running = True
    while running:
        dt = clock.tick(settings.FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                scene_manager.handle_event(event)

        scene_manager.update(dt)
        scene_manager.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()