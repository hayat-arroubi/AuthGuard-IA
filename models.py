"""
models.py — Tâche 4 : Diagramme de classes
5 classes : User, Authentification, Session, Log, Alerte
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum
from extensions import db


# ═══════════════════════════════════════════════════════════════
# CLASSE USER
# ═══════════════════════════════════════════════════════════════
class UserRole(PyEnum):
    USER = 'user'
    ADMIN = 'admin'


class User(db.Model):
    __tablename__ = 'users'

    # ── Attributs ──────────────────────────────────────────────
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    is_blocked    = db.Column(db.Boolean, default=False, nullable=False)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # ── Relations ──────────────────────────────────────────────
    authentifications = db.relationship('Authentification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    sessions          = db.relationship('Session',          backref='user', lazy='dynamic', cascade='all, delete-orphan')
    logs              = db.relationship('Log',              backref='user', lazy='dynamic', cascade='all, delete-orphan')
    alertes           = db.relationship('Alerte',           backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # ── Méthodes ───────────────────────────────────────────────
    def register(self, bcrypt, email: str, username: str, password: str) -> None:
        """BF-01 : Inscription avec bcrypt (BNF-01)"""
        self.email         = email
        self.username      = username
        self.password_hash = bcrypt.generate_password_hash(password, rounds=12).decode('utf-8')

    def check_password(self, bcrypt, password: str) -> bool:
        """BF-02 : Vérification du mot de passe"""
        return bcrypt.check_password_hash(self.password_hash, password)

    def update_profile(self, username: str = None, email: str = None) -> None:
        """BF-05 : Modifier le profil"""
        if username:
            self.username = username
        if email:
            self.email = email

    def block(self) -> None:
        """BF-09 : Blocage automatique"""
        self.is_blocked = True

    def unblock(self) -> None:
        """BF-12 : Déblocage manuel par admin"""
        self.is_blocked = False

    def to_dict(self) -> dict:
        return {
            'id':         self.id,
            'username':   self.username,
            'email':      self.email,
            'role':       self.role.value,
            'is_blocked': self.is_blocked,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<User {self.email} [{self.role.value}]>'


# ═══════════════════════════════════════════════════════════════
# CLASSE AUTHENTIFICATION
# ═══════════════════════════════════════════════════════════════
class Authentification(db.Model):
    __tablename__ = 'authentifications'

    # ── Attributs ──────────────────────────────────────────────
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token_type  = db.Column(db.String(20), default='JWT')   # JWT ou UNLOCK
    token_value = db.Column(db.String(512), nullable=False)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at  = db.Column(db.DateTime, nullable=False)
    is_valid    = db.Column(db.Boolean, default=True)

    # ── Méthodes ───────────────────────────────────────────────
    def generate_token(self, jwt_manager, user_id: int, expires_delta) -> str:
        """BF-02 : Génération du token JWT"""
        import jwt
        from datetime import datetime, timezone
        payload = {
            'sub':  str(user_id),
            'iat':  datetime.now(timezone.utc),
            'exp':  datetime.now(timezone.utc) + expires_delta,
            'type': self.token_type,
        }
        return jwt.encode(payload, jwt_manager, algorithm='HS256')

    def verify_token(self) -> bool:
        """Vérification validité token"""
        return self.is_valid and datetime.now(timezone.utc) < self.expires_at.replace(tzinfo=timezone.utc)

    def revoke_token(self) -> None:
        """BF-03 : Révocation du token"""
        self.is_valid = False

    @staticmethod
    def hash_password(bcrypt, password: str) -> str:
        """BNF-01 : Hash bcrypt coût 12"""
        return bcrypt.generate_password_hash(password, rounds=12).decode('utf-8')


# ═══════════════════════════════════════════════════════════════
# CLASSE SESSION
# ═══════════════════════════════════════════════════════════════
class Session(db.Model):
    __tablename__ = 'sessions'

    # ── Attributs ──────────────────────────────────────────────
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token      = db.Column(db.String(512), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active  = db.Column(db.Boolean, default=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(256))

    # ── Méthodes ───────────────────────────────────────────────
    @classmethod
    def create(cls, user_id: int, token: str, expires_at, ip: str, ua: str) -> 'Session':
        s = cls(user_id=user_id, token=token, expires_at=expires_at,
                ip_address=ip, user_agent=ua)
        db.session.add(s)
        return s

    def invalidate(self) -> None:
        """BF-03 : Déconnexion"""
        self.is_active = False

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    @classmethod
    def invalidate_all(cls, user_id: int) -> None:
        """US-21 : Déconnecter tous les appareils"""
        cls.query.filter_by(user_id=user_id, is_active=True).update({'is_active': False})


# ═══════════════════════════════════════════════════════════════
# CLASSE LOG
# ═══════════════════════════════════════════════════════════════
class Log(db.Model):
    __tablename__ = 'logs'

    # ── Attributs ──────────────────────────────────────────────
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    email_tried   = db.Column(db.String(120))                   # si user inconnu
    ip_address    = db.Column(db.String(45))
    browser       = db.Column(db.String(100))
    os            = db.Column(db.String(100))
    location      = db.Column(db.String(200))
    timestamp     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    anomaly_score = db.Column(db.Float, default=0.0)
    is_anomaly    = db.Column(db.Boolean, default=False)
    login_success = db.Column(db.Boolean, default=False)
    failed_count  = db.Column(db.Integer, default=0)            # tentatives échouées

    # Relation 1-1 avec Alerte
    alerte = db.relationship('Alerte', backref='log', uselist=False, cascade='all, delete-orphan')

    # ── Méthodes ───────────────────────────────────────────────
    @classmethod
    def create(cls, user_id, email_tried, ip, browser, os_name, location,
               score=0.0, is_anomaly=False, success=False, failed=0) -> 'Log':
        """BF-06 : Enregistrement connexion"""
        log = cls(
            user_id       = user_id,
            email_tried   = email_tried,
            ip_address    = ip,
            browser       = browser,
            os            = os_name,
            location      = location,
            anomaly_score = score,
            is_anomaly    = is_anomaly,
            login_success = success,
            failed_count  = failed,
        )
        db.session.add(log)
        return log

    @classmethod
    def get_by_user(cls, user_id: int) -> list:
        return cls.query.filter_by(user_id=user_id).order_by(cls.timestamp.desc()).all()

    def flag_anomaly(self, score: float) -> None:
        """BF-08 : Marquer comme anomalie"""
        self.anomaly_score = score
        self.is_anomaly    = True

    def to_dict(self) -> dict:
        return {
            'id':            self.id,
            'user_id':       self.user_id,
            'email_tried':   self.email_tried,
            'ip_address':    self.ip_address,
            'browser':       self.browser,
            'os':            self.os,
            'location':      self.location,
            'timestamp':     self.timestamp.isoformat() if self.timestamp else None,
            'anomaly_score': round(self.anomaly_score, 4) if self.anomaly_score else 0,
            'is_anomaly':    self.is_anomaly,
            'login_success': self.login_success,
        }


# ═══════════════════════════════════════════════════════════════
# CLASSE ALERTE
# ═══════════════════════════════════════════════════════════════
class AlerteStatus(PyEnum):
    EN_COURS = 'en_cours'
    RESOLU   = 'resolu'
    IGNORE   = 'ignore'


class Alerte(db.Model):
    __tablename__ = 'alertes'

    # ── Attributs ──────────────────────────────────────────────
    id         = db.Column(db.Integer, primary_key=True)
    log_id     = db.Column(db.Integer, db.ForeignKey('logs.id'), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type       = db.Column(db.String(50))                        # IP_SUSPECTE, HEURE_ANORMALE, etc.
    message    = db.Column(db.Text)
    status     = db.Column(db.Enum(AlerteStatus), default=AlerteStatus.EN_COURS)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # ── Méthodes ───────────────────────────────────────────────
    @classmethod
    def create(cls, log_id: int, user_id: int, alert_type: str, message: str) -> 'Alerte':
        """BF-10 : Créer alerte"""
        a = cls(log_id=log_id, user_id=user_id, type=alert_type, message=message)
        db.session.add(a)
        return a

    def update_status(self, new_status: str) -> None:
        """BF-11 : Mettre à jour le statut"""
        self.status = AlerteStatus(new_status)

    def to_dict(self) -> dict:
        return {
            'id':         self.id,
            'log_id':     self.log_id,
            'user_id':    self.user_id,
            'type':       self.type,
            'message':    self.message,
            'status':     self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
