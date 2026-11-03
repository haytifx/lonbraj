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
- Gardes qui patrouillent (voir entities/guard.py) : si un garde voit le
  joueur assez longtemps, le joueur est repere et le niveau recommence
- Zone de sortie (ExitZone) : y entrer termine le niveau (on_finish)

REGLES DE VISION (les gardes voient seulement DEVANT eux) :
- Joueur normal               : portee complete
- Joueur accroupi (sneak/BAS)  : portee x SNEAK_VISION_MULT
- Joueur dans une zone d'ombre : portee x SHADOW_VISION_MULT (il faut
  presque toucher le garde pour etre vu)
- Les deux ensemble            : on garde la plus petite portee

NOMS DE DOSSIER ATTENDUS POUR LE FOND (parallax) :
    assets/backgrounds/<level_folder>/layer1_sky.png   (fond lointain)
    assets/backgrounds/<level_folder>/layer2_mid.png    (milieu)
    assets/backgrounds/<level_folder>/layer3_ground.png  (sol/premier plan)

Si un de ces fichiers manque, un degrade de couleur uni le remplace --
le niveau reste jouable et testable pendant que les vrais decors sont
en cours de creation.

COMPATIBILITE : les parametres guards et exit_zone sont optionnels. Sans
exit_zone, une sortie par defaut est placee a la fin du niveau.
"""

import pygame
import os
import settings
from src.entities.player import Player
from src.audio.audio_manager import audio

GROUND_Y = 550          # position Y du sol (ou les pieds du joueur touchent)
LEVEL_WIDTH = 2400        # largeur totale du niveau (pour le scroll de camera)

PLAYER_START_X = 100

PARALLAX_FACTORS = {
    "layer1_sky.png": 0.2,
    "layer2_mid.png": 0.5,
    "layer3_ground.png": 1.0,
}

# Degrade de secours si les images de fond ne sont pas encore pretes
# (teintes sombres/froides pour evoquer l'interieur d'une base)
FALLBACK_TOP_COLOR = (25, 28, 38)
FALLBACK_BOTTOM_COLOR = (55, 60, 75)

# --- Infiltration ---
SNEAK_VISION_MULT = 0.5      # accroupi : le garde voit 2x moins loin
SHADOW_VISION_MULT = 0.2     # dans l'ombre : le garde voit 5x moins loin
PLAYER_HITBOX_WIDTH = 50     # largeur utile du joueur (le sprite a de la marge autour)
CAUGHT_DURATION_MS = 1500    # duree de l'ecran "OU TRAPE!" avant de recommencer

STATE_PLAYING = "playing"
STATE_CAUGHT = "caught"
STATE_FINISHED = "finished"


class ShadowZone:
    """Rectangle simple representant une zone d'ombre ou le joueur est discret."""
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)


class ExitZone:
    """Rectangle de sortie : quand le joueur le touche, le niveau est termine."""
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)


