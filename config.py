import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ─── Sécurité ───────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod-12345')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-prod-12345')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_COOKIE_SECURE = False          # True en production (HTTPS)
    JWT_COOKIE_CSRF_PROTECT = True
    BCRYPT_LOG_ROUNDS = 12             # BNF-01 : coût minimum 12

    # ─── Base de données ────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///auth_platform.db'   # US-08 : SQLite en dev
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ─── Mail ───────────────────────────────────────────────────
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@authplatform.com')

    # ─── IA ─────────────────────────────────────────────────────
    ANOMALY_THRESHOLD = -0.62  # Bloque après 3-4 tentatives échouées
    MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ia', 'model.pkl')
    UNLOCK_TOKEN_EXPIRES = timedelta(minutes=30)

    # ─── App ────────────────────────────────────────────────────
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@authplatform.com')
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')


class DevelopmentConfig(Config):
    DEBUG = True
    JWT_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    JWT_COOKIE_SECURE = True           # HTTPS obligatoire en prod
    SQLALCHEMY_DATABASE_URI = os.environ.get('OCI_DB_URL', Config.SQLALCHEMY_DATABASE_URI)


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
