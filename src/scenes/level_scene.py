"""
level_scene.py
---------------
Niveau jouable avec :
- Fond en parallax (3 couches, avec fallback en degrade colore si les
  images ne sont pas encore pretes)
- Le joueur (voir entities/player.py), avec fallback rectangle si le
  spritesheet n'est pas encore pret
- Zones d'ombre (mecanique "Lonbraj") : le joueur devient plus transparent
  et un indicateur "KACHE" apparait quand il est dedans
- Obstacles (Cover, voir entities/cover.py) : accroupi devant, les gardes
  ne voient plus James
- Gardes qui patrouillent (voir entities/guard.py) : si un garde voit le
  joueur assez longtemps, le joueur est repere et le niveau recommence
- Attaque par surprise : dans le dos d'un garde qui ne se doute de rien,
  F fait tomber le garde
- 9mm silencieux : G sort/range l'arme, X tire (debout, immobile). La balle
  neutralise le garde touche
- Zone de sortie (ExitZone) : y entrer termine le niveau (on_finish)

REGLES DE VISION (les gardes voient seulement DEVANT eux) :
- Joueur normal                 : portee complete
- Joueur accroupi (sneak/BAS)    : portee x SNEAK_VISION_MULT
- Joueur dans une zone d'ombre   : portee x SHADOW_VISION_MULT
- Joueur accroupi DERRIERE un obstacle : invisible (portee 0)
- Plusieurs conditions ensemble  : on garde la plus petite portee

NOMS DE DOSSIER ATTENDUS POUR LE FOND (parallax) :
    assets/backgrounds/<level_folder>/layer1_sky.png   (fond lointain)
    assets/backgrounds/<level_folder>/layer2_mid.png    (milieu)
    assets/backgrounds/<level_folder>/layer3_ground.png  (sol/premier plan)

Si un de ces fichiers manque, un degrade de couleur uni le remplace --
le niveau reste jouable et testable pendant que les vrais decors sont
en cours de creation.

COMPATIBILITE : guards, exit_zone et covers sont optionnels. Sans
exit_zone, une sortie par defaut est placee a la fin du niveau.
"""

import pygame
import os
import settings
from src.entities.player import Player
from src.entities.projectile import Bullet
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
CAUGHT_DURATION_MS = 2000    # duree de l'ecran "OU TRAPE!" (animation de mort comprise)

# --- Attaque par surprise ---
TAKEDOWN_RANGE = 85          # distance max (centre a centre) pour attraper un garde
TAKEDOWN_MAX_DETECTION = 0.5 # au-dessus, le garde se doute de quelque chose : impossible

