"""
ia/scorer.py — US-27 : Scoring temps réel
Chargement unique du modèle en mémoire au démarrage (BNF-05 : < 500 ms).
"""
import os
import pickle
import numpy as np
from datetime import datetime, timezone, timedelta

_model = None


def _load_model(path: str):
    global _model
    if os.path.exists(path):
        with open(path, 'rb') as f:
            _model = pickle.load(f)
    return _model


def get_model(path: str):
    """Retourne le modèle, le charge si besoin (lazy-loading)."""
    global _model
    if _model is None:
        _load_model(path)
    return _model


def classify_threat(hour: int, ip_score: float, failed: int) -> str:
    """
    Détermine le type de menace.
    ip_score : CONFIANCE (0.0=suspect, 1.0=confiance)
    """
    if failed >= 5:
        return 'ATTAQUE_BRUTE_FORCE'
    if ip_score < 0.3:
        return 'IP_SUSPECTE'
    if hour < 6 or hour > 22:
        return 'HEURE_ANORMALE'
    return 'COMPORTEMENT_ANORMAL'


def score(user_id: int, ip: str, model_path: str, threshold: float, Log) -> tuple:
    """
    Retourne (score: float, is_anomaly: bool, threat_type: str | None).

    RÈGLES DE BLOCAGE :
      - brute_force : failed_count >= 5, QUELLE QUE SOIT l'IP
      - ia_anomaly  : score IA < seuil ET IP inconnue/suspecte
    """
    clf = get_model(model_path)
    if clf is None:
        print("[IA] Modèle non chargé, scoring désactivé")
        return 0.0, False, None

    hour = datetime.now().hour

    # Score de confiance IP
    successful_logs = Log.query.filter_by(user_id=user_id, login_success=True).all()

    if not successful_logs:
        failed_already = Log.query.filter(
            Log.user_id == user_id,
            Log.login_success == False,
        ).count()
        ip_score = 0.0 if failed_already > 0 else 0.5
    else:
        ip_usage_count = sum(1 for l in successful_logs if l.ip_address == ip)
        ip_score       = min(ip_usage_count / max(len(successful_logs), 1), 1.0)

    # Tentatives échouées sur 24h
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    failed_count = Log.query.filter(
        Log.user_id       == user_id,
        Log.login_success == False,
        Log.timestamp     >= since
    ).count()
    failed_count = min(failed_count, 10)

    # Score IA
    features  = np.array([[hour, ip_score, failed_count]])
    raw_score = float(clf.score_samples(features)[0])

    # Décision : brute force = blocage peu importe l'IP
    ia_anomaly  = raw_score < threshold and ip_score < 0.5
    brute_force = failed_count >= 5
    is_anomaly  = ia_anomaly or brute_force

    threat_type = classify_threat(hour, ip_score, failed_count) if is_anomaly else None

    print(f"\n{'='*60}")
    print(f"[IA SCORING] User #{user_id} | IP: {ip}")
    print(f"  • Heure: {hour}h | IP Score: {ip_score:.3f} | Échecs 24h: {failed_count}")
    print(f"  • Score brut: {raw_score:.4f} | Seuil: {threshold}")
    print(f"  • Anomalie: {'OUI - ' + str(threat_type) if is_anomaly else 'NON'}")
    print(f"{'='*60}\n")

    return raw_score, is_anomaly, threat_type
