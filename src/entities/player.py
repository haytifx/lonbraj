"""
player.py
---------
Le personnage jouable (James). Gere le mouvement, la gravite simple, les
etats et le choix de l'animation a afficher.

CONTROLES (clavier, temporaire -- a remplacer par une vraie gestion
input/mobile plus tard) :
    Fleches gauche/droite : marcher
    Bas                    : s'accroupir (immobile = "crouch", en marchant = "sneak", silencieux)
    Espace                 : sauter
    F / Ctrl gauche        : attaquer (dans le dos d'un garde = takedown, sinon coup de poing)
    G                      : sortir / ranger le 9mm silencieux
    X                      : tirer (arme sortie, debout, immobile)

NOMS D'ANIMATION CHERCHES DANS LE SPRITESHEET (tous optionnels) :
    idle, walk, sneak, crouch, jump, attack, hurt, dead, takedown
    pistol_idle, pistol_walk, pistol_sneak, pistol_crouch   <- memes poses mais le 9mm en main
    pistol_aim, pistol_shoot                                  <- tir (jamais en accroupi)

REPLIS (FALLBACKS) : si une animation n'existe pas encore, le jeu choisit
la premiere de la liste CANDIDATES ci-dessous qui existe. Ex: "idle"
manquant -> 1ere frame de "walk" figee. Le jeu ne plante donc jamais, et
chaque nouvelle animation ajoutee au spritesheet est utilisee
automatiquement, sans toucher au code.

SYNCHRONISATION MARCHE/VITESSE (le secret de l'animation fluide) :
    Pour "walk" et "sneak", la vitesse de lecture n'est PAS un fps fixe :
    elle est calculee a partir de la vitesse reelle du joueur
        frames_par_seconde = nb_frames * vitesse / stride
    ou "stride" = pixels parcourus au sol pendant un cycle complet (voir
    STRIDE_PX ou le champ "stride" du JSON). Resultat : les pieds ne
    glissent pas sur le sol.
      - Si James PATINE (les pieds glissent vers l'avant)  -> DIMINUE le stride
      - Si les pieds semblent reculer plus vite que le sol -> AUGMENTE le stride
"""

import pygame
import os
import settings
from src.entities.animation import SpriteSheet, AnimationPlayer

GRAVITY = 1400          # pixels/s^2
WALK_SPEED = 220         # pixels/s
PISTOL_WALK_SPEED = 170   # pixels/s (marche arme au poing : un peu plus lent)
SNEAK_SPEED = 90          # pixels/s (plus lent que la marche normale)
JUMP_FORCE = -550          # pixels/s (negatif = vers le haut)
AIR_CONTROL = 1.0          # multiplicateur de vitesse horizontale en l'air

# fps de secours (utilises SEULEMENT si le JSON du spritesheet n'a pas de "fps")
ANIM_FPS = {
    "idle": 6, "walk": 8, "sneak": 6, "crouch": 6, "jump": 8,
    "attack": 10, "hurt": 8, "dead": 6,
    "pistol_aim": 10, "pistol_shoot": 12, "takedown": 10,
}
DEFAULT_ANIM_FPS = 8

# Animations jouees UNE seule fois quand le JSON ne precise pas "loop"
# ("jump" reste en boucle ici pour ne pas changer l'ancien spritesheet)
ONE_SHOT = {"attack", "hurt", "dead", "pistol_aim", "pistol_shoot", "takedown"}

# Pixels parcourus au sol pendant UN cycle complet de marche (ESTIMATION a ajuster)
STRIDE_PX = {"walk": 96, "sneak": 72}

SQUASH_RATIO = 0.85       # compression verticale quand il n'y a pas d'animation accroupie

MAX_HP = 3
HURT_INVULN_MS = 1000     # invincibilite apres un coup

# Duree des actions quand il n'y a PAS d'animation (repli) -- avec une animation,
# c'est la fin de l'animation qui deverrouille le mouvement.
FALLBACK_LOCK_MS = {"attack": 350, "shoot": 400, "takedown": 600, "hurt": 500}
DEAD_FALLBACK_MS = 900
SHOOT_FIRE_DELAY_MS = 150      # repli : delai avant que la balle parte
TAKEDOWN_HIT_DELAY_MS = 250    # repli : delai avant que le garde tombe
SHOOT_COOLDOWN_MS = 350

