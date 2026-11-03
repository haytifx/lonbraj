"""
settings.py
-----------
Toutes les constantes du jeu au meme endroit. Si tu veux changer la taille
de l'ecran, les couleurs, ou les chemins de dossiers, c'est toujours ici
et nulle part ailleurs -- pas besoin de fouiller dans 10 fichiers.
"""

# --- Ecran ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GAME_TITLE = "Lonbraj"

# --- Couleurs (R, G, B) ---
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GREY = (40, 40, 40)
COLOR_ACCENT = (200, 30, 30)  # rouge sobre, pour les menus/titres
COLOR_NEON_GOLD = (255, 210, 40)  # couleur de l'option de menu selectionnee

# --- Chemins de dossiers (relatifs a la racine du projet) ---
ASSETS_DIR = "assets"
CHARACTERS_DIR = f"{ASSETS_DIR}/characters"
BACKGROUNDS_DIR = f"{ASSETS_DIR}/backgrounds"
UI_DIR = f"{ASSETS_DIR}/ui"
CUTSCENES_DIR = f"{ASSETS_DIR}/cutscenes"
MUSIC_DIR = f"{ASSETS_DIR}/audio/music"
SFX_DIR = f"{ASSETS_DIR}/audio/sfx"
DIALOGUES_DIR = "data/dialogues"

# --- Personnage ---
PLAYER_SPRITESHEET = f"{CHARACTERS_DIR}/james/james_spritesheet.png"
PLAYER_SPRITESHEET_META = f"{CHARACTERS_DIR}/james/james_spritesheet.json"

# --- Volume par defaut ---
DEFAULT_MUSIC_VOLUME = 0.5
DEFAULT_SFX_VOLUME = 0.7

# --- Debug (SEULEMENT pour les tests -- remettre False avant de livrer le jeu) ---
# Si True : la cinematique d'intro rejoue a CHAQUE lancement du jeu, meme si
# elle a deja ete vue. Utile pour revoir/tester l'intro sans effacer toute la
# sauvegarde (progression des chapitres). Remettre a False pour les vrais joueurs.
DEBUG_FORCE_REPLAY_INTRO = True
