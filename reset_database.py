"""
Script de réinitialisation complète de la base de données
Usage : python reset_database.py
"""
import os
from app import create_app
from extensions import db, bcrypt
from models import User, UserRole

def reset_database():
    """Réinitialise complètement la base de données"""
    
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("RÉINITIALISATION DE LA BASE DE DONNÉES")
        print("="*60 + "\n")
        
        # 1. Supprimer toutes les tables
        print("1. Suppression des tables existantes...")
        db.drop_all()
        print("   ✅ Tables supprimées")
        
        # 2. Recréer toutes les tables
        print("\n2. Création des nouvelles tables...")
        db.create_all()
        print("   ✅ Tables créées")
        
        # 3. Créer les utilisateurs par défaut
        print("\n3. Création des utilisateurs...")
        
        # Admin — mot de passe identique à _seed_admin() dans app.py
        admin = User()
        admin.register(bcrypt, 'admin@authplatform.com', 'Administrateur', 'Admin@1234!')
        admin.role = UserRole.ADMIN
        db.session.add(admin)
        print("   ✅ Admin créé")

        # User principal
        user = User()
        user.register(bcrypt, 'arroubihayate@gmail.com', 'Hayat', 'Test@1234!')
        db.session.add(user)
        print("   ✅ Utilisateur créé")
        
        db.session.commit()
        
        # 4. Résumé
        print("\n" + "="*60)
        print("✅ RÉINITIALISATION TERMINÉE !")
        print("="*60)
        print("\n📋 COMPTES CRÉÉS :\n")
        print("   🔑 ADMIN :")
        print("      Email    : admin@authplatform.com")
        print("      Password : Admin@1234!")
        print("\n   👤 USER :")
        print("      Email    : arroubihayate@gmail.com")
        print("      Password : Test@1234!")
        print("\n" + "="*60)
        print("🚀 Vous pouvez maintenant démarrer Flask avec : python app.py")
        print("="*60 + "\n")

if __name__ == '__main__':
    reset_database()