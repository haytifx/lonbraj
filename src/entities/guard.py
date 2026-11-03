"""
guard.py
--------
Un garde qui patrouille entre deux points et surveille devant lui.

MECANIQUE DE DETECTION (infiltration) :
- Le garde voit seulement DEVANT lui (cone de vision). Dans son dos, le
  joueur est invisible.
- Quand il voit le joueur, il s'arrete, se tourne vers lui, et sa jauge de
  detection se remplit (DETECT_TIME_MS). Si elle arrive a 1.0 : le joueur
  est repere (le level_scene decide quoi faire -- voir LevelScene).
- Si le joueur disparait, la jauge redescend doucement (DECAY_TIME_MS) et
  le garde reprend sa patrouille quand elle est a zero.
- La portee de vision est reduite par le level_scene quand le joueur est
  accroupi (sneak) ou dans une zone d'ombre (voir vision_rect(range_mult)).

PLACEHOLDER : pas encore de sprite de garde -> un rectangle est dessine.
Quand un spritesheet existera, il suffira de remplacer draw_body().
"""

import pygame

GUARD_WIDTH = 60
GUARD_HEIGHT = 128

PATROL_SPEED = 70            # pixels/s (plus lent que le joueur : 220)
END_PAUSE_MS = 800           # pause a chaque bout de la patrouille
DEFAULT_VISION_RANGE = 320   # pixels devant le garde

DETECT_TIME_MS = 900         # temps pour etre repere en restant visible
DECAY_TIME_MS = 2000         # temps pour que la jauge retombe de 1.0 a 0

BODY_COLOR = (150, 35, 35)
BODY_ALERT_COLOR = (230, 60, 30)
CONE_COLOR = (255, 230, 80)
CONE_ALERT_COLOR = (255, 90, 40)


class Guard:
    def __init__(self, x_left, x_right, ground_y, speed=PATROL_SPEED,
                 vision_range=DEFAULT_VISION_RANGE, start_facing_right=True):
        self.x_left = x_left       # bord gauche de la patrouille (position du coin gauche du garde)
        self.x_right = x_right     # bord droit de la patrouille
        self.ground_y = ground_y
        self.speed = speed
        self.vision_range = vision_range
        self._start_facing_right = start_facing_right
        self.width = GUARD_WIDTH
        self.height = GUARD_HEIGHT
        self.reset()

    def reset(self):
        """Remet le garde a son point de depart (utilise quand le niveau recommence)."""
        self.x = self.x_left if self._start_facing_right else self.x_right
        self.facing_right = self._start_facing_right
        self.detection = 0.0         # 0.0 = rien vu, 1.0 = joueur repere
        self.pause_timer = 0
        self._was_suspicious = False

    # ------------------------------------------------------------------
    # Geometrie
    # ------------------------------------------------------------------
    @property
    def rect(self):
        return pygame.Rect(int(self.x), self.ground_y - self.height, self.width, self.height)

    def vision_rect(self, range_mult=1.0):
        """Rectangle devant le garde dans lequel il voit le joueur.
        range_mult < 1 raccourcit la portee (joueur accroupi, dans l'ombre...)."""
        length = int(self.vision_range * range_mult)
        body = self.rect
        if self.facing_right:
            return pygame.Rect(body.right, body.top, length, body.height)
        return pygame.Rect(body.left - length, body.top, length, body.height)

    # ------------------------------------------------------------------
    # Logique
    # ------------------------------------------------------------------
    def update(self, dt_ms, sees_player, player_center_x):
        """Met a jour le garde. Retourne True UNIQUEMENT a l'instant ou il
        commence a remarquer le joueur (pour jouer un son d'alerte une fois)."""
        just_noticed = False

        if sees_player:
            # Il s'arrete et regarde le joueur
            self.facing_right = player_center_x >= self.rect.centerx
            self.detection = min(1.0, self.detection + dt_ms / DETECT_TIME_MS)
        else:
            self.detection = max(0.0, self.detection - dt_ms / DECAY_TIME_MS)

        suspicious = self.detection > 0.0
        if suspicious and not self._was_suspicious:
            just_noticed = True
        self._was_suspicious = suspicious

        # Tant qu'il est mefiant (jauge > 0), il reste sur place
        if not suspicious:
            self._patrol(dt_ms)

        return just_noticed

    def _patrol(self, dt_ms):
        if self.pause_timer > 0:
            self.pause_timer -= dt_ms
            return

        step = self.speed * dt_ms / 1000
        if self.facing_right:
            self.x += step
            if self.x >= self.x_right:
                self.x = self.x_right
                self.facing_right = False
                self.pause_timer = END_PAUSE_MS
        else:
            self.x -= step
            if self.x <= self.x_left:
                self.x = self.x_left
                self.facing_right = True
                self.pause_timer = END_PAUSE_MS

    # ------------------------------------------------------------------
    # Affichage
    # ------------------------------------------------------------------
    def draw(self, surface, camera_x, range_mult=1.0, font=None):
        body = self.rect.move(-camera_x, 0)
        self._draw_vision_cone(surface, body, range_mult)
        self.draw_body(surface, body)
        self._draw_detection_bar(surface, body, font)

    def draw_body(self, surface, body):
        """PLACEHOLDER : a remplacer par un sprite quand il sera pret."""
        color = BODY_ALERT_COLOR if self.detection > 0 else BODY_COLOR
        pygame.draw.rect(surface, color, body)
        # "Oeil" pour montrer dans quelle direction il regarde
        eye_x = body.right - 14 if self.facing_right else body.left + 6
        pygame.draw.rect(surface, (255, 255, 255), (eye_x, body.top + 20, 8, 8))

    def _draw_vision_cone(self, surface, body, range_mult):
        length = int(self.vision_range * range_mult)
        eye_y = body.top + 24
        if self.facing_right:
            start_x = body.right
            far_x = start_x + length
        else:
            start_x = body.left
            far_x = start_x - length

        points = [(start_x, eye_y), (far_x, body.top), (far_x, body.bottom)]
        color = CONE_ALERT_COLOR if self.detection > 0 else CONE_COLOR

        min_x = min(p[0] for p in points)
        min_y = min(p[1] for p in points)
        w = max(1, max(p[0] for p in points) - min_x)
        h = max(1, max(p[1] for p in points) - min_y)
        cone_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        local_points = [(px - min_x, py - min_y) for px, py in points]
        pygame.draw.polygon(cone_surface, (*color, 55), local_points)
        surface.blit(cone_surface, (min_x, min_y))

    def _draw_detection_bar(self, surface, body, font):
        if self.detection <= 0:
            return
        bar_w = self.width
        bar_rect = pygame.Rect(body.left, body.top - 14, bar_w, 6)
        pygame.draw.rect(surface, (40, 40, 40), bar_rect)
        fill = bar_rect.copy()
        fill.width = int(bar_w * self.detection)
        pygame.draw.rect(surface, (255, 70, 40), fill)
        if font and self.detection > 0.4:
            mark = font.render("!", True, (255, 220, 60))
            surface.blit(mark, (body.centerx - mark.get_width() // 2, body.top - 44))
