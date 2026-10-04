# LaMain

The smallest three-finger end-effector with tactile feedback that replaces the SO-101 gripper, and succeeds at a task the gripper fails, with the dataset and policy to prove it.

BOM: https://docs.google.com/spreadsheets/d/1QRkrFNEr4OLIYoRjOxhvR7IqRy3qPOLTq45OjTfyoFY/edit?usp=sharing

---

# La Main

Main robotique custom à 5 servos Feetech SCS0009, inspirée de l'AmazingHand
(Pollen Robotics). Objectif : après montage, **une seule commande** calibre la
main, et une **même commande articulaire** donne la même pose physique sur
toutes les mains La Main (portabilité téléopération / IA).

Alimentation : **6 V**.

## Architecture

```
lamain/                       workspace uv
├── packages/lamain-core/     bibliothèque
│   └── src/lamain_core/
│       ├── bus.py            driver rustypot réel + FakeBus
│       ├── model.py          lecture de hand_model.yaml
│       ├── calibration.py    F3/F4
│       ├── safety.py         F6
│       └── controller.py     F5 HandController
├── tools/setup-servo/        CLI `lamain` (F1/F2/F3/F7) + scripts legacy
├── config/hand_model.yaml    description de la conception (versionnée CAO)
├── calibration/              un JSON par main
├── demos/gestures/           gestes (poses nommées)
├── demos/episodes/           épisodes (séquences)
├── logs/                     sorties par run, ignorées par git
│   ├── calibration/<date>_<serial>/sweep.csv
│   ├── inspect/<date>_<serial>/<joint>.csv + .png + summary.{txt,json}
│   └── collect/<date>_<serial>/poses.csv
└── tests/                    tests FakeBus (CI, sans matériel)
```

Le code client ne parle **jamais** directement aux servos : uniquement à
`HandController`, avec des noms d'articulation (`index_flex`, `middle_flex`,
`index_middle_abd`, `thumb_rot`, `thumb_flex`) et des radians (ou des
coordonnées normalisées `[-1, 1]`).

## Installation

```bash
uv sync            # installe le workspace + deps
uv run pytest      # tests FakeBus, sans matériel
```

## Matériel

- Servos chaînés sur le bus Feetech, carte Waveshare Bus Servo Adapter (A).
- Alim **6 V**, câble USB sur `/dev/ttyACM0`, utilisateur dans `dialout`.
- **Palonniers non vissés** au départ.

## Procédure de calibration (une seule commande)

Palonniers **non vissés** au départ. Alim 6 V, bus sur `/dev/ttyACM0` :

```bash
uv run lamain calibrate
```

Ce que fait la commande, dans l'ordre :

1. vérifie les préconditions (5 IDs, tension, température) et demande de
   confirmer que la main est libre ;
2. **met TOUS les servos à `0°`** (511 ticks) ;
3. **pause** : tu emboîtes les palonniers pour une main **étendue** (vers le
   haut), puis tu appuies sur Entrée ;
4. pour chaque articulation, **un doigt à la fois** : mise à `0°` de tous →
   balayage flexion/extension → **retour de tous à `0°`** → doigt suivant.
   Ordre : `index_flex → middle_flex → index_middle_abd → thumb_rot →
   thumb_flex` ;
5. écrit `calibration/<serial>.json` + journal CSV dans `logs/`.

Options :
- `--yes` : ne demande aucune confirmation (utile pour scripter).
- `--verify` : compare la course mesurée au nominal de la CAO.
- `--repeat 2` : répète et vérifie la répétabilité (≤ 2 pas).
- `--batch` : désactive l'isolation (calibration d'affilée).
- `--serial LM-0001` : numéro de série de la main.
- Le balayage **affiche sa progression**, s'arrête au bout de `joint_timeout_s`
  (60 s) par articulation, et **abandonne avec un message clair** si une
  articulation ne rejoint pas son zéro (bloquée / palonnier mal monté).
- `--tag apres_pouce` : suffixe du fichier de sortie.
- Chaque calibration est **conservée** : si `LM-0001.json` existe, la suivante
  s'écrit `LM-0001_2.json`, puis `_3`, etc. Tu peux donc choisir ta calibration.

Chaque articulation a un `type` dans `config/hand_model.yaml` :
`crank` (manivelle, point mort) ou `two_stop` (butée de chaque côté). Pour les
`two_stop`, `reference_side` choisit le zéro : `auto` (plus grande portée),
`stop_low`, `stop_high`, ou `mount` (zéro palonnier). Un statut `uncertain`
signale une butée douteuse (molle, ou collée à la fin de course du servo).

`lamain assemble` reste disponible si tu veux seulement mettre à `0°` et
monter les palonniers sans calibrer.

### Essai sans matériel

```bash
uv run lamain --simulate calibrate --serial TEST --yes
```

Déroule toute la logique sur le FakeBus (butées, point mort, charge, pannes).

## Diagnostic d'une articulation

Balaie une articulation sur toute la course et montre où elle s'arrête, si
chaque butée est **mécanique** ou la **fin interne du servo**, la charge, la
température, la tension, et les limites EEPROM :

```bash
uv run lamain inspect                 # toutes les articulations
uv run lamain inspect thumb_rot --plot
```

