"""
app.py — Point d'entrée Flask
Architecture en Blueprints (BNF-09) : auth/ logs/ ia/ admin/
"""
import os
from flask import Flask, redirect, url_for

from config     import config
from extensions import db, bcrypt, mail


def create_app(config_name: str = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config[config_name])

    # ── Extensions ──────────────────────────────────────────────
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)

    # ── Blueprints — BNF-09 ─────────────────────────────────────
    from auth  import auth_bp
    from admin import admin_bp
    from logs  import logs_bp
    from ia    import ia_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(ia_bp)

    # ── Route racine ────────────────────────────────────────────
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # ── Création des tables (dev) ───────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_admin(app)

    # ── Gestionnaires d'erreurs ─────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template('errors/403.html'), 403

    return app


def _seed_admin(app: Flask):
    """Crée le compte admin par défaut si aucun admin n'existe"""
    from models import User, UserRole
    from extensions import bcrypt as bc

    ADMIN_EMAIL    = 'admin@authplatform.com'
    ADMIN_PASSWORD = 'Admin@1234!'

    with app.app_context():
        admin = User.query.filter_by(role=UserRole.ADMIN).first()
        if not admin:
            admin = User()
            admin.register(bc, ADMIN_EMAIL, 'Administrateur', ADMIN_PASSWORD)
            admin.role = UserRole.ADMIN
            db.session.add(admin)
            db.session.commit()
            print(f'[SEED] Admin créé : {ADMIN_EMAIL} / {ADMIN_PASSWORD}')
        elif not admin.check_password(bc, ADMIN_PASSWORD):
            # Hash obsolète (ex : créé par reset_database.py avec un autre mdp)
            admin.register(bc, admin.email, admin.username, ADMIN_PASSWORD)
            db.session.commit()
            print(f'[SEED] Mot de passe admin mis à jour : {ADMIN_EMAIL} / {ADMIN_PASSWORD}')


# ── Lancement direct ────────────────────────────────────────────
if __name__ == '__main__':
    flask_app = create_app()
    flask_app.run(
        host  = '0.0.0.0',
        port  = int(os.environ.get('PORT', 5000)),
        debug = True
    )
