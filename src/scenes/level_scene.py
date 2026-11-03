"""
level_scene.py
---------------
Niveau jouable avec :
- Fond en parallax (3 couches, avec fallback en degrade colore si les
  images ne sont pas encore pretes)
- Le joueur (voir entities/player.py), avec fallback rectangle si le
  spritesheet n'est pas encore pret
- Zones d'ombre simples (mecanique "Lonbraj") : le joueur devient plus
  transparent et un indicateur "KACHE" apparait quand il est dedans

NOMS DE DOSSIER ATTENDUS POUR LE FOND (parallax) :
    assets/backgrounds/<level_folder>/layer1_sky.png   (fond lointain)
    assets/backgrounds/<level_folder>/layer2_mid.png    (milieu)
    assets/backgrounds/<level_folder>/layer3_ground.png  (sol/premier plan)

Si un de ces fichiers manque, un degrade de couleur uni le remplace --
le niveau reste jouable et testable pendant que les vrais decors sont
en cours de creation.
"""

import pygame
import os
import settings
from src.entities.player import Player
from src.audio.audio_manager import audio

GROUND_Y = 550          # position Y du sol (ou les pieds du joueur touchent)
LEVEL_WIDTH = 2400        # largeur totale du niveau (pour le scroll de camera)

PARALLAX_FACTORS = {
    "layer1_sky.png": 0.2,
    "layer2_mid.png": 0.5,
    "layer3_ground.png": 1.0,
}

# Degrade de secours si les images de fond ne sont pas encore pretes
# (teintes sombres/froides pour evoquer l'interieur d'une base)
FALLBACK_TOP_COLOR = (25, 28, 38)
FALLBACK_BOTTOM_COLOR = (55, 60, 75)


class ShadowZone:
    """Rectangle simple representant une zone d'ombre ou le joueur est discret."""
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)


class LevelScene:
    def __init__(self, level_folder, chapter_id, on_finish, shadow_zones=None):
        self.level_folder = level_folder
        self.chapter_id = chapter_id
        self.on_finish = on_finish
        self.camera_x = 0

        self.player = Player(x=100, y=GROUND_Y, ground_y=GROUND_Y)
        self.layers = self._load_layers()
        self.shadow_zones = shadow_zones or []

        self.hint_font = pygame.font.Font(None, 28)
        self.status_font = pygame.font.Font(None, 32)

        audio.play_music("chapter1_theme.ogg")

    def _load_layers(self):
        layers = {}
        base_path = os.path.join(settings.BACKGROUNDS_DIR, self.level_folder)
        for filename, factor in PARALLAX_FACTORS.items():
            path = os.path.join(base_path, filename)
            if os.path.exists(path):
                img = pygame.image.load(path).convert()
                layers[filename] = {"image": img, "factor": factor}
            else:
                layers[filename] = {"image": None, "factor": factor}
                print(f"[LevelScene] Fond introuvable : {path} (degrade de secours utilise)")
        return layers

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LCTRL, pygame.K_f):
                self.player.trigger_attack()
                audio.play_sfx("punch.wav")

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)
        self.player.update(dt)

        # Empeche le joueur de sortir des limites du niveau
        self.player.x = max(0, min(self.player.x, LEVEL_WIDTH - self.player.width))

        # Camera suit le joueur, centree, sans depasser les bords du niveau
        target_camera_x = self.player.x - settings.SCREEN_WIDTH // 2
        self.camera_x = max(0, min(target_camera_x, LEVEL_WIDTH - settings.SCREEN_WIDTH))

    def _is_in_shadow(self):
        player_rect = pygame.Rect(self.player.x, self.player.y - self.player.height,
                                   self.player.width, self.player.height)
        return any(zone.rect.colliderect(player_rect) for zone in self.shadow_zones)

    def _draw_fallback_gradient(self, surface):
        for y in range(settings.SCREEN_HEIGHT):
            t = y / settings.SCREEN_HEIGHT
            color = tuple(
                int(FALLBACK_TOP_COLOR[i] + (FALLBACK_BOTTOM_COLOR[i] - FALLBACK_TOP_COLOR[i]) * t)
                for i in range(3)
            )
            pygame.draw.line(surface, color, (0, y), (settings.SCREEN_WIDTH, y))

    def _draw_layers(self, surface):
        any_real_layer = any(layer["image"] is not None for layer in self.layers.values())
        if not any_real_layer:
            self._draw_fallback_gradient(surface)
            return

        for filename in ["layer1_sky.png", "layer2_mid.png", "layer3_ground.png"]:
            layer = self.layers[filename]
            if layer["image"] is None:
                continue
            offset_x = -int(self.camera_x * layer["factor"]) % layer["image"].get_width()
            surface.blit(layer["image"], (offset_x - layer["image"].get_width(), 0))
            surface.blit(layer["image"], (offset_x, 0))

    def _draw_shadow_zones_debug(self, surface):
        """Affiche les zones d'ombre en semi-transparent -- utile pendant les
        tests pour voir ou elles sont. A retirer/desactiver une fois le level
        design final."""
        for zone in self.shadow_zones:
            debug_rect = zone.rect.move(-self.camera_x, 0)
            shadow_surface = pygame.Surface((debug_rect.width, debug_rect.height), pygame.SRCALPHA)
            shadow_surface.fill((0, 0, 0, 90))
            surface.blit(shadow_surface, debug_rect.topleft)

    def draw(self, surface):
        self._draw_layers(surface)
        self._draw_shadow_zones_debug(surface)

        frame, rect, _ = self.player.get_render_info()
        render_rect = rect.move(-self.camera_x, 0)

        in_shadow = self._is_in_shadow()

        if frame:
            if in_shadow:
                frame = frame.copy()
                frame.set_alpha(130)
            surface.blit(frame, render_rect.topleft)
        else:
            # Fallback : rectangle temporaire tant que le spritesheet n'est pas pret
            color = (150, 150, 150) if not in_shadow else (80, 80, 80)
            pygame.draw.rect(surface, color, render_rect)

        if in_shadow:
            hidden_text = self.status_font.render("KACHE", True, (200, 200, 60))
            surface.blit(hidden_text, (20, 20))

        hint = self.hint_font.render(
            "FLECHES: mache | BA+FLECH: sneak | ESPAS: sote | CTRL/F: atake",
            True, settings.COLOR_WHITE
        )
        surface.blit(hint, (20, settings.SCREEN_HEIGHT - 30))
