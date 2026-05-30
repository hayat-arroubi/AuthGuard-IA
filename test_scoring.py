"""Test direct du scoring IA"""
from app import app, db
from models import User, Log
from ia.scorer import score

with app.app_context():
    # Trouver l'utilisateur
    user = User.query.filter_by(email='testuser@example.com').first()
    
    if not user:
        print("❌ Utilisateur introuvable")
    else:
        print(f"✅ Test pour {user.email}")
        print(f"   Rôle : {user.role.value}")
        print(f"   ID   : {user.id}")
        
        # APPEL DIRECT DU SCORING
        print("\n🔥 APPEL DU SCORING...")
        result = score(
            user_id=user.id,
            ip='127.0.0.1',
            model_path='ia/model.pkl',
            threshold=-0.85,
            Log=Log
        )
        
        print(f"\n📊 RÉSULTAT :")
        print(f"   Score      : {result[0]:.4f}")
        print(f"   Anomalie ? : {result[1]}")
        print(f"   Type       : {result[2]}")