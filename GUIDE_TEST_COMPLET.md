# 🎯 GUIDE DE TEST COMPLET — Système de Détection d'Anomalies

## ✅ ÉTAPE 1 : Réinitialiser la base de données

```bash
cd "D:\download\auth_platform (2)\auth_platform"
python reset_database.py
```

**Résultat attendu** :
```
✅ RÉINITIALISATION TERMINÉE !

📋 COMPTES CRÉÉS :
   🔑 ADMIN :
      Email    : admin@authplatform.com
      Password : Admin123!

   👤 USER :
      Email    : arroubihayate@gmail.com
      Password : Test123!
```

---

## ✅ ÉTAPE 2 : Démarrer Flask

```bash
python app.py
```

**Attendre** :
```
* Running on http://127.0.0.1:5000
```

---

## 🧪 TEST 1 : Connexion normale (0 échecs)

### 1.1 Se connecter

**Dans le navigateur** :
- Aller sur `http://localhost:5000/auth/login`
- Email : `arroubihayate@gmail.com`
- Password : `Test123!`

**Résultat attendu** :
- ✅ Connexion réussie
- Dashboard affiché

**Dans les logs Flask** :
```
[IA SCORING] User #2 | IP: 127.0.0.1
  • Échecs 24h    : 0
  • Score brut    : -0.5XXX
  • Seuil         : -0.62
  • Anomalie ?    : ✅ NON
```

---

## 🧪 TEST 2 : Blocage après 3 tentatives échouées

### 2.1 Se déconnecter

**Dans le navigateur** :
- Cliquer sur "Se déconnecter"
- **OU** aller sur `http://localhost:5000/auth/logout`

### 2.2 Créer 3 échecs

```bash
flask shell
```

```python
from models import User, Log

user = User.query.filter_by(email='arroubihayate@gmail.com').first()

# Créer 3 échecs
for i in range(3):
    Log.create(
        user_id=user.id,
        email_tried=user.email,
        ip='127.0.0.1',
        browser='Chrome',
        os_name='Windows',
        location='N/A',
        success=False
    )

db.session.commit()

print("✅ 3 échecs créés")
print("👉 Se connecter avec arroubihayate@gmail.com / Test123!")

exit()
```

### 2.3 Se connecter avec le BON mot de passe

**Dans le navigateur** :
- Email : `arroubihayate@gmail.com`
- Password : `Test123!` (BON mot de passe)

**Résultat attendu** :
- 🚨 Page "Compte temporairement bloqué"
- 📧 2 emails reçus (admin + utilisateur)

**Dans les logs Flask** :
```
[IA SCORING] User #2 | IP: 127.0.0.1
  • Échecs 24h    : 3
  • Score brut    : -0.6XXX
  • Seuil         : -0.62
  • Anomalie ?    : 🚨 OUI
  • Type menace   : MULTIPLES_TENTATIVES

[MAIL] Alerte admin envoyee a arroubihayate@gmail.com
[DEBLOCAGE] Lien : http://127.0.0.1:5000/auth/unlock/...
[MAIL] Email deblocage envoye a arroubihayate@gmail.com
```

---

## 🧪 TEST 3 : Déblocage via lien email

### 3.1 Copier le lien

**Dans les logs Flask**, copier :
```
[DEBLOCAGE] Lien : http://127.0.0.1:5000/auth/unlock/...
```

### 3.2 Cliquer sur le lien

**Coller dans le navigateur** et **Entrée**.

**Résultat attendu** :
- ✅ Message "Votre compte a été débloqué. Vous pouvez vous reconnecter."
- ✅ Redirection vers la page de login

### 3.3 Se reconnecter

**Se connecter avec** :
- Email : `arroubihayate@gmail.com`
- Password : `Test123!`

**Résultat attendu** :
- ✅ Connexion réussie
- ✅ Pas de re-blocage (les échecs ont été supprimés automatiquement)

---

## 🧪 TEST 4 : Déblocage admin