# Position du bout du canon par rapport aux PIEDS de James : (devant, hauteur)
MUZZLE_OFFSET = (46, 72)

# Pour chaque etat : liste ordonnee de (animation, mode, compresser?)
#   mode "loco"   : boucle, vitesse liee a la vitesse reelle (marche)
#   mode "play"   : boucle a fps normal
#   mode "freeze" : premiere frame, figee
#   mode "once"   : jouee une fois (actions)
# {p} = "pistol_" si le 9mm est sorti, sinon "".
CANDIDATES = {
    "idle":   [("{p}idle", "play", False), ("idle", "play", False),
               ("{p}walk", "freeze", False), ("walk", "freeze", False)],
    "walk":   [("{p}walk", "loco", False), ("walk", "loco", False)],
    "sneak":  [("{p}sneak", "loco", False), ("sneak", "loco", False),
               ("{p}walk", "loco", True), ("walk", "loco", True)],
    "crouch": [("{p}crouch", "play", False), ("crouch", "play", False),
               ("{p}sneak", "freeze", False), ("sneak", "freeze", False),
               ("{p}walk", "freeze", True), ("walk", "freeze", True)],
    "jump":   [("jump", "play", False), ("walk", "freeze", False)],
    "attack": [("attack", "once", False), ("walk", "freeze", False)],
    "shoot":  [("pistol_shoot", "once", False), ("pistol_aim", "once", False),
               ("pistol_idle", "freeze", False), ("idle", "freeze", False),
               ("walk", "freeze", False)],
    "takedown": [("takedown", "once", False), ("attack", "once", False),
                 ("walk", "freeze", False)],
    "hurt":   [("hurt", "once", False), ("walk", "freeze", False)],
    "dead":   [("dead", "once", False), ("hurt", "freeze", False), ("walk", "freeze", False)],
}

