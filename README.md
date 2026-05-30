# AuthGuard IA — Sprint 2
**Plateforme d'authentification intelligente avec détection d'anomalies par IA**

---

## Structure du projet (BNF-09 — Blueprints Flask)

```
auth_platform/
├── app.py                  # Factory Flask + seed admin
├── config.py               # DevelopmentConfig / ProductionConfig
├── extensions.py           # db, bcrypt, mail (évite imports circulaires)
├── models.py               # User, Authentification, Session, Log, Alerte
├── requirements.txt
├── .env.example
│
├── auth/                   # Blueprint : login, register, logout, profil
│   ├── __init__.py
│   └── routes.py
├── admin/                  # Blueprint : dashboard, logs, alertes, users
│   ├── __init__.py
│   └── routes.py
├── logs/                   # Blueprint Sprint 3 (geoip2, sessions actives)
│   └── __init__.py
├── ia/                     # Blueprint Sprint 4 (Isolation Forest, /predict)
│   └── __init__.py
│
└── templates/
    ├── base.html
    ├── auth/
    │   ├── base_auth.html
    │   ├── login.html      # BF-02 : Connexion + JWT
    │   ├── register.html   # BF-01 : Inscription + bcrypt
    │   └── blocked.html    # BF-09 : Compte bloqué
    ├── admin/
    │   ├── dashboard.html  # Chart.js : barres + donut
    │   ├── logs.html       # BF-07 : Filtres date/user/IP
    │   ├── alertes.html    # BF-11 : Statuts + actions
    │   └── users.html      # BF-04/12 : Rôles + blocage
    └── user/
        ├── dashboard.html  # Tableau de bord utilisateur
        └── profile.html    # BF-05 : Modifier profil + MDP
```

---

## Installation & lancement

### 1. Cloner et créer l'environnement virtuel
```bash
git clone <votre-repo>
cd auth_platform
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement
```bash
cp .env.example .env
# Éditez .env avec vos valeurs (SECRET_KEY, JWT_SECRET_KEY, mail...)
```

### 4. Lancer l'application
```bash
python app.py
```

L'application démarre sur **http://localhost:5000**

### Compte admin par défaut (créé automatiquement)
- **Email** : `admin@authplatform.com`
- **Mot de passe** : `Admin@1234!`
- ⚠️ Changez ce mot de passe immédiatement après la première connexion !

---

## Besoins fonctionnels couverts (Sprint 2)

| ID | Description | Statut |
|----|-------------|--------|
| BF-01 | Inscription avec bcrypt (coût 12) | ✅ |
| BF-02 | Connexion + token JWT (1h) | ✅ |
| BF-03 | Déconnexion + invalidation JWT | ✅ |
| BF-04 | Rôles Admin/Utilisateur + décorateurs | ✅ |
| BF-05 | Modifier profil + changer MDP | ✅ |
| BF-06 | Log connexion (IP, browser, OS) | ✅ |
| BF-07 | Historique admin avec filtres | ✅ |
| BF-08 | Scoring IA stub (prêt Sprint 4) | ✅ |
| BF-09 | Blocage automatique si anomalie | ✅ |
| BF-11 | Alertes avec statuts | ✅ |
| BF-12 | Déblocage manuel admin (tracé) | ✅ |

## Besoins non-fonctionnels couverts

| ID | Description | Statut |
|----|-------------|--------|
| BNF-01 | bcrypt coût 12 | ✅ |
| BNF-02 | JWT HttpOnly cookie, expire 1h | ✅ |
| BNF-04 | SQLAlchemy paramétré (anti-injection) | ✅ |
| BNF-09 | Blueprints Flask modulaires | ✅ |

---

## Sprints suivants

- **Sprint 3** : `logs/routes.py` — geoip2, sessions actives, signalement
- **Sprint 4** : `ia/routes.py` — Isolation Forest, model.pkl, emails alertes
- **Sprint 6** : Migration SQLite → OCI Autonomous Database