class LevelScene:
    def __init__(self, level_folder, chapter_id, on_finish, shadow_zones=None,
                 guards=None, exit_zone=None):
        self.level_folder = level_folder
        self.chapter_id = chapter_id
        self.on_finish = on_finish
        self.camera_x = 0
        self.state = STATE_PLAYING
        self.caught_timer = 0

        self.player = Player(x=PLAYER_START_X, y=GROUND_Y, ground_y=GROUND_Y)
        self.layers = self._load_layers()
        self.shadow_zones = shadow_zones or []
        self.guards = guards or []
        self.exit_zone = exit_zone or ExitZone(LEVEL_WIDTH - 220, GROUND_Y - 200, 180, 200)

        self.hint_font = pygame.font.Font(None, 28)
        self.status_font = pygame.font.Font(None, 32)
        self.alert_font = pygame.font.Font(None, 48)
        self.big_font = pygame.font.Font(None, 96)

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

    # ------------------------------------------------------------------
    # Evenements / logique
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if self.state != STATE_PLAYING:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LCTRL, pygame.K_f):
                self.player.trigger_attack()
                audio.play_sfx("punch.wav")

    def update(self, dt):
        if self.state == STATE_FINISHED:
            return

        if self.state == STATE_CAUGHT:
            self.caught_timer += dt
            if self.caught_timer >= CAUGHT_DURATION_MS:
                self._restart_level()
            return

        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)
        self.player.update(dt)

        # Empeche le joueur de sortir des limites du niveau
        self.player.x = max(0, min(self.player.x, LEVEL_WIDTH - self.player.width))

        # Camera suit le joueur, centree, sans depasser les bords du niveau
        target_camera_x = self.player.x - settings.SCREEN_WIDTH // 2
        self.camera_x = max(0, min(target_camera_x, LEVEL_WIDTH - settings.SCREEN_WIDTH))

        self._update_guards(dt)
        if self.state != STATE_PLAYING:
            return

        self._check_exit()

    def _player_hitbox(self):
        """Zone utile du joueur (plus etroite que le sprite, qui a de la marge)."""
        center_x = self.player.x + self.player.width / 2
        left = int(center_x - PLAYER_HITBOX_WIDTH / 2)
        return pygame.Rect(left, self.player.y - self.player.height,
                           PLAYER_HITBOX_WIDTH, self.player.height)

    def _vision_multiplier(self):
        mult = 1.0
        if self.player.state in ("sneak", "crouch"):
            mult = min(mult, SNEAK_VISION_MULT)
        if self._is_in_shadow():
            mult = min(mult, SHADOW_VISION_MULT)
        return mult

    def _update_guards(self, dt):
        hitbox = self._player_hitbox()
        mult = self._vision_multiplier()

        for guard in self.guards:
            sees = guard.vision_rect(mult).colliderect(hitbox)
            just_noticed = guard.update(dt, sees, hitbox.centerx)
            if just_noticed:
                audio.play_sfx("alert.wav")
            if guard.detection >= 1.0:
                self._player_caught()
                return

    def _player_caught(self):
        self.state = STATE_CAUGHT
        self.caught_timer = 0
        self.player.take_hit()
        audio.play_sfx("hurt.wav")

    def _restart_level(self):
        self.player.x = PLAYER_START_X
        self.player.y = GROUND_Y
        self.player.vel_x = 0
        self.player.vel_y = 0
        self.player.on_ground = True
        self.player.attack_lock = False
        self.player.state = "idle"
        for guard in self.guards:
            guard.reset()
        self.camera_x = 0
        self.caught_timer = 0
        self.state = STATE_PLAYING

    def _check_exit(self):
        if self._player_hitbox().colliderect(self.exit_zone.rect):
            self.state = STATE_FINISHED
            audio.play_sfx("menu_confirm.wav")
            self.on_finish()

    def _is_in_shadow(self):
        player_rect = pygame.Rect(self.player.x, self.player.y - self.player.height,
                                   self.player.width, self.player.height)
        return any(zone.rect.colliderect(player_rect) for zone in self.shadow_zones)

    # ------------------------------------------------------------------
    # Affichage
    # ------------------------------------------------------------------
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

    def _draw_exit_zone(self, surface):
        exit_rect = self.exit_zone.rect.move(-self.camera_x, 0)
        exit_surface = pygame.Surface((exit_rect.width, exit_rect.height), pygame.SRCALPHA)
        exit_surface.fill((60, 220, 120, 70))
        surface.blit(exit_surface, exit_rect.topleft)
        pygame.draw.rect(surface, (60, 220, 120), exit_rect, 2)
        label = self.status_font.render("SOTI", True, (60, 220, 120))
        surface.blit(label, (exit_rect.centerx - label.get_width() // 2, exit_rect.top - 30))

    def _draw_player(self, surface, in_shadow):
        frame, rect, _ = self.player.get_render_info()
        render_rect = rect.move(-self.camera_x, 0)

        if frame:
            if in_shadow:
                frame = frame.copy()
                frame.set_alpha(130)
            surface.blit(frame, render_rect.topleft)
        else:
            # Fallback : rectangle temporaire tant que le spritesheet n'est pas pret
            color = (150, 150, 150) if not in_shadow else (80, 80, 80)
            pygame.draw.rect(surface, color, render_rect)

    def _draw_caught_overlay(self, surface):
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((120, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        text = self.big_font.render("OU TRAPE!", True, settings.COLOR_WHITE)
        surface.blit(text, text.get_rect(center=(settings.SCREEN_WIDTH // 2,
                                                 settings.SCREEN_HEIGHT // 2)))

    def draw(self, surface):
        self._draw_layers(surface)
        self._draw_shadow_zones_debug(surface)
        self._draw_exit_zone(surface)

        mult = self._vision_multiplier()
        for guard in self.guards:
            guard.draw(surface, self.camera_x, mult, self.alert_font)

        in_shadow = self._is_in_shadow()
        self._draw_player(surface, in_shadow)

        if in_shadow:
            hidden_text = self.status_font.render("KACHE", True, (200, 200, 60))
            surface.blit(hidden_text, (20, 20))

        hint = self.hint_font.render(
            "FLECHES: mache | BA+FLECH: sneak | ESPAS: sote | CTRL/F: atake",
            True, settings.COLOR_WHITE
        )
        surface.blit(hint, (20, settings.SCREEN_HEIGHT - 30))

        if self.state == STATE_CAUGHT:
            self._draw_caught_overlay(surface)