Sorties : un dossier par inspection `logs/inspect/<date>_<serial>/` contenant
`<joint>.csv`, `<joint>.png` (activé par défaut, `--no-plot` pour l'enlever) et
un `summary.txt` / `summary.json`. Options : `--step`, `--torque`, `--end-margin`.

Couples : le **balayage** est à 60 % et la **poussée** (vérification de butée) à
100 %, identiques pour toutes les articulations. `--torque N` change le couple
d'inspection.

## Démo : studio de gestes et d'épisodes

Enregistre des poses au clavier, réutilise-les comme briques, et rejoue vite
pour filmer.

```bash
uv run lamain studio          # menu guidé
uv run lamain demo play demo1 # rejoue un épisode (rapide, en boucle)
```

- **Jog** (dans le studio) : `0/1` index, `2/3` majeur, `4/5` abduction,
  `6/7` base pouce, `8/9` flexion pouce (pas de 3° par appui, toujours borné).
  Chaque articulation va **dans les deux sens** (`q=-1` une butée, `q=+1` l'autre).
- **Sauver un geste** : au jog, appuie sur **`s`**, tape le **nom**, Entrée → sauvegardé.
- **Avant toute action** (créer un geste, un épisode, jouer), la main est
  **ramenée au zéro** `q = 0` et on attend que la pose soit atteinte.
- **Geste** : une pose nommée, sauvegardée dans `demos/gestures/<nom>.json`
  (un nom déjà pris est écrasé).
- **Épisode** : une séquence de pas (`keypoint` et/ou `gesture`) dans
  `demos/episodes/` (noms jamais écrasés : `_2`, `_3`…).
- **Jouer** : le studio propose « Play an episode » et « Play a gesture ».
  En ligne de commande : `lamain demo play <nom>` (épisode **ou** geste).
- **Gérer** (studio → « Manage », ou CLI) : **modifier**, **renommer**,
  **supprimer** un geste ou un épisode.
  - modifier un geste : la main va à la pose, tu ajustes au jog, puis `s`
    (écrase) ou `n` (nouveau nom) ;
  - modifier un épisode : éditeur complet (ajouter keypoints/gestes, undo,
    preview, save qui écrase) ;
  - CLI : `lamain gesture show|rename|delete`, `lamain episode show|rename|delete`.
- **Play = durée proportionnelle à la distance** (le plus rapide possible) et
  on **attend** que chaque pose soit réellement atteinte avant la suivante.
- Insérer un geste dans un épisode **déplace réellement la main** jusqu'à la
  pose, et l'épisode stocke une **référence au nom** : si tu supprimes le geste
  et le remplaces par un autre **du même nom**, l'épisode utilise **le nouveau**.

Le **zéro logique `q=0`** est réglé par `config/hand_model.yaml` :
`calibration.reference_mode: middle` (milieu des deux butées, **défaut**) ou
`mount` (zéro palonnier). `middle` garde les deux sens symétriques même si le
palonnier est monté près d'une butée. `q=-1` / `q=+1` atteignent les deux butées.
- Les poses sont stockées **normalisées `[-1,1]`** (portables entre mains) plus
  en radians. `q = -1` = une butée, `q = +1` = l'autre ; `q = 0` = milieu de la
  course, donc **chaque servo se pilote dans les deux sens** au jog. Le bornage
  de calibration est **toujours** appliqué.
- Arrêt propre sur `Ctrl-C` et si température/tension sortent des bornes.

`demos/` est **versionné** : tu gardes tes gestes et épisodes.

## Utiliser la main (F5)

```python
from lamain_core.controller import HandController

ctrl = HandController.from_files("calibration/LM-0001.json")
ctrl.connect()
ctrl.enable_torque("grasp")                 # calib | free | default | grasp
print(ctrl.get_joint_positions())           # {nom: rad}
ctrl.set_joint_positions({"index_flex": 0.5})
ctrl.set_normalized({"index_flex": 0.8})    # [-1, 1]
ctrl.disconnect()
```

Toute consigne passe par le filtre de sécurité F6 : bornage articulaire,
limitation de saut, couple par mode, et jamais de franchissement du point mort
des manivelles. `write_hardware_limits()` écrit en plus les butées min/max dans
l'EEPROM des servos (filet si le logiciel plante).

## Garde-fous V1 (F6)

- Bornage logiciel (mode `clamp` ou `strict`).
- Limites matérielles EEPROM (registres min/max position).
- Couple par mode : `calib` faible, `free` modéré, `default`, `grasp` élevé.
- Vitesse max et limitation du saut par cycle.
- Surveillance température / tension / charge.
- Branche des manivelles : interdiction de traverser le point mort.

## Hors périmètre V1 (préparé)

- **Collisions entre doigts** : la collecte est prête (`lamain
  collect-collisions`), le modèle et le filtre viennent en V2.
- Contrôle de force pour la préhension.
- Téléopération / IA.

## Documentation

- Spec détaillée : ce fichier + `config/hand_model.yaml`.
- Scripts legacy (debug manuel d'un servo) : `tools/setup-servo/calib.py`,
  `tools/setup-servo/GUIDE.md`.
