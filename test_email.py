from app import app, mail
from flask_mail import Message

with app.app_context():
    try:
        print("🔄 Envoi d'un email de test...")
        
        msg = Message(
            subject='Test AuthPlatform',
            recipients=['arroubihayate@gmail.com'],
            body='Ceci est un email de test. Si tu reçois cet email, la configuration fonctionne !'
        )
        
        mail.send(msg)
        
        print("✅ EMAIL ENVOYÉ AVEC SUCCÈS !")
        print("📬 Vérifie ta boîte de réception : arroubihayate@gmail.com")
        print("⚠️  Vérifie aussi les SPAMS si tu ne le vois pas")
        
    except Exception as e:
        print(f"❌ ERREUR : {e}")