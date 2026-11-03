# Lonbraj — Estrikti pwojè a

## Enstalasyon
```
pip install -r requirements.txt
python main.py
```

## Non dosye egzat pou chak asset

### Pèsonaj (James)
Apre ou fin travay nan pwojè `Spritesheet_builder` (split_grid.py → remove_bg.py →
build_spritesheet.py), kopye rezilta final la (2 fichye) isit la:
```
assets/characters/james/james_spritesheet.png
assets/characters/james/james_spritesheet.json
```
Se `settings.py` ki di kote yo ye — pa chanje non yo san w pa chanje `settings.py` tou.

### Splash screen (premye ekran lè jwèt la lanse)
```
assets/ui/splash.png     (1280x720)
```

### Meni prensipal
```
assets/ui/menu_background.png     (1280x720)
```

### Poster/afich jwèt la (généré ak Gemini)
Ka menm imaj ak splash.png, oswa yon vèsyon separe si ou vle yon poster
pou pwomosyon apa. Mete l tou nan `assets/ui/` si ou itilize l nan jwèt la.

### Imaj sinematik (chapit pa chapit)
```
assets/cutscenes/chapter1_opening.png
assets/cutscenes/chapter1_closing.png
assets/cutscenes/chapter2_opening.png
...
```
Chak chapit gen omwen 2: yon imaj ouvèti, yon imaj klotiraj.

### Background nivo jwe a (parallax, 3 kouch pa nivo)
```
assets/backgrounds/level1_marche/layer1_sky.png
assets/backgrounds/level1_marche/layer2_mid.png
assets/backgrounds/level1_marche/layer3_ground.png
```
Repete pou chak nivo: `level2_depo/`, `level3_biwo/`, `level4_katye_anwo/`, `level5_katye_jeneral/`

### Mizik
```
assets/audio/music/menu_theme.ogg
assets/audio/music/chapter1_theme.ogg
assets/audio/music/chapter2_theme.ogg
assets/audio/music/boss_theme.ogg
```

### Efè sonò (SFX)
```
assets/audio/sfx/footstep.wav
assets/audio/sfx/punch.wav
assets/audio/sfx/alert.wav          <- lè yon gad remake James
assets/audio/sfx/hurt.wav
assets/audio/sfx/pickup.wav          <- ranmase yon objè/dosye
assets/audio/sfx/menu_select.wav
assets/audio/sfx/menu_confirm.wav
```

### Dyalòg / sinematik (tèks, pa kòd)
```
data/dialogues/chapter1_opening.json
data/dialogues/chapter1_closing.json
data/dialogues/chapter2_opening.json
...
```
Gade `data/dialogues/chapter1_opening.json` kòm egzanp fòma a.

---

## Kouman chak moso jwèt la separe (arsitekti a)

| Fichye | Responsablite |
|---|---|
| `main.py` | Lanse jwèt la, boukle prensipal la sèlman |
| `settings.py` | Tout konstant (chemen, koulè, gwosè ekran) |
| `src/scene_manager.py` | Deside ki "ekran" ki aktif kounye a |
| `src/scenes/splash_scene.py` | Ekran lansman |
| `src/scenes/menu_scene.py` | Meni prensipal |
| `src/scenes/cutscene_scene.py` | Sinematik (imaj + tèks) |
| `src/entities/animation.py` | Li spritesheet la, jwe animasyon |
| `src/audio/audio_manager.py` | Mizik ak SFX |
| `data/dialogues/*.json` | Tèks dyalòg — modifye san w pa touche kòd |

Chak moso ka modifye poukont li san l pa kraze lòt yo. Egzanp: si ou vle
chanje jan meni an parèt, ou jis touche `menu_scene.py` — `main.py`,
`cutscene_scene.py`, elatriye pa afekte menm si ou modifye byen fon.

## Sa ki rete pou fè
- [ ] `src/scenes/level_scene.py` — nivo jouwab la (mouvman, parallax, koliziyon)
- [ ] `src/entities/player.py` — lojik jwè a (kontwòl, eta: idle/walk/sneak...)
- [ ] `src/ui/dialogue_box.py` — si ou vle dyalòg nan mitan gameplay la (pa sèlman sinematik)
