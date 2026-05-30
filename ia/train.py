"""
ia/train.py — US-25 + US-26 : Génération dataset + entraînement Isolation Forest
Dataset : 1050 connexions  (1000 normales + 50 suspectes)
Split   : 80% entraînement / 20% test  (stratifié)
Bruit   : cas ambigus ajoutés pour éviter l'overfitting
Usage   : python ia/train.py
"""
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

IA_DIR     = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(IA_DIR, 'model.pkl')
DATA_PATH  = os.path.join(IA_DIR, 'dataset.csv')


# ──────────────────────────────────────────────
# 1. Génération du dataset simulé — US-25
# ──────────────────────────────────────────────
def generate_dataset() -> pd.DataFrame:
    """
    1000 connexions normales  (label = 0)
      50 connexions suspectes (label = 1)

    Bruit ajouté pour éviter l'overfitting :
    - Utilisateurs qui travaillent la nuit (normal mais heure tardive)
    - Utilisateurs en déplacement (nouvelle IP mais comportement normal)
    - Attaques en journée (IP inconnue pendant les heures de bureau)
    - Mots de passe oubliés (plusieurs échecs mais pas une attaque)
    """
    rng = np.random.default_rng(42)

    rows = []

    # ── Connexions normales classiques (700) ──────────────────────
    n = 700
    for _ in range(n):
        rows.append({
            'heure':      rng.integers(7, 22),
            'ip_score':   rng.choice([0.0, 0.1], p=[0.85, 0.15]),
            'tentatives': rng.integers(0, 2),
            'label':      0
        })

    # ── Cas ambigus normaux (300) ─────────────────────────────────

    # Travailleurs de nuit (normal mais heure tardive)
    for _ in range(80):
        rows.append({
            'heure':      rng.choice([0, 1, 2, 3, 22, 23]),
            'ip_score':   rng.choice([0.0, 0.1], p=[0.80, 0.20]),
            'tentatives': rng.integers(0, 2),
            'label':      0
        })

    # Utilisateurs en déplacement / VPN (nouvelle IP mais peu d'échecs)
    for _ in range(100):
        rows.append({
            'heure':      rng.integers(8, 20),
            'ip_score':   rng.choice([0.7, 0.8, 0.9]),
            'tentatives': rng.integers(0, 2),
            'label':      0
        })

    # Mot de passe oublié (plusieurs échecs mais heure et IP normales)
    for _ in range(80):
        rows.append({
            'heure':      rng.integers(8, 19),
            'ip_score':   rng.choice([0.0, 0.1], p=[0.85, 0.15]),
            'tentatives': rng.integers(3, 6),
            'label':      0
        })

    # Nouvelle IP + heure normale (premier accès depuis un nouvel appareil)
    for _ in range(40):
        rows.append({
            'heure':      rng.integers(9, 18),
            'ip_score':   1.0,
            'tentatives': rng.integers(0, 2),
            'label':      0
        })

    # ── Connexions suspectes classiques (30) ─────────────────────
    for _ in range(30):
        rows.append({
            'heure':      rng.choice([1, 2, 3, 4]),
            'ip_score':   1.0,
            'tentatives': rng.integers(7, 10),
            'label':      1
        })

    # ── Cas ambigus suspects (20) ─────────────────────────────────

    # Attaque en journée (IP inconnue + beaucoup d'échecs)
    for _ in range(10):
        rows.append({
            'heure':      rng.integers(9, 18),
            'ip_score':   rng.choice([0.8, 1.0]),
            'tentatives': rng.integers(6, 10),
            'label':      1
        })

    # Attaque furtive (heure normale + IP suspecte + échecs modérés)
    for _ in range(10):
        rows.append({
            'heure':      rng.integers(10, 20),
            'ip_score':   rng.choice([0.8, 0.9]),
            'tentatives': rng.integers(4, 7),
            'label':      1
        })

    df = pd.DataFrame(rows)
    df['label'] = df['label'].astype(int)

    # Mélanger les lignes
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    return df


# ──────────────────────────────────────────────
# 2. Entraînement + évaluation — US-26
# ──────────────────────────────────────────────
def train(output_path: str = MODEL_PATH) -> None:

    # ── Génération & sauvegarde CSV ──────────
    df = generate_dataset()
    df.to_csv(DATA_PATH, index=False)
    print(f'[DATA] Dataset sauvegarde → {DATA_PATH}')
    print(f'[DATA] Total : {len(df)} lignes  '
          f'| Normales : {(df.label==0).sum()}  '
          f'| Suspectes : {(df.label==1).sum()}')

    X = df[['heure', 'ip_score', 'tentatives']].values
    y = df['label'].values

    # ── Split 80 % train / 20 % test ─────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )
    print(f'\n[SPLIT] Train : {len(X_train)} echantillons'
          f'  (normaux={int((y_train==0).sum())}  suspects={int((y_train==1).sum())})')
    print(f'[SPLIT] Test  : {len(X_test)} echantillons'
          f'  (normaux={int((y_test==0).sum())}  suspects={int((y_test==1).sum())})')

    # ── Entraînement sur X_train uniquement ──
    contamination = round((y_train == 1).sum() / len(y_train), 4)
    clf = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        max_samples='auto',
        random_state=42,
    )
    clf.fit(X_train)

    # ── Évaluation sur X_test ─────────────────
    y_pred_raw = clf.predict(X_test)
    y_pred     = (y_pred_raw == -1).astype(int)
    scores     = clf.score_samples(X_test)

    print('\n[EVAL] Matrice de confusion (test set) :')
    cm = confusion_matrix(y_test, y_pred)
    print(f'         Predit Normal  Predit Suspect')
    print(f'  Reel Normal   {cm[0][0]:>5}          {cm[0][1]:>5}')
    print(f'  Reel Suspect  {cm[1][0]:>5}          {cm[1][1]:>5}')

    print('\n[EVAL] Rapport de classification :')
    print(classification_report(y_test, y_pred,
                                target_names=['Normal', 'Suspect']))

    tp = cm[1][1]
    fn = cm[1][0]
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    print(f'[EVAL] Recall suspects (detection) : {recall:.1%}')
    print(f'[EVAL] Scores test  min={scores.min():.4f}  '
          f'max={scores.max():.4f}  moy={scores.mean():.4f}')

    # ── Sauvegarde modèle ─────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        pickle.dump(clf, f)
    print(f'\n[IA] Modele sauvegarde → {output_path}')


if __name__ == '__main__':
    train()
