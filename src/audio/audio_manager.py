"""
audio_manager.py
----------------
Tout ce qui concerne le son est ici. Le reste du jeu ne touche jamais
directement a pygame.mixer -- il appelle juste AudioManager.play_music(),
AudioManager.play_sfx(), etc. Comme ca, si tu changes de systeme audio
plus tard, tu ne modifies qu'un seul fichier.

NOMMAGE DES FICHIERS AUDIO ATTENDU (voir settings.py pour les dossiers) :

assets/audio/music/
    menu_theme.ogg
    chapter1_theme.ogg
    chapter2_theme.ogg
    boss_theme.ogg

assets/audio/sfx/
    footstep.wav
    punch.wav
    alert.wav          <- quand un garde repere le joueur
    menu_select.wav
    menu_confirm.wav
    hurt.wav
    pickup.wav          <- ramasser un objet/dossier

assets/audio/voice/
    chapter1_opening_1.ogg    <- narration pour chaque ligne de dialogue
    chapter1_opening_2.ogg       (voir cutscene_scene.py pour le format)

Format recommande : .ogg pour la musique et les voix (fichiers plus legers),
.wav pour les effets courts (chargement instantane, pas de latence).
"""

import pygame
import os
import settings

VOICE_DIR = f"{settings.ASSETS_DIR}/audio/voice"


class AudioManager:
    def __init__(self):
        pygame.mixer.init()
        self.sfx_cache = {}
        self.music_volume = settings.DEFAULT_MUSIC_VOLUME
        self.sfx_volume = settings.DEFAULT_SFX_VOLUME
        self.voice_volume = 1.0
        self.current_music = None
        # Canal dedie a la voix, separe des SFX/musique pour ne jamais
        # etre coupe par un autre son qui se joue en meme temps.
        self.voice_channel = pygame.mixer.Channel(7)

    def play_music(self, filename, loop=True):
        """filename ex: 'menu_theme.ogg' (juste le nom, pas le chemin complet)"""
        path = os.path.join(settings.MUSIC_DIR, filename)
        if not os.path.exists(path):
            print(f"[AudioManager] Musique introuvable : {path}")
            return
        if self.current_music == filename:
            return  # deja en train de jouer, on ne relance pas
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1 if loop else 0)
            self.current_music = filename
        except pygame.error as e:
            print(f"[AudioManager] Fichier audio corrompu ou invalide : {path}")
            print(f"[AudioManager] Detail : {e}")
            print("[AudioManager] Le jeu continue sans musique -- reconvertis le fichier.")

    def stop_music(self, fade_ms=500):
        pygame.mixer.music.fadeout(fade_ms)
        self.current_music = None

    def play_sfx(self, filename):
        """filename ex: 'punch.wav'"""
        if filename not in self.sfx_cache:
            path = os.path.join(settings.SFX_DIR, filename)
            if not os.path.exists(path):
                print(f"[AudioManager] Effet sonore introuvable : {path}")
                return
            self.sfx_cache[filename] = pygame.mixer.Sound(path)
        sound = self.sfx_cache[filename]
        sound.set_volume(self.sfx_volume)
        sound.play()

    def play_voice(self, filename):
        """filename ex: 'chapter1_opening_1.ogg'. Retourne True si la lecture a demarre."""
        path = os.path.join(VOICE_DIR, filename)
        if not os.path.exists(path):
            print(f"[AudioManager] Fichier vwa introuvable : {path} (fallback tèks sèlman)")
            return False
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(self.voice_volume)
            self.voice_channel.play(sound)
            return True
        except pygame.error as e:
            print(f"[AudioManager] Fichier vwa corrompu : {path} ({e})")
            return False

    def is_voice_playing(self):
        return self.voice_channel.get_busy()

    def stop_voice(self):
        self.voice_channel.stop()

    def set_music_volume(self, value):
        self.music_volume = max(0.0, min(1.0, value))
        pygame.mixer.music.set_volume(self.music_volume)

    def set_sfx_volume(self, value):
        self.sfx_volume = max(0.0, min(1.0, value))


# Instance unique partagee par tout le jeu (pattern singleton simple)
audio = AudioManager()