# Touche de test : H = James recoit un coup (pour voir les animations hurt/dead)
DEBUG_HIT_KEY = True

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
                 guards=None, exit_zone=None, covers=None):
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
        self.covers = covers or []
        self.exit_zone = exit_zone or ExitZone(LEVEL_WIDTH - 220, GROUND_Y - 200, 180, 200)

        self.bullets = []
        self.takedown_target = None

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
    # Evenements
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if self.state != STATE_PLAYING:
            return
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_LCTRL, pygame.K_f):
            self._action_melee()
        elif event.key == pygame.K_g:
            self.player.toggle_pistol()
        elif event.key == pygame.K_x:
            self.player.trigger_shoot()
        elif event.key == pygame.K_h and DEBUG_HIT_KEY:
            self.player.take_hit()

    def _action_melee(self):
        """F : attaque par surprise si un garde est a portee dans son dos, sinon coup de poing."""
        target = self._find_takedown_target()
        if target:
            self.player.facing_right = target.rect.centerx >= self._player_hitbox().centerx
            if self.player.trigger_takedown():
                self.takedown_target = target
                audio.play_sfx("punch.wav")
        elif self.player.trigger_attack():
            audio.play_sfx("punch.wav")

    def _find_takedown_target(self):
        """Garde que James peut neutraliser maintenant (ou None)."""
        if not self.player.can_act():
            return None
        center = self._player_hitbox().centerx
        for guard in self.guards:
            if guard.down or guard.detection >= TAKEDOWN_MAX_DETECTION:
                continue
            if abs(guard.rect.centerx - center) > TAKEDOWN_RANGE:
                continue
            if guard.facing_away_from(center):
                return guard
        return None

    # ------------------------------------------------------------------
    # Logique
    # ------------------------------------------------------------------
    def update(self, dt):
        if self.state == STATE_FINISHED:
            return

        if self.state == STATE_CAUGHT:
            self.player.update(dt)   # laisse l'animation de mort se jouer
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

        self._process_player_events()
        self._update_bullets(dt)
        self._update_guards(dt)

        if self.player.dead and self.state == STATE_PLAYING:
            self._player_caught()      # tue par autre chose que la detection (ex: touche de test H)
        if self.state != STATE_PLAYING:
            return

        self._check_exit()

    def _process_player_events(self):
        """Evenements declenches par l'animation de James : la balle part, le garde tombe."""
        if self.player.consume_shot():
            x, y = self.player.muzzle_pos()
            self.bullets.append(Bullet(x, y, self.player.facing_right))
            audio.play_sfx("pistol_silenced.wav")

        if self.player.consume_takedown_hit():
            target, self.takedown_target = self.takedown_target, None
            if target and target.take_down():
                audio.play_sfx("takedown.wav")

    def _update_bullets(self, dt):
        for bullet in self.bullets:
            bullet.update(dt)
            if bullet.x < 0 or bullet.x > LEVEL_WIDTH:
                bullet.alive = False
                continue
            for guard in self.guards:
                if not guard.down and bullet.rect.colliderect(guard.rect):
                    guard.take_down()
                    bullet.alive = False
                    break
        self.bullets = [b for b in self.bullets if b.alive]

    def _player_hitbox(self):
        """Zone utile du joueur (plus etroite que le sprite, qui a de la marge)."""
        center_x = self.player.x + self.player.width / 2
        left = int(center_x - PLAYER_HITBOX_WIDTH / 2)
        return pygame.Rect(left, self.player.y - self.player.height,
                           PLAYER_HITBOX_WIDTH, self.player.height)

    def _is_hidden_by_cover(self):
        if self.player.state not in ("sneak", "crouch"):
            return False
        center = self._player_hitbox().centerx
        return any(cover.hides(center) for cover in self.covers)

    def _vision_multiplier(self):
        if self._is_hidden_by_cover():
            return 0.0
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
        self.player.die()
        audio.play_sfx("hurt.wav")

    def _restart_level(self):
        self.player.reset(PLAYER_START_X, GROUND_Y)
        for guard in self.guards:
            guard.reset()
        self.bullets = []
        self.takedown_target = None
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
        # Les images de fond (560 px de haut) ne couvrent pas tout l'ecran (720 px) :
        # on efface d'abord, sinon la bande du bas garde les images precedentes
        # (et le texte de l'interface s'y accumule).
        surface.fill(settings.COLOR_BLACK)
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

    def _draw_player(self, surface, concealed):
        frame, rect, _ = self.player.get_render_info()
        render_rect = rect.move(-self.camera_x, 0)

        if frame:
            if concealed:
                frame = frame.copy()
                frame.set_alpha(130)
            surface.blit(frame, render_rect.topleft)
        else:
            # Fallback : rectangle temporaire tant que le spritesheet n'est pas pret
            color = (150, 150, 150) if not concealed else (80, 80, 80)
            pygame.draw.rect(surface, color, render_rect)

        self.player.draw_props(surface, self.camera_x)

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

        hidden = self._is_hidden_by_cover()
        concealed = self._is_in_shadow() or hidden
        self._draw_player(surface, concealed)

        for bullet in self.bullets:
            bullet.draw(surface, self.camera_x)

        # Les obstacles sont dessines APRES James : il apparait derriere
        for cover in self.covers:
            cover.draw(surface, self.camera_x)

        # Invite d'attaque par surprise au-dessus du garde qu'on peut attraper
        target = self._find_takedown_target() if self.state == STATE_PLAYING else None
        if target:
            prompt = self.status_font.render("[F]", True, (255, 220, 60))
            body = target.rect.move(-self.camera_x, 0)
            surface.blit(prompt, (body.centerx - prompt.get_width() // 2, body.top - 34))

        if concealed:
            hidden_text = self.status_font.render("KACHE", True, (200, 200, 60))
            surface.blit(hidden_text, (20, 20))
        if self.player.armed:
            armed_text = self.status_font.render("9mm", True, (220, 220, 220))
            surface.blit(armed_text, (20, 50))

        hint = self.hint_font.render(
            "FLECHES: mache | BA: akoupi | ESPAS: sote | F: atake | G: zam | X: tire",
            True, settings.COLOR_WHITE
        )
        surface.blit(hint, (20, settings.SCREEN_HEIGHT - 30))

        if self.state == STATE_CAUGHT:
            self._draw_caught_overlay(surface)