### 4.1 Créer 3 échecs et bloquer le compte

```bash
flask shell
```

```python
from models import User, Log

user = User.query.filter_by(email='arroubihayate@gmail.com').first()

# Nettoyer d'abord
Log.query.filter_by(user_id=user.id, login_success=False).delete()
user.is_blocked = False
db.session.commit()

# Créer 3 échecs
for i in range(3):
    Log.create(
        user_id=user.id,
        email_tried=user.email,
        ip='127.0.0.1',
        browser='Chrome',
        os_name='Windows',
        location='N/A',
        success=False
    )

db.session.commit()

exit()
```

**Se connecter** avec `arroubihayate@gmail.com` / `Test123!` → Compte bloqué

### 4.2 Se connecter en tant qu'admin

**Dans le navigateur** :
- Aller sur `http://localhost:5000/auth/login`
- Email : `admin@authplatform.com`
- Password : `Admin123!`

### 4.3 Débloquer le compte

**Dans le dashboard admin** :
1. Cliquer sur "Utilisateurs"
2. Trouver `arroubihayate@gmail.com`
3. Cliquer sur "Débloquer"

**Résultat attendu** :
- ✅ Message "Compte débloqué avec succès. 1 alerte(s) résolue(s)."

### 4.4 Tester la reconnexion

**Se déconnecter** (admin) et **se reconnecter** avec :
- Email : `arroubihayate@gmail.com`
- Password : `Test123!`

**Résultat attendu** :
- ✅ Connexion réussie
- ✅ Pas de re-blocage

---

## 📊 CONFIGURATION ACTUELLE

```python
# config.py ligne 34
ANOMALY_THRESHOLD = -0.62  # Bloque après 3-4 tentatives échouées
```

**Comportement** :
- 0-2 échecs → ✅ Connexion autorisée
- 3-4 échecs → 🚨 Compte bloqué
- 5+ échecs → 🚨 Compte bloqué (garanti)

---

## 🔧 DÉPANNAGE

### Problème 1 : Le compte se re-bloque après déblocage

**Cause** : Les logs d'échecs sont toujours en base

**Solution** : Les corrections appliquées suppriment automatiquement les échecs lors du déblocage

### Problème 2 : Pas d'email reçu

**Cause** : Configuration `.env` incorrecte

**Solution** :
```bash
notepad .env
```

Vérifier :
```env
MAIL_USERNAME=arroubihayate@gmail.com
MAIL_PASSWORD=[mot_passe_application_16_caractères]
ADMIN_EMAIL=arroubihayate@gmail.com
```

### Problème 3 : Le lien ne fonctionne pas

**Cause** : Token expiré (> 30 minutes)

**Solution** : Débloquer manuellement
```bash
flask shell
```

```python
from models import User, Log

user = User.query.filter_by(email='arroubihayate@gmail.com').first()
user.is_blocked = False
Log.query.filter_by(user_id=user.id, login_success=False).delete()
db.session.commit()

exit()
```

---

## ✅ CHECKLIST COMPLÈTE

```
□ Réinitialiser la base (python reset_database.py)
□ Démarrer Flask (python app.py)
□ TEST 1 : Connexion normale (0 échecs) → ✅ OK
□ TEST 2 : Blocage après 3 échecs → 🚨 Bloqué
□ TEST 3 : Déblocage via lien email → ✅ Débloqué
□ TEST 3bis : Reconnexion après déblocage → ✅ OK
□ TEST 4 : Déblocage admin → ✅ Débloqué
□ Vérifier les emails reçus → 📧 2 emails
```

---

## 🎯 RÉSULTAT FINAL

✅ Système 100% fonctionnel avec :
- Détection d'anomalies après 3-4 échecs
- Blocage automatique
- Emails d'alerte (admin + utilisateur)
- Déblocage via lien email (avec suppression auto des échecs)
- Déblocage admin (avec suppression auto des échecs)
- Pas de re-blocage après déblocage
