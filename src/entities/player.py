"""
player.py
---------
Le personnage jouable (James). Gere le mouvement, la gravite simple, et
les etats d'animation.

FALLBACKS IMPORTANTS (a retirer au fur et a mesure que les vraies frames
sont pretes) :
- "idle" n'existe pas encore dans le spritesheet -> on affiche la 1ere
  frame de "walk", figee (pas d'animation).
- "sneak" n'existe pas encore -> on reutilise "walk" mais plus lentement
  et avec le sprite compresse verticalement (~15%) pour simuler
  visuellement une posture accroupie, en attendant les vraies frames.

CONTROLES (clavier, temporaire -- a remplacer par une vraie gestion
input/mobile plus tard) :
    Fleches gauche/droite : marcher
    Bas + gauche/droite    : sneak (mode discret, plus lent)
    Espace                 : sauter
    Ctrl gauche / F         : attaquer (coup de poing)
"""

import pygame
import os
import settings
from src.entities.animation import SpriteSheet, AnimationPlayer

GRAVITY = 1400          # pixels/s^2
WALK_SPEED = 220         # pixels/s
SNEAK_SPEED = 90          # pixels/s (plus lent que la marche normale)
JUMP_FORCE = -550          # pixels/s (negatif = vers le haut)
AIR_CONTROL = 1.0          # multiplicateur de vitesse horizontale en l'air (1.0 = pleine vitesse, permet de sauter par-dessus un obstacle en avancant)

ANIM_FPS = {
    "walk": 8,     # AJUSTE ICI si la marche est trop rapide/lente -- baisse le chiffre pour ralentir
    "sneak": 6,
    "jump": 8,
    "attack": 10,
    "hurt": 8,
    "dead": 6,
}
DEFAULT_ANIM_FPS = 8


