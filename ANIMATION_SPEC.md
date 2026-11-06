# Espesifikasyon animasyon — Lonbraj

Dokiman sa a di egzakteman ki imaj pou kreye (ak Gemini oswa lòt) pou James, kijan
pou non yo ye, ak kijan pou verifye yo. Non animasyon yo **dwe egzat** — se yo
jwèt la chache nan JSON la. Chak animasyon ki manke gen yon repli (jwèt la pa kraze),
kidonk ou ka ajoute yo youn apre lòt.

## 1. Règ pou TOUT frame

- Vi sou kote, James gade **adwat**, tout kò a toujou vizib.
- **Menm gwosè pèsonaj la nan chak frame ak chak animasyon.** Mande Gemini pou l fè tout
  animasyon yo nan menm konvèsasyon an, ak menm imaj referans James lan.
- **Pye yo sou menm liy orizontal nan chak frame** (sòf nan `jump` ak `dead`).
- Fon inifòm vèt pi (`#00FF00`) oswa transparan. **Pa gen tèks, nimewo, etikèt, ni lonbraj sou tè a.**
  (Imaj referans samouraï a gen nimewo ak non rangée yo: se sèlman pou montre, pa mete yo nan frame yo.)
- Non fichye: `<animasyon>_<nimewo>.png` → `walk_1.png`, `walk_2.png`, `pistol_walk_1.png`...
- Chak animasyon yon fwa **yon bann orizontal** nan yon sèl imaj, apre sa ou koupe l (`split_grid.py` → `remove_bg.py`).

## 2. Lis animasyon James

Kolòn **Frames** = kantite ideyal. Fps/loop yo ekri otomatikman nan JSON la (ou ka chanje yo la).

| Non (egzat) | Frames | Fps | Loop | Sa li ye |
|---|---|---|---|---|
| `walk` | **12** (min 8) | 12 | wi | Mache nòmal. 2 pa (goch + dwat) nan yon sik. Gade §3. |
| `sneak` | 8–12 | 10 | wi | **Akoupi-mache** (silansye). Kò a ba (~72 % otè kanpe), jenou pliye. |
| `crouch` | 2 | 4 | wi | Akoupi sou plas (respirasyon). |
| `idle` | 4–6 | 6 | wi | Kanpe san bouje (respirasyon). |
| `jump` | 6 | 10 | non | Prepare, monte, pik, desann, aterisaj. |
| `hurt` | 3–4 | 12 | non | Touche pa yon bal oswa yon kou. |
| `dead` | 6–8 | 10 | non | Tonbe. **Dènye frame = kò a kouche**; jwèt la kenbe l la. |
| `attack` | 3–5 | 12 | non | Kout pwen (egziste deja). |
| `takedown` | 6–8 | 12 | non | Atak pa surprise **dèyè** yon gad (James dèyè l, li kenbe/frape l). Evènman an nan mitan (frame 3). |
| `pistol_idle` | 4 | 6 | wi | Kanpe ak 9mm silansye nan men dwat, bra bese, kanon devan-anba. |
| `pistol_walk` | 12 (min 8) | 12 | wi | Mache ak 9mm la. |
| `pistol_sneak` | 8–12 | 10 | wi | Akoupi-mache ak 9mm la. |
| `pistol_crouch` | 2 | 4 | wi | Akoupi sou plas ak 9mm la. |
| `pistol_aim` | 3 | 12 | non | Leve zam nan pou vize (kanpe). |
| `pistol_shoot` | 4 | 12 | non | Tire. **Frame 2 (index 1) = moman bal la soti** (`event_frame`). Silansye = ti recul, **pa gen flach**. |

Pou yon gad ki tonbe (pita, pou ènmi yo): `fall`, 4–6 frames. Pou kounye a jwèt la desine yon rektang ki tonbe.

## 3. Pou animasyon mache a fluid (sa ki te mal nan spritesheet aktyèl la)

Spritesheet aktyèl la (8 frame `walk`) gen 4 pwoblèm:

1. **Frame 4 pi piti** (113 px kont ~125 px lòt yo): James bèl tèt chanje gwosè.
2. **Pye yo pa sou menm liy** (3 px diferans) ak kò a deplase 9 px sou kote.
3. **Frame 1, 5, 7, 8 prèske menm pòz** (pye kole): pa gen vrè pòz kontak ni pòz pasaj, se sèlman 3-4 pòz diferan.
4. Frame 1 se yon pòz kanpe, pa yon etap mache.

Yon bon sik mache 12 frame:

| Frame | Pòz |
|---|---|
| 1 | **Kontak** — pye goch devan touche tè a |
| 2 | Desann (pwa a desann) |
| 3 | **Pasaj** — pye dwat pase devan |
| 4 | Monte |
| 5 | Pye dwat ap vanse |
| 6 | Prèske kontak |
| 7 | **Kontak** — pye dwat devan touche tè a |
| 8–12 | Menm bagay, mirwa (pye goch pase devan, elatriye) |

Dènye frame a dwe mennen nan frame 1 san kase (boukl). Yon kontak = yon frame kote **de pye yo byen ouvè**.

## 4. Konsènan "60 fps"

Jwèt la deja kouri a **60 FPS**. Men animasyon an pa bezwen 60 desen pa segonn (sa pa posib ni itil). Sa ki fè l fliyid:

