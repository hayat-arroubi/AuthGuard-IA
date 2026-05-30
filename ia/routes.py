"""
ia/routes.py — US-27 (endpoint /predict) + US-37 (3 scénarios de test)
"""
import numpy as np
from flask import request, jsonify, current_app

from ia import ia_bp
from ia.scorer import score as ia_score, get_model, classify_threat


@ia_bp.route('/predict', methods=['POST'])
def predict():
    """
    US-27 : Scoring JSON d'une tentative de connexion.
    Body JSON : { "user_id": int, "ip": str }
    """
    data       = request.get_json(force=True) or {}
    user_id    = data.get('user_id')
    ip         = data.get('ip', '127.0.0.1')
    model_path = current_app.config.get('MODEL_PATH', '')
    threshold  = current_app.config.get('ANOMALY_THRESHOLD', -0.5)

    from models import Log
    raw, anomaly, threat = ia_score(user_id, ip, model_path, threshold, Log)

    return jsonify({
        'score':      round(raw, 4),
        'is_anomaly': anomaly,
        'threat':     threat,
    })


@ia_bp.route('/test')
def test_scenarios():
    """
    US-37 : Validation du modèle sur 3 scénarios simulés.
    Scénario 1 — connexion normale (bureau, IP connue, 0 échec)
    Scénario 2 — IP suspecte la nuit (3h, IP inconnue, 1 échec)
    Scénario 3 — attaque brute-force (2h, IP inconnue, 10 échecs)
    """
    model_path = current_app.config.get('MODEL_PATH', '')
    threshold  = current_app.config.get('ANOMALY_THRESHOLD', -0.5)

    clf = get_model(model_path)
    if clf is None:
        return jsonify({'error': 'Modele absent. Lancez : python ia/train.py'}), 503

    scenarios = [
        {'name': 'Connexion normale',  'desc': '9h, IP connue, 0 echec',          'features': [9,  0.0,  0]},
        {'name': 'IP suspecte (nuit)', 'desc': '3h, IP inconnue, 1 echec',         'features': [3,  1.0,  1]},
        {'name': 'Brute-force',        'desc': '2h, IP inconnue, 10 echecs',        'features': [2,  1.0, 10]},
    ]

    results = []
    for s in scenarios:
        feat  = np.array([s['features']])
        sc    = float(clf.score_samples(feat)[0])
        h, ip_sc, failed = s['features']
        threat = classify_threat(h, ip_sc, failed) if sc < threshold else None
        results.append({
            'scenario':    s['name'],
            'description': s['desc'],
            'features': {'heure': h, 'ip_score': ip_sc, 'tentatives': failed},
            'score':      round(sc, 4),
            'threshold':  threshold,
            'is_anomaly': sc < threshold,
            'threat':     threat,
            'verdict':    'ANOMALIE' if sc < threshold else 'NORMAL',
        })

    return jsonify({'model_path': model_path, 'scenarios': results})
