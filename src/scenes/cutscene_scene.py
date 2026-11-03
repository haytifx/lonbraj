"""
cutscene_scene.py
------------------
Gere les cinematiques "legeres" (image fixe + texte + voix optionnelle).

FONDU ENTRE IMAGES :
Quand la ligne suivante utilise une image differente de la precedente,
un fondu (crossfade) de FADE_DURATION ms se joue automatiquement -- pas
besoin de le specifier dans le JSON, c'est detecte tout seul.

SYNCHRO VOIX/IMAGE :
Si une ligne a un champ "voice", l'image et le texte de cette ligne
restent affiches TANT QUE la voix n'est pas terminee -- meme si le texte
est deja entierement affiche. L'image ne peut donc jamais "partir" avant
que le narrateur ait fini de parler. Des que la voix termine, la ligne
suivante commence (avec son propre fondu si l'image change).

FORMAT JSON (voir data/dialogues/intro_narration.json pour un exemple 
complet) :
[
    {"image": "intro_1.png", "speaker": null, "text": "...", "voice": "intro_1.ogg"},
    ...
]
"""

import pygame
import os
import json
import settings
from src.audio.audio_manager import audio

FADE_DURATION = 600  # ms, duree du fondu entre deux images differentes


class CutsceneScene:
    def __init__(self, dialogue_file, on_finish, background_music=None):
        """background_music : nom de fichier optionnel dans assets/audio/music/
        (ex: 'intro_theme.ogg') -- joue en boucle pendant toute la cutscene,
        et s'arrete quand la cutscene se termine."""
        self.on_finish = on_finish
        self.background_music = background_music
        self.lines = self._load_dialogue(dialogue_file)
        self.current_line = -1
        self.image_cache = {}

        self.speaker_font = pygame.font.Font(None, 36)
        self.text_font = pygame.font.Font(None, 32)

        self.displayed_chars = 0
        self.type_timer = 0
        self.type_speed = 40
        self.has_voice_this_line = False

        self.prev_image = None       # image de la ligne precedente (pour le fondu)
        self.current_image = None
        self.fade_timer = FADE_DURATION  # commence "termine" (pas de fondu au tout debut)

        if self.background_music:
            audio.play_music(self.background_music)

        self._advance()

    def _load_dialogue(self, filename):
        path = os.path.join(settings.DIALOGUES_DIR, filename)
        if not os.path.exists(path):
            print(f"[CutsceneScene] Dialogue introuvable : {path}")
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_image(self, filename):
        if filename not in self.image_cache:
            path = os.path.join(settings.CUTSCENES_DIR, filename)
            if os.path.exists(path):
                img = pygame.image.load(path).convert()
                img = pygame.transform.scale(img, (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
                self.image_cache[filename] = img
            else:
                self.image_cache[filename] = None
                print(f"[CutsceneScene] Image introuvable : {path}")
        return self.image_cache[filename]

    def _advance(self):
        audio.stop_voice()
        self.current_line += 1
        self.displayed_chars = 0
        self.type_timer = 0

        if self.current_line >= len(self.lines):
            if self.background_music:
                audio.stop_music()
            self.on_finish()
            return

        line = self.lines[self.current_line]
        new_image = self._get_image(line["image"])

        if new_image is not self.current_image:
            self.prev_image = self.current_image
            self.current_image = new_image
            self.fade_timer = 0  # demarre un nouveau fondu
        else:
            self.fade_timer = FADE_DURATION  # meme image, pas de fondu

        voice_file = line.get("voice")
        if voice_file:
            self.has_voice_this_line = audio.play_voice(voice_file)
        else:
            self.has_voice_this_line = False

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.current_line >= len(self.lines):
                return
            current_text = self.lines[self.current_line]["text"]
            if self.displayed_chars < len(current_text):
                self.displayed_chars = len(current_text)
            elif not self.has_voice_this_line:
                # Ne permet de passer manuellement que s'il n'y a PAS de voix
                # en cours -- on ne coupe jamais un narrateur qui parle encore.
                self._advance()

    def update(self, dt):
        if self.current_line >= len(self.lines):
            return

        if self.fade_timer < FADE_DURATION:
            self.fade_timer = min(FADE_DURATION, self.fade_timer + dt)

        current_text = self.lines[self.current_line]["text"]

        if self.has_voice_this_line:
            self.displayed_chars = len(current_text)
            if not audio.is_voice_playing():
                self._advance()
        else:
            if self.displayed_chars < len(current_text):
                self.type_timer += dt
                chars_to_show = int(self.type_timer / 1000 * self.type_speed)
                self.displayed_chars = min(chars_to_show, len(current_text))

    def draw(self, surface):
        if self.current_line >= len(self.lines):
            return

        line = self.lines[self.current_line]

        if self.current_image:
            surface.blit(self.current_image, (0, 0))
        else:
            surface.fill(settings.COLOR_BLACK)

        # Fondu : l'ancienne image (opacite decroissante) par-dessus la nouvelle
        if self.fade_timer < FADE_DURATION and self.prev_image:
            alpha = int(255 * (1 - self.fade_timer / FADE_DURATION))
            faded = self.prev_image.copy()
            faded.set_alpha(alpha)
            surface.blit(faded, (0, 0))

        box_height = 160
        box_rect = pygame.Rect(0, settings.SCREEN_HEIGHT - box_height, settings.SCREEN_WIDTH, box_height)
        box_surface = pygame.Surface((box_rect.width, box_rect.height))
        box_surface.set_alpha(200)
        box_surface.fill(settings.COLOR_BLACK)
        surface.blit(box_surface, box_rect.topleft)

        y = box_rect.top + 20
        if line.get("speaker"):
            speaker_text = self.speaker_font.render(line["speaker"], True, settings.COLOR_ACCENT)
            surface.blit(speaker_text, (40, y))
            y += 40

        visible_text = line["text"][:self.displayed_chars]
        text_surface = self.text_font.render(visible_text, True, settings.COLOR_WHITE)
        surface.blit(text_surface, (40, y))
