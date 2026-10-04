# Guide de calibration — étape par étape

> **Note** : procédure legacy (outil `calib.py`, réglage manuel d'un servo).
> La procédure officielle V1 est `lamain assemble` puis `lamain calibrate`
> (voir le `README.md` à la racine). Alimentation : **6 V**.

Main custom 5 dof. Servos : `1` flexion index, `2` flexion majeur,
`3` abduction index+majeur, `4` base pouce, `5` flexion pouce.

## Prérequis

- Alim **5 V** branchée, servos chaînés sur le bus Feetech.
- Câble USB sur `/dev/ttyACM0`, toi dans le groupe `dialout` (`groups`).
- Palonniers **non vissés**.

## Étape 1 — Vérifier le bus

```bash
cd ~/projects/lamain/setup-servo
uv sync
uv run python scs_id_tool.py --port /dev/ttyACM0 --scan
```

Attendu : les IDs `1 2 3 4 5`. Si non → alim, cavalier A/B, câble, droits.

## Étape 2 — Tester le script de calibration

```bash
uv run python calib.py --help
uv run python calib.py --ids 1,2,3,4,5 --read
```

`--read` affiche les angles courants (en degrés). Note-les, c'est ton point de
départ.

## Étape 2bis — Explorer les angles à la volée

Pour tester un angle précis (ex. 180°) sans relancer le script :

```bash
# Va a MiddlePos+180 puis quitte
uv run python calib.py --ids 2 --middle 30 --goto 180

# Balayage large (ouvert -60, ferme +180)
uv run python calib.py --ids 2 --middle 30 --open -60 --close 180 --cycle
```

Pour piloter en direct (tape l'angle au clavier) :

```bash
uv run python calib.py --ids 2 --middle 30 --interactive
# angle> 180        -> va a MiddlePos+180
# angle> f / o      -> ferme / ouvert
# angle> r          -> revient a MiddlePos
# angle> s 5        -> vitesse 5
# angle> l          -> relit position / couple / temperature
# angle> q          -> quitte
```

Le couple lu (`l`) monte quand le servo force : utile pour repérer une butée
sans attendre qu'il chauffe.

## Étape 3 — Régler la référence d'un servo (ex. index, ID 1)

1. **Figer le servo à 0°** :

   ```bash
   uv run python calib.py --ids 1 --middle 0 --hold
   ```

2. Pendant qu'il tient, **emboîte le palonnier** dans la pose de référence, puis
   **visse M2x4**. Coupe avec `Ctrl-C`.

3. **Balayage ouvert/ferme** :

   ```bash
   uv run python calib.py --ids 1 --middle 0 --cycle
   ```

   Le script alterne fermé (`middle + 90`) et ouvert (`middle - 30`).
   Observe le doigt, puis `Ctrl-C`.

4. **Corriger** : si le doigt ne ferme pas complètement ou butte, change la
   référence de quelques degrés et relance :

   ```bash
   uv run python calib.py --ids 1 --middle 3 --cycle
   ```

   Répète par pas de **3°** jusqu'à ce que la fermeture soit propre, sans que le
   servo force. En cas de doute, refais `--hold` avec la nouvelle valeur, coupe,
   et revois le montage du palonnier.

5. **Note** la valeur finale de `middle` pour l'ID 1.

## Étape 4 — Répéter pour les autres servos

Mêmes commandes, en remplaçant l'ID et, si besoin, les signes :

```bash
uv run python calib.py --ids 2 --middle 0 --hold     # flexion majeur
uv run python calib.py --ids 2 --middle 0 --cycle

uv run python calib.py --ids 3 --middle 0 --hold     # abduction
uv run python calib.py --ids 3 --middle 0 --cycle
```

Pour l'**abduction** (ID 3), la pose de référence = doigts serrés/alignés.
Vérifie que l'écartement max reste dans la plage sûre.

## Étape 5 — Pouce (ID 4 base, ID 5 flexion)

Les deux servos sont empilés. Calibre-les **base puis flexion**, ou les deux
ensemble :

```bash
uv run python calib.py --ids 4,5 --middle 0,0 --hold
uv run python calib.py --ids 4,5 --middle 0,0 --cycle
```

Si leur mécanique est symétrique, utilise des signes opposés :

```bash
uv run python calib.py --ids 4,5 --middle 0,0 --signs 1,-1 --cycle
```

Ajuste les deux `middle` jusqu'à atteindre les deux butées du pouce sans
blocage.

## Étape 6 — Consigner et sauvegarder

1. Écris les `middle_pos` trouvés dans `calibration.json`.
2. Vérifie le JSON :

   ```bash
   uv run python -c "import json; print(json.load(open('calibration.json')))"
   ```

3. Commit git :

   ```bash
   cd ~/projects/lamain
   git add setup-servo/
   git commit -m "Setup servo: IDs + outillage et guide de calibration"
   ```

## Dépannage

- **Servo qui force / chauffe** : `Ctrl-C` immédiat, réduis `--close`/`--open`
  ou corrige `--middle`.
- **Permission denied** : reconnecte ta session (groupe `dialout`).
- **Aucun servo** : alim 5 V, cavalier A/B, câble, sens du connecteur.
- **Sens inversé** : ajoute un signe négatif pour ce servo (`--signs -1`).
