"""
diagnostic.py — Script de diagnostic complet du système
Vérifie que tous les composants fonctionnent correctement
"""
import os
import sys

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database():
    """Test 1 : Connexion à la BDD"""
    print("\n" + "="*60)
    print("TEST 1 : Base de données")
    print("="*60)
    
    try:
        from app import app, db
        from models import User, Log, Alerte
        
        with app.app_context():
            # Compter les utilisateurs
            user_count = User.query.count()
            log_count = Log.query.count()
            alert_count = Alerte.query.count()
            
            print(f"✅ Connexion BDD réussie")
            print(f"   - Utilisateurs : {user_count}")
            print(f"   - Logs         : {log_count}")
            print(f"   - Alertes      : {alert_count}")
            
            # Vérifier les utilisateurs bloqués
            blocked = User.query.filter_by(is_blocked=True).all()
            if blocked:
                print(f"\n⚠️  Utilisateurs bloqués : {len(blocked)}")
                for u in blocked:
                    print(f"     - {u.email}")
            else:
                print(f"✅ Aucun utilisateur bloqué")
                
            return True
            
    except Exception as e:
        print(f"❌ ERREUR BDD : {e}")
        return False


def test_model_loading():
    """Test 2 : Chargement du modèle IA"""
    print("\n" + "="*60)
    print("TEST 2 : Modèle IA (Isolation Forest)")
    print("="*60)
    
    try:
        from app import app
        from ia.scorer import get_model
        
        model_path = app.config.get('MODEL_PATH', 'ia/model.pkl')
        
        # Vérifier que le fichier existe
        if not os.path.exists(model_path):
            print(f"❌ Fichier modèle introuvable : {model_path}")
            return False
        
        # Charger le modèle
        model = get_model(model_path)
        
        if model is None:
            print(f"❌ Modèle chargé = None")
            return False
        
        print(f"✅ Modèle chargé avec succès")
        print(f"   - Type   : {type(model)}")
        print(f"   - Fichier : {model_path}")
        print(f"   - Taille  : {os.path.getsize(model_path) / 1024:.1f} KB")
        
        # Test de scoring
        import numpy as np
        test_features = np.array([[14, 0.9, 0]])  # Normal
        score = float(model.score_samples(test_features)[0])
        print(f"\n✅ Test scoring normal : {score:.4f}")
        
        test_features = np.array([[3, 0.1, 8]])  # Suspect
        score = float(model.score_samples(test_features)[0])
        print(f"✅ Test scoring suspect : {score:.4f}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR Modèle : {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scoring_logic():
    """Test 3 : Logique de scoring complète"""
    print("\n" + "="*60)
    print("TEST 3 : Logique de scoring IA")
    print("="*60)
    
    try:
        from app import app, db
        from models import User, Log
        from ia.scorer import score
        
        with app.app_context():
            # Prendre le premier utilisateur
            user = User.query.first()
            if not user:
                print("❌ Aucun utilisateur en BDD")
                return False
            
            print(f"👤 Test avec utilisateur : {user.email}")
            
            # Test 1 : IP connue, heure normale, pas d'échecs
            print("\n📊 Test 1 : Connexion normale")
            result = score(
                user_id=user.id,
                ip='192.168.1.1',
                model_path=app.config['MODEL_PATH'],
                threshold=app.config['ANOMALY_THRESHOLD'],
                Log=Log
            )
            print(f"   Score    : {result[0]:.4f}")
            print(f"   Anomalie : {result[1]}")
            print(f"   Type     : {result[2]}")
            
            # Test 2 : IP inconnue, heure suspecte, échecs
            print("\n📊 Test 2 : Connexion suspecte")
            result = score(
                user_id=user.id,
                ip='203.0.113.42',  # IP jamais vue
                model_path=app.config['MODEL_PATH'],
                threshold=app.config['ANOMALY_THRESHOLD'],
                Log=Log
            )
            print(f"   Score    : {result[0]:.4f}")
            print(f"   Anomalie : {result[1]}")
            print(f"   Type     : {result[2]}")
            
            if result[1]:
                print("✅ Détection d'anomalie fonctionnelle")
            else:
                print("⚠️  Anomalie non détectée (possible si pas assez de logs)")
            
            return True
            
    except Exception as e:
        print(f"❌ ERREUR Scoring : {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_config():
    """Test 4 : Configuration email"""
    print("\n" + "="*60)
    print("TEST 4 : Configuration Email")
    print("="*60)
    
    try:
        from app import app
        
        mail_user = app.config.get('MAIL_USERNAME', '')
        mail_pass = app.config.get('MAIL_PASSWORD', '')
        admin_email = app.config.get('ADMIN_EMAIL', '')
        
        if not mail_user:
            print("⚠️  MAIL_USERNAME non configuré")
            print("   → Les emails ne seront PAS envoyés")
            print("   → Les liens de déblocage s'afficheront dans la console")
        else:
            print(f"✅ MAIL_USERNAME  : {mail_user}")
            print(f"✅ MAIL_PASSWORD  : {'***' if mail_pass else '❌ VIDE'}")
            print(f"✅ ADMIN_EMAIL    : {admin_email}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR Config : {e}")
        return False


def test_alertes_system():
    """Test 5 : Système d'alertes"""
    print("\n" + "="*60)
    print("TEST 5 : Système d'alertes")
    print("="*60)
    
    try:
        from app import app, db
        from models import Alerte, AlerteStatus, User
        
        with app.app_context():
            # Compter les alertes par statut
            en_cours = Alerte.query.filter_by(status=AlerteStatus.EN_COURS).count()
            resolu = Alerte.query.filter_by(status=AlerteStatus.RESOLU).count()
            ignore = Alerte.query.filter_by(status=AlerteStatus.IGNORE).count()
            
            print(f"📊 Alertes par statut :")
            print(f"   - En cours : {en_cours}")
            print(f"   - Résolues : {resolu}")
            print(f"   - Ignorées : {ignore}")
            
            # Vérifier les utilisateurs avec alertes ouvertes
            if en_cours > 0:
                alertes_ouvertes = Alerte.query.filter_by(
                    status=AlerteStatus.EN_COURS
                ).all()
                
                print(f"\n⚠️  {en_cours} alerte(s) en cours :")
                for alerte in alertes_ouvertes[:5]:  # Max 5
                    user = User.query.get(alerte.user_id)
                    print(f"     - #{alerte.id} | {user.email if user else 'N/A'} | {alerte.type}")
            else:
                print("✅ Aucune alerte en cours")
            
            return True
            
    except Exception as e:
        print(f"❌ ERREUR Alertes : {e}")
        return False


def test_admin_functions():
    """Test 6 : Fonctions admin"""
    print("\n" + "="*60)
    print("TEST 6 : Fonctions administrateur")
    print("="*60)
    
    try:
        from app import app, db
        from models import User, UserRole
        
        with app.app_context():
            # Vérifier qu'il y a un admin
            admin = User.query.filter_by(role=UserRole.ADMIN).first()
            
            if not admin:
                print("⚠️  Aucun compte administrateur trouvé")
                print("\n💡 Pour créer un admin :")
                print("   flask shell")
                print("   >>> from models import User, UserRole")
                print("   >>> user = User.query.filter_by(email='votre@email.com').first()")
                print("   >>> user.role = UserRole.ADMIN")
                print("   >>> db.session.commit()")
                return False
            
            print(f"✅ Administrateur trouvé : {admin.email}")
            
            # Vérifier les utilisateurs bloqués
            blocked = User.query.filter_by(is_blocked=True).all()
            if blocked:
                print(f"\n📋 Utilisateurs à débloquer :")
                for u in blocked:
                    alertes = Alerte.query.filter_by(
                        user_id=u.id,
                        status=AlerteStatus.EN_COURS
                    ).count()
                    print(f"   - {u.email} ({alertes} alerte(s) ouvertes)")
            
            return True
            
    except Exception as e:
        print(f"❌ ERREUR Admin : {e}")
        return False


def main():
    """Exécuter tous les tests"""
    print("\n" + "🔍 DIAGNOSTIC COMPLET DU SYSTÈME")
    print("="*60)
    
    results = {
        'BDD': test_database(),
        'Modèle IA': test_model_loading(),
        'Scoring': test_scoring_logic(),
        'Email': test_email_config(),
        'Alertes': test_alertes_system(),
        'Admin': test_admin_functions(),
    }
    
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ OK" if result else "❌ ÉCHEC"
        print(f"{status:8} | {test_name}")
    
    total_ok = sum(results.values())
    total_tests = len(results)
    
    print(f"\n🎯 Score : {total_ok}/{total_tests} tests réussis")
    
    if total_ok == total_tests:
        print("\n✅ LE SYSTÈME EST OPÉRATIONNEL !")
    else:
        print("\n⚠️  DES CORRECTIONS SONT NÉCESSAIRES")
        print("\n📖 Consultez GUIDE_CORRECTION_COMPLETE.md pour les solutions")


if __name__ == '__main__':
    main()
