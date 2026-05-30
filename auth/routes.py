"""
auth/routes.py — US-09, US-10, US-11, US-12, US-14
BF-01 : Inscription  |  BF-02 : Connexion  |  BF-03 : Déconnexion
BF-04 : Rôles        |  BF-05 : Profil
Sprint 4 : BF-08/09/10 scoring IA, alertes, emails déblocage
"""
import jwt
import secrets
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import (
    request, render_template, redirect, url_for,
    flash, make_response, g, current_app, jsonify
)
from flask_mail import Message

from auth    import auth_bp
from extensions import db, bcrypt, mail
from models  import User, UserRole, Session, Authentification, Log, Alerte


# ───────────────────────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────────────────────
def get_token_from_cookie():
    return request.cookies.get('access_token')


def decode_token(token: str):
    """Décode et valide le JWT"""
    try:
        return jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_current_user():
    """Récupère l'utilisateur courant depuis le cookie JWT"""
    token = get_token_from_cookie()
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    # Vérifier que la session est active en BDD
    session_obj = Session.query.filter_by(token=token, is_active=True).first()
    if not session_obj or session_obj.is_expired():
        return None
    return User.query.get(int(payload['sub']))


# ───────────────────────────────────────────────────────────────
# DÉCORATEURS — US-11 : Gestion des rôles
# ───────────────────────────────────────────────────────────────
def login_required(f):
    """Vérifie que l'utilisateur est connecté"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('auth.login'))
        if user.is_blocked:
            flash('Votre compte est bloqué. Contactez l\'administrateur.', 'danger')
            return redirect(url_for('auth.blocked'))
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Vérifie le rôle de l'utilisateur — BF-04"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            user = g.current_user
            if user.role.value not in roles:
                flash('Accès refusé : droits insuffisants.', 'danger')
                return redirect(url_for('auth.dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    return role_required('admin')(f)


# ───────────────────────────────────────────────────────────────
# ROUTES AUTHENTIFICATION
# ───────────────────────────────────────────────────────────────
@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """US-09 : Inscription — BF-01"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        # Validations
        errors = []
        if not username or len(username) < 3:
            errors.append('Le nom doit contenir au moins 3 caractères.')
        if not email or '@' not in email:
            errors.append('Email invalide.')
        if len(password) < 8:
            errors.append('Le mot de passe doit contenir au moins 8 caractères.')
        if password != confirm:
            errors.append('Les mots de passe ne correspondent pas.')
        if User.query.filter_by(email=email).first():
            errors.append('Cet email est déjà utilisé.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('auth/register.html', username=username, email=email)

        # Création utilisateur — BNF-01 : bcrypt coût 12
        user = User()
        user.register(bcrypt, email, username, password)
        db.session.add(user)
        db.session.commit()

        flash('Compte créé avec succès ! Vous pouvez vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """US-10 : Connexion — BF-02 + BF-06 (logs) + BF-08 (scoring IA)"""
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # Récupérer info navigateur/IP — BF-06
        ip         = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        browser, os_name = _parse_user_agent(user_agent)

        user = User.query.filter_by(email=email).first()

        # Vérifier d'abord le mot de passe (ne pas révéler si le compte existe)
        if not user or not user.check_password(bcrypt, password):
            flash('Email ou mot de passe incorrect.', 'danger')
            # BUG FIX : passer user.id si l'utilisateur existe, pour que le scorer
            # puisse compter les tentatives échouées et déclencher le blocage
            _log_attempt(user.id if user else None, email, ip, browser, os_name, success=False)

            # Vérifier le blocage par brute-force si l'utilisateur existe
            if user and user.role != UserRole.ADMIN:
                anomaly_score, is_anomaly, threat_type = _score_connection(user.id, ip)

                # Mettre à jour le dernier log avec le vrai score et flag anomalie
                last_log = Log.query.filter_by(
                    user_id=user.id, login_success=False
                ).order_by(Log.id.desc()).first()
                if last_log:
                    last_log.anomaly_score = anomaly_score
                    last_log.is_anomaly    = is_anomaly
                    db.session.flush()

                if is_anomaly:
                    user.block()
                    log = last_log
                    if log:
                        alerte = Alerte.create(
                            log_id=log.id, user_id=user.id,
                            alert_type=threat_type or 'BRUTE_FORCE',
                            message=(
                                f'Blocage automatique : {user.email} depuis {ip} '
                                f'(score : {anomaly_score:.4f}, type : {threat_type})'
                            ),
                        )
                    unlock_token = _create_unlock_token(user.id)
                    db.session.commit()
                    _send_admin_alert(user, log, alerte if log else None, anomaly_score, threat_type)
                    _send_unlock_email(user, unlock_token)
                    from flask import session as flask_session
                    flask_session['unlock_url'] = url_for(
                        'auth.unlock_account', token=unlock_token, _external=True
                    )
                    return redirect(url_for('auth.blocked'))

            return render_template('auth/login.html', email=email)

        # Mot de passe correct — vérifier si le compte est bloqué
        if user.is_blocked:
            _log_attempt(user.id, email, ip, browser, os_name, success=False)
            # Générer un nouveau lien de déblocage à chaque tentative
            Authentification.query.filter_by(
                user_id=user.id, token_type='UNLOCK', is_valid=True
            ).update({'is_valid': False})
            unlock_token = _create_unlock_token(user.id)
            db.session.commit()
            _send_unlock_email(user, unlock_token)
            from flask import session as flask_session
            flask_session['unlock_url'] = url_for(
                'auth.unlock_account', token=unlock_token, _external=True
            )
            return redirect(url_for('auth.blocked'))

        # ── Scoring IA — BF-08 (jamais sur les admins) ───────
        if user.role == UserRole.ADMIN:
            anomaly_score, is_anomaly, threat_type = 0.0, False, None
        else:
            anomaly_score, is_anomaly, threat_type = _score_connection(user.id, ip)

        # ── Log de connexion — BF-06 ───────────────────────────
        log = Log.create(
            user_id   = user.id,
            email_tried = email,
            ip         = ip,
            browser    = browser,
            os_name    = os_name,
            location   = 'N/A',
            score      = anomaly_score,
            is_anomaly = is_anomaly,
            success    = True,
        )
        db.session.flush()

        if is_anomaly:
            # BF-09 : Blocage automatique
            user.block()

            # Créer alerte en BDD — BF-11
            alerte = Alerte.create(
                log_id     = log.id,
                user_id    = user.id,
                alert_type = threat_type or 'COMPORTEMENT_ANORMAL',
                message    = (
                    f'Anomalie détectée pour {user.email} depuis {ip} '
                    f'(score : {anomaly_score:.4f}, type : {threat_type})'
                ),
            )
            # Générer token de déblocage — US-30/US-32
            unlock_token = _create_unlock_token(user.id)
            db.session.commit()

            # Envoyer emails — BF-10
            _send_admin_alert(user, log, alerte, anomaly_score, threat_type)
            _send_unlock_email(user, unlock_token)
            # Stocker le lien dans la session pour l'afficher sur la page bloquée
            from flask import session as flask_session
            flask_session['unlock_url'] = url_for('auth.unlock_account', token=unlock_token, _external=True)
            return redirect(url_for('auth.blocked'))

        # ── Génération token JWT — BNF-02 ──────────────────────
        expires  = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        payload  = {
            'sub':  str(user.id),
            'role': user.role.value,
            'iat':  datetime.now(timezone.utc),
            'exp':  datetime.now(timezone.utc) + expires,
            'jti':  secrets.token_hex(16),   # identifiant unique par token
        }
        token = jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

        # ── Session en BDD ─────────────────────────────────────
        Session.create(
            user_id    = user.id,
            token      = token,
            expires_at = datetime.now(timezone.utc) + expires,
            ip         = ip,
            ua         = user_agent[:256],
        )
        db.session.commit()

        # ── Cookie JWT (HttpOnly) ───────────────────────────────
        resp = make_response(redirect(url_for('admin.dashboard') if user.role == UserRole.ADMIN else url_for('auth.user_dashboard')))
        resp.set_cookie(
            'access_token', token,
            httponly=True,
            secure=current_app.config.get('JWT_COOKIE_SECURE', False),
            samesite='Lax',
            max_age=int(expires.total_seconds())
        )
        return resp

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    """US-14 : Déconnexion — BF-03"""
    token = get_token_from_cookie()
    if token:
        session_obj = Session.query.filter_by(token=token).first()
        if session_obj:
            session_obj.invalidate()
            db.session.commit()

    resp = make_response(redirect(url_for('auth.login')))
    resp.delete_cookie('access_token')
    flash('Vous avez été déconnecté.', 'info')
    return resp


@auth_bp.route('/blocked')
def blocked():
    """BF-09 : Page compte bloqué — US-31"""
    from flask import session as flask_session
    unlock_url = flask_session.pop('unlock_url', None)
    return render_template('auth/blocked.html', unlock_url=unlock_url)


@auth_bp.route('/unlock/<token>')
def unlock_account(token):
    """US-32 : Déblocage automatique via lien email (token valide 30 min)"""
    auth_obj = Authentification.query.filter_by(
        token_value=token,
        token_type='UNLOCK',
        is_valid=True,
    ).first()

    if not auth_obj:
        flash('Lien de déblocage invalide ou déjà utilisé.', 'danger')
        return redirect(url_for('auth.login'))

    if not auth_obj.verify_token():
        flash('Le lien a expiré (30 min). Demandez un nouveau lien depuis la page de blocage.', 'warning')
        return redirect(url_for('auth.blocked'))

    user = User.query.get(auth_obj.user_id)
    if user:
        user.unblock()
        auth_obj.revoke_token()
        
        # Supprimer les logs d'échecs pour éviter le re-blocage immédiat
        Log.query.filter_by(user_id=user.id, login_success=False).delete()
        
        db.session.commit()
        flash('Votre compte a été débloqué. Vous pouvez vous reconnecter.', 'success')

    return redirect(url_for('auth.login'))


@auth_bp.route('/resend-unlock', methods=['POST'])
def resend_unlock():
    """US-31 : Renvoyer le lien de déblocage depuis la page blocked"""
    email = request.form.get('email', '').strip().lower()
    user  = User.query.filter_by(email=email).first()

    # Réponse identique qu'il existe ou non (anti-énumération)
    flash('Si cet email correspond à un compte bloqué, un nouveau lien vous a été envoyé.', 'info')

    if user and user.is_blocked:
        # Invalider les anciens tokens UNLOCK
        Authentification.query.filter_by(
            user_id=user.id,
            token_type='UNLOCK',
            is_valid=True,
        ).update({'is_valid': False})

        unlock_token = _create_unlock_token(user.id)
        db.session.commit()
        _send_unlock_email(user, unlock_token)

    return redirect(url_for('auth.blocked'))


# ───────────────────────────────────────────────────────────────
# ROUTES PROFIL — US-12 : BF-05
# ───────────────────────────────────────────────────────────────
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """US-12 : Consulter et modifier le profil"""
    user = g.current_user

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            new_username = request.form.get('username', '').strip()
            new_email    = request.form.get('email', '').strip().lower()

            if new_email != user.email:
                existing = User.query.filter_by(email=new_email).first()
                if existing:
                    flash('Cet email est déjà utilisé.', 'danger')
                    return redirect(url_for('auth.profile'))

            user.update_profile(username=new_username, email=new_email)
            db.session.commit()
            flash('Profil mis à jour avec succès.', 'success')

        elif action == 'change_password':
            old_pw  = request.form.get('old_password', '')
            new_pw  = request.form.get('new_password', '')
            confirm = request.form.get('confirm_password', '')

            if not user.check_password(bcrypt, old_pw):
                flash('Mot de passe actuel incorrect.', 'danger')
            elif len(new_pw) < 8:
                flash('Le nouveau mot de passe doit contenir au moins 8 caractères.', 'danger')
            elif new_pw != confirm:
                flash('Les mots de passe ne correspondent pas.', 'danger')
            else:
                user.password_hash = bcrypt.generate_password_hash(new_pw, rounds=12).decode('utf-8')
                db.session.commit()
                flash('Mot de passe modifié avec succès.', 'success')

        return redirect(url_for('auth.profile'))

    # Logs de l'utilisateur
    user_logs = Log.get_by_user(user.id)[:10]
    return render_template('user/profile.html', user=user, logs=user_logs)


@auth_bp.route('/dashboard')
@login_required
def user_dashboard():
    """Dashboard utilisateur"""
    user = g.current_user
    if user.role == UserRole.ADMIN:
        return redirect(url_for('admin.dashboard'))
    recent_logs = Log.get_by_user(user.id)[:5]
    return render_template('user/dashboard.html', user=user, logs=recent_logs)


# ───────────────────────────────────────────────────────────────
# HELPERS PRIVÉS
# ───────────────────────────────────────────────────────────────
def _parse_user_agent(ua: str):
    """Extrait navigateur et OS depuis le User-Agent"""
    ua_lower = ua.lower()
    # Navigateur
    if 'firefox' in ua_lower:
        browser = 'Firefox'
    elif 'edg' in ua_lower:
        browser = 'Edge'
    elif 'chrome' in ua_lower:
        browser = 'Chrome'
    elif 'safari' in ua_lower:
        browser = 'Safari'
    else:
        browser = 'Autre'
    # OS
    if 'windows' in ua_lower:
        os_name = 'Windows'
    elif 'mac' in ua_lower:
        os_name = 'macOS'
    elif 'linux' in ua_lower:
        os_name = 'Linux'
    elif 'android' in ua_lower:
        os_name = 'Android'
    elif 'iphone' in ua_lower or 'ipad' in ua_lower:
        os_name = 'iOS'
    else:
        os_name = 'Autre'
    return browser, os_name


def _log_attempt(user_id, email, ip, browser, os_name, success=False):
    """Log une tentative de connexion échouée"""
    Log.create(
        user_id=user_id, email_tried=email, ip=ip,
        browser=browser, os_name=os_name,
        location='N/A', success=success
    )
    db.session.commit()


def _score_connection(user_id: int, ip: str) -> tuple:
    """
    US-27 : Scoring IA temps réel via Isolation Forest.
    Retourne (score: float, is_anomaly: bool, threat_type: str | None).
    """
    from ia.scorer import score as ia_score
    model_path = current_app.config.get('MODEL_PATH', '')
    threshold  = current_app.config.get('ANOMALY_THRESHOLD', -0.5)
    try:
        return ia_score(user_id, ip, model_path, threshold, Log)
    except Exception as e:
        current_app.logger.error(f'[IA] Erreur scoring : {e}')
        return 0.0, False, None


# ───────────────────────────────────────────────────────────────
# HELPERS EMAIL & TOKEN — Sprint 4
# ───────────────────────────────────────────────────────────────
def _create_unlock_token(user_id: int) -> str:
    """Génère et stocke un token de déblocage valide 30 min — US-30/US-32"""
    token_value = secrets.token_urlsafe(32)
    expires     = datetime.now(timezone.utc) + current_app.config['UNLOCK_TOKEN_EXPIRES']
    auth_obj    = Authentification(
        user_id     = user_id,
        token_type  = 'UNLOCK',
        token_value = token_value,
        expires_at  = expires,
        is_valid    = True,
    )
    db.session.add(auth_obj)
    return token_value


def _send_admin_alert(user, log, alerte, score: float, threat_type: str):
    """BF-10 : Email d'alerte à l'admin avec détails de l'anomalie"""
    try:
        admin_email = current_app.config.get('ADMIN_EMAIL', '')
        mail_user   = current_app.config.get('MAIL_USERNAME', '')
        print(f'[MAIL] MAIL_USERNAME={mail_user!r}  ADMIN_EMAIL={admin_email!r}')
        if not admin_email or not mail_user:
            print('[MAIL] Email non configure — alerte admin ignoree')
            return
        subject = f'[ALERTE IA] Anomalie détectée — {user.username}'
        body = render_template(
            'email/admin_alert.html',
            user=user, log=log, alerte=alerte,
            score=score, threat=threat_type,
        )
        msg = Message(subject, recipients=[admin_email], html=body)
        mail.send(msg)
        print(f'[MAIL] Alerte admin envoyee a {admin_email}')
    except Exception as e:
        print(f'[MAIL] ERREUR alerte admin : {e}')


def _send_unlock_email(user, token_value: str):
    """US-30 : Email à l'utilisateur avec lien de déblocage valide 30 min"""
    unlock_url = url_for('auth.unlock_account', token=token_value, _external=True)

    # Toujours afficher le lien dans la console (utile en dev)
    print('\n' + '='*60)
    print(f'[DEBLOCAGE] Compte : {user.email}')
    print(f'[DEBLOCAGE] Lien   : {unlock_url}')
    print('='*60 + '\n')

    if not current_app.config.get('MAIL_USERNAME'):
        return

    try:
        subject = 'AuthGuard — Débloquez votre compte'
        body = render_template(
            'email/user_unlock.html',
            user=user,
            unlock_url=unlock_url,
            expires_minutes=30,
        )
        msg = Message(subject, recipients=[user.email], html=body)
        mail.send(msg)
        print(f'[MAIL] Email deblocage envoye a {user.email}')
    except Exception as e:
        print(f'[MAIL] ERREUR envoi email : {e}')
        print(f'[MAIL] Utilise le lien console ci-dessus pour debloquer')
