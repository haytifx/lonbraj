"""
save_manager.py
----------------
Gere la sauvegarde de progression du joueur : quels chapitres sont
debloques, ou il en est rendu. Sauvegarde en JSON simple dans
data/save.json -- facile a inspecter/modifier a la main si besoin
pendant les tests.

Si aucun fichier de sauvegarde n'existe (premiere fois que le joueur
lance le jeu), on considere que c'est une nouvelle partie.
"""

import json
import os

SAVE_PATH = "data/save.json"

DEFAULT_SAVE = {
    "unlocked_chapters": [1],   # le chapitre 1 est toujours debloque
    "last_chapter": 1,
    "intro_seen": False,        # True apres la premiere lecture de l'intro narrative
}


class SaveManager:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if os.path.exists(SAVE_PATH):
            try:
                with open(SAVE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print("[SaveManager] Fichier de sauvegarde corrompu, nouvelle sauvegarde creee.")
        return dict(DEFAULT_SAVE)

    def save(self):
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def has_progress(self):
        """True si le joueur a deja commence a jouer (pas juste chapitre 1 par defaut)."""
        return self.data["last_chapter"] > 1 or len(self.data["unlocked_chapters"]) > 1

    def is_unlocked(self, chapter_id):
        return chapter_id in self.data["unlocked_chapters"]

    def unlock_chapter(self, chapter_id):
        if chapter_id not in self.data["unlocked_chapters"]:
            self.data["unlocked_chapters"].append(chapter_id)
            self.data["unlocked_chapters"].sort()
        self.save()

    def complete_chapter(self, chapter_id):
        """A appeler quand un chapitre est termine : debloque le suivant."""
        next_chapter = chapter_id + 1
        self.unlock_chapter(next_chapter)
        self.data["last_chapter"] = next_chapter
        self.save()

    def get_last_chapter(self):
        return self.data["last_chapter"]

    def has_seen_intro(self):
        return self.data.get("intro_seen", False)

    def mark_intro_seen(self):
        self.data["intro_seen"] = True
        self.save()

    def reset(self):
        self.data = dict(DEFAULT_SAVE)
        self.save()


# Instance unique partagee par tout le jeu
save_manager = SaveManager()