LOCK_STATES = ("attack", "shoot", "takedown", "hurt", "dead")


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

        self.armed = False        # 9mm silencieux sorti ?
        self.hp = MAX_HP
        self.invuln_ms = 0
        self.shoot_cooldown_ms = 0

        # Verrou d'action : pendant "attack"/"shoot"/"takedown"/"hurt"/"dead" on ne bouge pas
        self.lock = None
        self.lock_timer = 0
        self._anim_driven = False   # le verrou se termine avec l'animation (sinon : chrono)
        self._shot_fired = False
        self._shot_ready = False
        self._td_fired = False
        self._td_ready = False
        self._squash = False
        self._squash_cache = {}

        self.spritesheet = None
        self.anim = None
        self._load_spritesheet()

        # Taille utilisee pour la collision/placeholder si pas de spritesheet
        self.width = 60
        self.height = 120
        if self.spritesheet:
            self.width = self.spritesheet.frame_width
            self.height = self.spritesheet.frame_height

    # ------------------------------------------------------------------
    # Chargement
    # ------------------------------------------------------------------
    def _load_spritesheet(self):
        if os.path.exists(settings.PLAYER_SPRITESHEET) and os.path.exists(settings.PLAYER_SPRITESHEET_META):
            self.spritesheet = SpriteSheet(settings.PLAYER_SPRITESHEET, settings.PLAYER_SPRITESHEET_META)
            self.anim = AnimationPlayer(self.spritesheet, fps=DEFAULT_ANIM_FPS)
        else:
            print(f"[Player] Spritesheet introuvable ({settings.PLAYER_SPRITESHEET}) "
                  f"-- un rectangle temporaire sera affiche a la place.")

    @property
    def has_pistol_art(self):
        s = self.spritesheet
        return bool(s) and any(s.has(n) for n in ("pistol_idle", "pistol_walk", "pistol_shoot"))

    # ------------------------------------------------------------------
    # Etat
    # ------------------------------------------------------------------
    @property
    def locked(self):
        return self.lock is not None

    @property
    def attack_lock(self):          # ancien nom, garde pour compatibilite
        return self.lock == "attack"

    @property
    def dead(self):
        return self.lock == "dead"

    @property
    def death_finished(self):
        if not self.dead:
            return False
        if self._anim_driven and self.anim:
            return self.anim.finished
        return self.lock_timer >= DEAD_FALLBACK_MS

    def can_act(self):
        return self.on_ground and not self.locked

    def reset(self, x, y):
        """Remet James au depart (apres 'OU TRAPE')."""
        self.x, self.y = x, y
        self.vel_x = self.vel_y = 0
        self.on_ground = True
        self.facing_right = True
        self.armed = False
        self.hp = MAX_HP
        self.invuln_ms = 0
        self.shoot_cooldown_ms = 0
        self.lock = None
        self.lock_timer = 0
        self.state = "idle"
        self._shot_ready = self._td_ready = False

    # ------------------------------------------------------------------
    # Entrees
    # ------------------------------------------------------------------
    def handle_input(self, keys):
        if self.locked:
            self.vel_x = 0   # on ne glisse pas pendant une action
            return

        sneaking = keys[pygame.K_DOWN]
        moving_left = keys[pygame.K_LEFT]
        moving_right = keys[pygame.K_RIGHT]

        if sneaking:
            speed = SNEAK_SPEED
        else:
            speed = PISTOL_WALK_SPEED if self.armed else WALK_SPEED
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

    # ------------------------------------------------------------------
    # Actions (retournent True si l'action a demarre)
    # ------------------------------------------------------------------
    def _start_lock(self, kind):
        self.lock = kind
        self.state = kind
        self.lock_timer = 0
        self.vel_x = 0
        res = self._resolve(kind)
        self._anim_driven = bool(res and res[1] == "once" and self.anim)
        if self._anim_driven:
            name = res[0]
            fps = self.spritesheet.anim_fps(name, ANIM_FPS.get(name, ANIM_FPS.get(kind, DEFAULT_ANIM_FPS)))
            self.anim.play(name, loop=False, restart_if_same=True, fps=fps)

    def trigger_attack(self):
        if not self.can_act():
            return False
        self._start_lock("attack")
        return True

    def trigger_takedown(self):
        """Attaque par surprise (dans le dos d'un garde)."""
        if not self.can_act():
            return False
        self._td_fired = False
        self._td_ready = False
        self._start_lock("takedown")
        return True

    def toggle_pistol(self):
        if not self.can_act():
            return self.armed
        self.armed = not self.armed
        return self.armed

    def trigger_shoot(self):
        """Tirer : arme sortie, debout et immobile (jamais en accroupi)."""
        if not self.armed or not self.can_act() or self.shoot_cooldown_ms > 0:
            return False
        if self.state in ("sneak", "crouch"):
            return False
        self._shot_fired = False
        self._shot_ready = False
        self._start_lock("shoot")
        self.shoot_cooldown_ms = SHOOT_COOLDOWN_MS
        return True

    def take_hit(self, damage=1):
        """Touche par une balle ou un coup. Retourne True si le coup a porte."""
        if self.dead or self.invuln_ms > 0:
            return False
        self.hp -= damage
        if self.hp <= 0:
            self.die()
            return True
        self.invuln_ms = HURT_INVULN_MS
        self._start_lock("hurt")
        return True

    def die(self):
        if self.dead:
            return
        self.hp = 0
        self._start_lock("dead")

    # Evenements declenches PAR l'animation (la scene les consomme)
    def consume_shot(self):
        ready, self._shot_ready = self._shot_ready, False
        return ready

    def consume_takedown_hit(self):
        ready, self._td_ready = self._td_ready, False
        return ready

    def muzzle_pos(self):
        """Position (monde) du bout du canon, pour faire partir la balle."""
        cx = self.x + self.width / 2
        dx, dy = MUZZLE_OFFSET
        return (cx + (dx if self.facing_right else -dx), self.y - dy)

    # ------------------------------------------------------------------
    # Mise a jour
    # ------------------------------------------------------------------
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

        self.invuln_ms = max(0, self.invuln_ms - dt_ms)
        self.shoot_cooldown_ms = max(0, self.shoot_cooldown_ms - dt_ms)

        self._update_animation(dt_ms)
        self._process_lock(dt_ms)

    def _process_lock(self, dt_ms):
        if not self.lock:
            return
        self.lock_timer += dt_ms

        # Evenements au bon moment de l'animation
        if self.lock == "shoot" and not self._shot_fired:
            if self._event_reached(default_frame=1, fallback_ms=SHOOT_FIRE_DELAY_MS):
                self._shot_fired = True
                self._shot_ready = True
        elif self.lock == "takedown" and not self._td_fired:
            if self._event_reached(default_frame=None, fallback_ms=TAKEDOWN_HIT_DELAY_MS):
                self._td_fired = True
                self._td_ready = True

        if self.lock == "dead":
            return  # reste mort jusqu'au reset()

        done = self.anim.finished if (self._anim_driven and self.anim) \
            else self.lock_timer >= FALLBACK_LOCK_MS[self.lock]
        if done:
            self.lock = None
            self.state = "idle"

    def _event_reached(self, default_frame, fallback_ms):
        if self._anim_driven and self.anim and self.anim.current_anim:
            sheet, name = self.spritesheet, self.anim.current_anim
            count = sheet.frame_count(name)
            if default_frame is None:
                default_frame = count // 2
            return self.anim.frame_index >= min(sheet.anim_event_frame(name, default_frame), count - 1)
        return self.lock_timer >= fallback_ms

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------
    def _resolve(self, key):
        """Premiere animation de la liste CANDIDATES qui existe dans le spritesheet."""
        if not self.spritesheet:
            return None
        prefix = "pistol_" if self.armed else ""
        for name, mode, squash in CANDIDATES.get(key, []):
            name = name.format(p=prefix)
            if self.spritesheet.has(name):
                return name, mode, squash
        return None

    def _update_animation(self, dt_ms):
        if not self.anim:
            return
        key = self.lock or self.state
        res = self._resolve(key)
        if res is None:
            self._squash = False
            return
        name, mode, squash = res
        self._squash = squash
        sheet = self.spritesheet
        fps = sheet.anim_fps(name, ANIM_FPS.get(name, ANIM_FPS.get(key, DEFAULT_ANIM_FPS)))

        if mode == "loco":
            self.anim.play(name, loop=True, fps=fps)
            stride = sheet.anim_stride(name, STRIDE_PX.get(key, 96))
            # cycles/s = vitesse / stride ; frames/s = nb_frames * cycles/s
            self.anim.fps = sheet.frame_count(name) * abs(self.vel_x) / stride
            self.anim.update(dt_ms)

        elif mode == "play":
            loop = sheet.anim_loop(name, name not in ONE_SHOT)
            self.anim.play(name, loop=loop, fps=fps)
            self.anim.update(dt_ms)

        elif mode == "freeze":
            self.anim.play(name, loop=True, fps=fps)
            self.anim.freeze(0)

        elif mode == "once":
            self.anim.play(name, loop=False, fps=fps)
            self.anim.update(dt_ms)

    def get_render_info(self):
        """Retourne (frame_surface_or_None, rect, is_sneak_fallback) pour l'affichage."""
        rect = pygame.Rect(int(self.x), int(self.y - self.height), self.width, self.height)

        if not self.anim or self.anim.current_anim is None:
            return None, rect, False

        flip = not self.facing_right
        frame = self.anim.get_current_frame(flip=flip)

        if self._squash and frame:
            # Compresse verticalement ~15% pour simuler une posture accroupie
            # en attendant les vraies frames "sneak"/"crouch"
            key = (self.anim.current_anim, self.anim.frame_index, flip)
            squashed = self._squash_cache.get(key)
            if squashed is None:
                squash_height = int(self.height * SQUASH_RATIO)
                squashed = pygame.transform.scale(frame, (self.width, squash_height))
                self._squash_cache[key] = squashed
            frame = squashed
            rect = pygame.Rect(int(self.x), int(self.y - frame.get_height()), self.width, frame.get_height())

        return frame, rect, self._squash

    def draw_props(self, surface, camera_x):
        """Dessine le 9mm de remplacement tant qu'il n'y a pas d'animations 'pistol_*'."""
        if not self.armed or self.has_pistol_art or self.dead:
            return
        direction = 1 if self.facing_right else -1
        mx, my = self.muzzle_pos()
        crouch_drop = 18 if self.state in ("sneak", "crouch") else 0
        my += crouch_drop
        mx -= camera_x
        grip_x = mx - direction * 34
        # pistolet (gris fonce) + silencieux (plus long, plus clair)
        pygame.draw.line(surface, (35, 35, 35), (grip_x, my), (mx - direction * 12, my), 7)
        pygame.draw.line(surface, (90, 90, 95), (mx - direction * 12, my), (mx, my), 5)