class Player:
    def __init__(self, x, y, ground_y):
        self.x = x
        self.y = y
        self.ground_y = ground_y
        self.vel_x = 0
        self.vel_y = 0
        self.facing_right = True
        self.state = "idle"
        self.on_ground = True
        self.attack_lock = False  # empeche de bouger pendant l'animation d'attaque

        self.spritesheet = None
        self.anim = None
        self.has_idle = False
        self.has_sneak = False
        self._load_spritesheet()

        # Taille utilisee pour la collision/placeholder si pas de spritesheet
        self.width = 60
        self.height = 120

    def _load_spritesheet(self):
        if os.path.exists(settings.PLAYER_SPRITESHEET) and os.path.exists(settings.PLAYER_SPRITESHEET_META):
            self.spritesheet = SpriteSheet(settings.PLAYER_SPRITESHEET, settings.PLAYER_SPRITESHEET_META)
            self.anim = AnimationPlayer(self.spritesheet, fps=8)
            self.has_idle = "idle" in self.spritesheet.animations
            self.has_sneak = "sneak" in self.spritesheet.animations
            self.width = self.spritesheet.frame_width
            self.height = self.spritesheet.frame_height
        else:
            print(f"[Player] Spritesheet introuvable ({settings.PLAYER_SPRITESHEET}) "
                  f"-- un rectangle temporaire sera affiche a la place.")

    def handle_input(self, keys):
        if self.attack_lock:
            return  # on ne bouge pas pendant qu'on frappe

        sneaking = keys[pygame.K_DOWN]
        moving_left = keys[pygame.K_LEFT]
        moving_right = keys[pygame.K_RIGHT]

        speed = SNEAK_SPEED if sneaking else WALK_SPEED
        if not self.on_ground:
            speed *= AIR_CONTROL  # permet de garder le mouvement horizontal pendant le saut
        self.vel_x = 0

        if moving_left:
            self.vel_x = -speed
            self.facing_right = False
        elif moving_right:
            self.vel_x = speed
            self.facing_right = True

        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = JUMP_FORCE
            self.on_ground = False

        # Determine l'etat d'animation en fonction du mouvement
        if not self.on_ground:
            self.state = "jump"
        elif sneaking and self.vel_x != 0:
            self.state = "sneak"
        elif sneaking and self.vel_x == 0:
            self.state = "crouch"  # akoupi estatik : touche BA peze, san deplasman
        elif self.vel_x != 0:
            self.state = "walk"
        else:
            self.state = "idle"

    def trigger_attack(self):
        if not self.attack_lock and self.on_ground:
            self.attack_lock = True
            self.state = "attack"
            if self.anim:
                self.anim.play("attack", loop=False, restart_if_same=True)

    def take_hit(self):
        self.state = "hurt"
        if self.anim:
            self.anim.play("hurt", loop=False, restart_if_same=True)

    def update(self, dt_ms):
        dt = dt_ms / 1000

        # Gravite + collision sol simple
        self.vel_y += GRAVITY * dt
        self.y += self.vel_y * dt
        if self.y >= self.ground_y:
            self.y = self.ground_y
            self.vel_y = 0
            self.on_ground = True

        self.x += self.vel_x * dt

        # Fin de l'attaque -> deverrouille le mouvement
        if self.attack_lock and self.anim and self.anim.finished:
            self.attack_lock = False

        self._update_animation(dt_ms)

    def _update_animation(self, dt_ms):
        if not self.anim:
            return

        if self.state == "idle":
            if self.has_idle:
                self.anim.fps = ANIM_FPS.get("idle", DEFAULT_ANIM_FPS)
                self.anim.play("idle", loop=True)
                self.anim.update(dt_ms)
            else:
                # Fallback : 1ere frame de "walk", figee (pas d'update -> pas d'animation)
                self.anim.play("walk", loop=True)
                self.anim.frame_index = 0

        elif self.state == "crouch":
            # Akoupi estatik (touche BA sans deplacement) : reutilise "sneak" si
            # dispo, sinon "walk" compresse -- toujours FIGE (pas d'update),
            # comme "idle", pour bien montrer une pose immobile.
            fallback_anim = "sneak" if self.has_sneak else "walk"
            self.anim.play(fallback_anim, loop=True)
            self.anim.frame_index = 0

        elif self.state == "sneak":
            if self.has_sneak:
                self.anim.fps = ANIM_FPS.get("sneak", DEFAULT_ANIM_FPS)
                self.anim.play("sneak", loop=True)
            else:
                # Fallback : reutilise "walk" (le rendu applique une compression
                # verticale, voir get_render_rect ci-dessous)
                self.anim.fps = ANIM_FPS.get("sneak", DEFAULT_ANIM_FPS)
                self.anim.play("walk", loop=True)
            self.anim.update(dt_ms)

        elif self.state in ("walk", "jump"):
            self.anim.fps = ANIM_FPS.get(self.state, DEFAULT_ANIM_FPS)
            self.anim.play(self.state, loop=True)
            self.anim.update(dt_ms)

        elif self.state in ("attack", "hurt"):
            self.anim.fps = ANIM_FPS.get(self.state, DEFAULT_ANIM_FPS)
            self.anim.update(dt_ms)  # deja lance via trigger_attack()/take_hit(), loop=False

    def get_render_info(self):
        """Retourne (frame_surface_or_None, rect, is_sneak_fallback) pour l'affichage."""
        rect = pygame.Rect(self.x, self.y - self.height, self.width, self.height)

        if not self.anim:
            return None, rect, False

        frame = self.anim.get_current_frame()
        needs_squash = (
            (self.state == "sneak" and not self.has_sneak) or
            (self.state == "crouch" and not self.has_sneak)
        )

        if needs_squash and frame:
            # Compresse verticalement ~15% pour simuler une posture accroupie
            # en attendant les vraies frames "sneak"
            squash_height = int(self.height * 0.85)
            frame = pygame.transform.scale(frame, (self.width, squash_height))
            rect = pygame.Rect(self.x, self.y - squash_height, self.width, squash_height)

        if frame and not self.facing_right:
            frame = pygame.transform.flip(frame, True, False)

        return frame, rect, needs_squash