# Calibration — main custom 5 servos

Doc de référence : à relire avant toute manip sur les servos. Résume ce qu'il faut
retenir de l'AmazingHand et ce qui change pour notre main.
Le **pas-à-pas opérationnel** est dans [GUIDE.md](GUIDE.md).

## 1. Notre main

Main custom à **5 servos** (l'AmazingHand d'origine en a 8 : 2 par doigt, en parallèle).

| ID | Rôle |
|----|------|
| 1 | flexion **index** |
| 2 | flexion **majeur** |
| 3 | **abduction** index + majeur |
| 4 | **base pouce** |
| 5 | **flexion pouce** |

Contrairement à l'AmazingHand, il n'y a **pas de paire de palonniers face à face**
par doigt. Les 2 servos du pouce sont empilés mais commandent deux mouvements
distincts (base + flexion), ils se calibrent donc séparément.

## 2. À quoi sert la calibration

Un SCS0009 mesure l'angle de **son** axe, mais son zéro est **arbitraire** par
rapport à la mécanique : le palonnier peut être emboîté dans n'importe quelle
orientation sur les cannelures, et chaque servo est légèrement différent.

La calibration trouve, pour **chaque servo**, l'angle brut qui correspond à une
**pose de référence** du doigt. Cette valeur s'appelle `MiddlePos` (ou `offset`).
Ensuite toute commande s'écrit `MiddlePos + angle` — sans quoi chaque doigt
réagirait différemment et aucune pose (poing, pince…) ne serait reproductible.

Source AmazingHand : `PythonExample/AmazingHand_Demo.py:241-244`
(`np.deg2rad(MiddlePos[0]+Angle_1)`).

## 3. Convention de référence (celle de l'AmazingHand)

D'après `docs/AmazingHand_Assembly.pdf` p. 22-23 :

- On **fige le servo à `MiddlePos` (0° par défaut)** et c'est **à ce moment**
  qu'on emboîte/viss le palonnier. C'est le montage qui crée la référence.
- `AmazingHand_FingerTest.py` balaie : **fermé = `MiddlePos +90`**,
  **ouvert = `MiddlePos -30`** (signes opposés entre les 2 servos d'un doigt).
- Critère de réglage : à la fermeture, la mécanique doit être propre et le servo
  **ne doit jamais forcer en butée**. Sinon on corrige `MiddlePos` de quelques
  degrés et on recommence.

Exemple du PDF : *« right servo horn (ID1) is a bit not far enough
=> New Middle pos should be increased of +3° »*.

Chez nous, le critère « palonniers alignés au plan médian » devient :
- la pose de référence est **reproduite à l'identique** à chaque test ;
- les deux butées (ouvert / fermé) restent **dans la plage sûre** du servo.

## 4. Procédure (résumé)

Outillage : `calib.py` — remplace les deux scripts AmazingHand, gère 1 ou 2
servos, port/offsets/signes paramétrables. Modes : `--hold`, `--cycle`,
`--goto DELTA`, `--interactive` (angles à la volée), `--read`. Détail dans
[GUIDE.md](GUIDE.md).

Pour chaque articulation, palonniers **non vissés** au départ :

1. `--hold` : mettre le(s) servo(s) à `--middle 0`.
2. Emboîter le(s) palonnier(s) dans la pose de référence, visser M2x4.
3. `--cycle` : si le doigt ne ferme pas ou butte, ajuster `--middle` par pas de 3°,
   relancer.
4. Noter `middle_pos`.

Ordre conseillé :
1. flexion **index** (ID 1)
2. flexion **majeur** (ID 2)
3. **abduction** index+majeur (ID 3, référence = doigts serrés/alignés)
4. **base pouce** (ID 4) puis **flexion pouce** (ID 5)

Sécurité : alim **5 V**, vitesse réduite au début, `Ctrl-C` dès qu'un servo force
ou chauffe. Le 6 V est la limite haute des SCS0009 — le 5 V les préserve.

## 5. Résultat à consigner

`calibration.json` : un `middle_pos` par servo.

## 6. État des fichiers

- `setup-servo/scs_id_tool.py` : scan + changement d'ID.
- `setup-servo/calib.py` : outil de calibration (`--hold` / `--cycle` / `--goto` / `--interactive` / `--read`).
- `setup-servo/calibration.json` : résultats (à remplir).
- `setup-servo/GUIDE.md` : pas-à-pas opérationnel.
- Scripts d'origine : `vendor/AmazingHand/PythonExample/AmazingHand_Hand_FingerMiddlePos.py`
  et `AmazingHand_FingerTest.py`.
- Guide matériel : `vendor/AmazingHand/docs/AmazingHand_Assembly.pdf`, p. 22-24.

### Format `calibration.json`

```json
{
  "hand": "custom-5dof",
  "notes": "1 flexion index; 2 flexion majeur; 3 abduction index+majeur; 4 base pouce; 5 flexion pouce",
  "reference": "servo fige a middle_pos, palonnier emboite a cette position (convention AmazingHand). Degres.",
  "servos": {
    "1": { "role": "flexion_index", "middle_pos": 0 },
    "2": { "role": "flexion_majeur", "middle_pos": 0 },
    "3": { "role": "abduction_index_majeur", "middle_pos": 0 },
    "4": { "role": "base_pouce", "middle_pos": 0 },
    "5": { "role": "flexion_pouce", "middle_pos": 0 }
  }
}
```

## 7. À faire / inconnues

- [x] Renseigner la correspondance **ID ↔ rôle**.
- [x] Créer `calib.py`.
- [ ] Passer la calibration et remplir `calibration.json`.
- [ ] Commit git (le repo n'a encore aucun commit).