1. **Cadans egzak** — korije: ansyen kòd la pèdi tan chak frame (12 fps vin 10,4 fps; nou mezire 104 frame sou 10 s olye de 120).
2. **Vitès animasyon an swiv vitès reyèl James** (`stride`): pye yo pa glise sou tè a.
3. **Frame yo konsistan**: menm gwosè, pye sou menm liy, kò santre (builder la fè sa).
4. **Ase frame**: 12 frame mache a 12–18 fps rete fliyid.

### Ajiste `stride` (pixel pa sik)

`walk` ak `sneak` gen yon `stride` nan JSON la. Valè defo yo (96 ak 72) se **estimasyon**. Pou ajiste yo:

```
python Spritesheet_builder/preview_animation.py assets/characters/james/james_spritesheet.png --anim walk --speed 220
```
Sol la defile a vitès reyèl la. Si James **glise devan** (pye yo pa kole sou tè a) → **diminye** `stride` (`[`).
Si pye yo **ale pi vit pase sol la** → **ogmante** l (`]`). Lè pye yo kole, kopye nimewo a nan JSON la.

## 5. Pwojektil ak obstak

**Bal** — `assets/projectiles/bullet.png`: yon bann orizontal ki gen **frame kare** (lajè = otè imaj la).
Egzanp: 4 frame 16×16 → imaj 64×16. Fon transparan, bal la **vè adwat** (jwèt la vire l si l ale agoch).
Si fichye a pa la, jwèt la desine yon ti liy jòn.

**Obstak pou kache** — `assets/props/cover_crate.png` (oswa lòt non, chanje l nan `main.py`):
PNG transparan, vi sou kote, **ba imaj la = kote l touche tè a**, san lonbraj sou tè a.
Nenpòt gwosè: `main.py` reglè otè a (`Cover(1080, GROUND_Y, height=90, image="cover_crate.png")`).
Rejis: James kanpe ~108 px, akoupi ~78 px → yon obstak ~**90 px** kache James akoupi,
men tèt James kanpe depase. Fè plizyè modèl (kès, miray ba, barik, machin).

## 6. Fabrike spritesheet la

```
cd Spritesheet_builder
python build_spritesheet.py --input frames --output ../assets/characters/james/james_spritesheet.png
python preview_animation.py ../assets/characters/james/james_spritesheet.png --check
```
`--check` montre otè, liy pye, ak santraj chak frame, epi avèti si sa varye twòp.
Si kèk animasyon te desine a yon lòt echèl pase `walk` (lòt imaj Gemini):
`--per-anim sneak,crouch --ratio sneak=0.72 --ratio crouch=0.72`.
Pou yon GIF: `preview_animation.py <sheet> --anim walk --speed 220 --gif walk.gif`.

> **ATANSYON — dosye `Spritesheet_builder/frames/` kounye a melanje:** `walk_1.png` … `walk_8.png` se **samouraï a** (done tès),
> men `attack_*`, `dead_*`, `hurt_*` ak `jump_*` se James. **Pa rebati spritesheet la ak dosye a jan l ye a**, sinon James ap
> mache an samouraï. Ranplase `walk_*` ak frame James yo (oswa vide dosye a epi mete nouvo frame James yo) anvan ou kouri `build_spritesheet.py`.
> Spritesheet ki nan `assets/characters/james/` kounye a (ak James k ap mache) pa chanje: li sèlman rebati lè ou kouri builder la.

## 7. Modèl prompt pou Gemini (anglè, bay imaj referans James lan)

Baz (kopye l chak fwa, chanje liy animasyon an):

```
Using the attached reference image of James (same character, same suit, same sunglasses,
same proportions), draw a sprite animation strip: <ANIMATION> in ONE horizontal row of
<N> frames, evenly spaced, on a solid pure green (#00FF00) background. Side view, facing
right. Full body visible in every frame. SAME character size in every frame. Feet on the
SAME horizontal line in every frame. No text, no numbers, no labels, no shadows on the
ground, no motion blur. The last frame must flow smoothly into the first frame.
```

Ranplase `<ANIMATION>` ak:

- **walk**: `a natural walking cycle (two steps). Frames 1 and 7 are contact poses (front foot touching the ground, legs wide apart), frames 4 and 10 are passing poses`
- **sneak**: `a crouched sneaking walk, body lowered to about 72% of standing height, knees bent, quiet careful steps`
- **crouch**: `a static crouch with a subtle breathing motion`
- **jump**: `a jump: crouch to prepare, take-off, rise, apex, fall, landing (6 frames, not a loop)`
- **hurt**: `a recoil from being hit (bullet or punch), 4 frames`
- **dead**: `being shot and falling to the ground, the last frame lying flat on the ground, 8 frames`
- **pistol_***: ajoute `holding a black 9mm pistol with a long suppressor in his right hand, arm lowered, barrel pointing forward and down` nan chak animasyon (walk, sneak, idle, crouch)
- **pistol_aim**: `raising a suppressed 9mm pistol with both hands to aim forward (3 frames)`
- **pistol_shoot**: `firing a suppressed 9mm pistol: slight recoil, NO muzzle flash (4 frames)`
- **takedown**: `sneaking up behind an enemy guard and grabbing him from behind to take him down silently (8 frames)`
- **bullet**: `a small bullet with a short motion trail, pointing right, 4 frames of 16x16 pixels, transparent background`
- **cover**: `a wooden crate / low concrete wall / barrel, side view, transparent background, bottom of the image touches the ground`
