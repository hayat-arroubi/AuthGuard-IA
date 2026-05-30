"""
admin/routes.py — BF-07, BF-11, BF-12, US-18, US-33, US-34, US-35, US-44
VERSION CORRIGÉE : Déblocage admin fonctionne + résolution des alertes
"""
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, jsonify, g

from admin import admin_bp
from auth.routes import admin_required, get_current_user, login_required
from extensions import db
from models import User, Log, Alerte, AlerteStatus, Session, UserRole


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """US-18 — Dashboard admin avec stats"""
    today = datetime.now(timezone.utc).date()

    # Compteurs
    logins_today = Log.query.filter(
        db.func.date(Log.timestamp) == today
    ).count()
    anomalies_total = Log.query.filter_by(is_anomaly=True).count()
    active_users    = User.query.filter_by(is_blocked=False).count()
    blocked_users   = User.query.filter_by(is_blocked=True).count()
    alerts_open     = Alerte.query.filter_by(status=AlerteStatus.EN_COURS).count()

    # Dernières connexions
    recent_logs = Log.query.order_by(Log.timestamp.desc()).limit(20).all()

    # Données graphique (7 derniers jours)
    chart_data = _get_chart_data()

    return render_template('admin/dashboard.html',
        user           = g.current_user,
        logins_today   = logins_today,
        anomalies      = anomalies_total,
        active_users   = active_users,
        blocked_users  = blocked_users,
        alerts_open    = alerts_open,
        recent_logs    = recent_logs,
        chart_data     = chart_data,
    )


@admin_bp.route('/logs')
@admin_required
def logs():
    """BF-07 : Historique complet avec filtres"""
    date_filter  = request.args.get('date', '')
    user_filter  = request.args.get('user', '')
    ip_filter    = request.args.get('ip', '')
    anomaly_only = request.args.get('anomaly', '') == '1'

    query = Log.query
    if date_filter:
        try:
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Log.timestamp) == d)
        except ValueError:
            pass
    if user_filter:
        query = query.join(User).filter(
            db.or_(User.username.ilike(f'%{user_filter}%'),
                   User.email.ilike(f'%{user_filter}%'))
        )
    if ip_filter:
        query = query.filter(Log.ip_address.ilike(f'%{ip_filter}%'))
    if anomaly_only:
        query = query.filter_by(is_anomaly=True)

    logs_list = query.order_by(Log.timestamp.desc()).limit(200).all()
    users_list = User.query.all()

    return render_template('admin/logs.html',
        user=g.current_user, logs=logs_list, users=users_list,
        date_filter=date_filter, user_filter=user_filter,
        ip_filter=ip_filter, anomaly_only=anomaly_only,
    )


@admin_bp.route('/alertes')
@admin_required
def alertes():
    """BF-11 : Liste des alertes avec statut"""
    status_filter = request.args.get('status', '')
    query = Alerte.query
    if status_filter:
        try:
            query = query.filter_by(status=AlerteStatus(status_filter))
        except ValueError:
            pass

    alertes_list = query.order_by(Alerte.created_at.desc()).all()

    counts = {
        'en_cours': Alerte.query.filter_by(status=AlerteStatus.EN_COURS).count(),
        'resolu':   Alerte.query.filter_by(status=AlerteStatus.RESOLU).count(),
        'ignore':   Alerte.query.filter_by(status=AlerteStatus.IGNORE).count(),
    }

    return render_template('admin/alertes.html',
        user=g.current_user, alertes=alertes_list,
        counts=counts, status_filter=status_filter,
    )


@admin_bp.route('/alertes/<int:alert_id>/status', methods=['POST'])
@admin_required
def update_alert_status(alert_id):
    """BF-11 : Résoudre ou ignorer une alerte"""
    alerte = Alerte.query.get_or_404(alert_id)
    new_status = request.form.get('status')
    try:
        alerte.update_status(new_status)
        db.session.commit()
        flash(f'Alerte #{alert_id} mise à jour : {new_status}.', 'success')
    except ValueError:
        flash('Statut invalide.', 'danger')
    return redirect(url_for('admin.alertes'))


@admin_bp.route('/users')
@admin_required
def users():
    """US-44 : Gestion des utilisateurs"""
    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html',
        user=g.current_user, users=users_list,
    )


@admin_bp.route('/users/<int:user_id>/block', methods=['POST'])
@admin_required
def block_user(user_id):
    """BF-09 / BF-12 : Bloquer un utilisateur"""
    target = User.query.get_or_404(user_id)
    
    # Empêcher l'auto-blocage
    if target.id == g.current_user.id:
        flash('Vous ne pouvez pas bloquer votre propre compte.', 'warning')
        return redirect(url_for('admin.users'))
    
    # Bloquer le compte
    target.block()
    
    # Invalider toutes les sessions actives
    Session.invalidate_all(target.id)
    
    # Log admin action
    _log_admin_action(g.current_user, target, 'BLOCAGE_MANUEL')
    
    db.session.commit()
    
    flash(f'Compte {target.email} bloqué avec succès.', 'warning')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/unblock', methods=['POST'])
@admin_required
def unblock_user(user_id):
    """
    BF-12 : Débloquer manuellement — VERSION CORRIGÉE
    
    ✅ CORRECTIFS APPLIQUÉS :
    1. Déblocage du compte
    2. Résolution automatique des alertes en cours
    3. Invalidation des tokens de déblocage
    4. Logging de l'action admin
    """
    target = User.query.get_or_404(user_id)
    
    # 1. Débloquer le compte
    target.unblock()
    print(f"[ADMIN] Déblocage du compte : {target.email}")
    
    # 2. Résoudre automatiquement toutes les alertes EN_COURS pour cet utilisateur
    # ──────────────────────────────────────────────────────────────────────────
    alertes_ouvertes = Alerte.query.filter_by(
        user_id=target.id,
        status=AlerteStatus.EN_COURS
    ).all()
    
    for alerte in alertes_ouvertes:
        alerte.update_status('resolu')
        print(f"[ADMIN] Alerte #{alerte.id} résolue automatiquement")
    
    # 3. Invalider tous les tokens de déblocage en cours
    # ──────────────────────────────────────────────────────────────────────────
    from models import Authentification
    Authentification.query.filter_by(
        user_id=target.id,
        token_type='UNLOCK',
        is_valid=True
    ).update({'is_valid': False})
    
    # 3bis. Supprimer TOUS les logs de cet utilisateur pour remettre
    #        le scoring IA à zéro (ip_score neutre = 0.5 au prochain login).
    #        Sans cela, l'ip_score peut rester à 1.0 et provoquer
    #        un re-blocage immédiat en dehors des heures normales.
    # ──────────────────────────────────────────────────────────────────────────
    Log.query.filter_by(user_id=target.id).delete()
    print(f"[ADMIN] Historique de logs réinitialisé pour {target.email}")
    
    # 4. Logger l'action admin (traçabilité BF-12)
    # ──────────────────────────────────────────────────────────────────────────
    _log_admin_action(g.current_user, target, 'DEBLOCAGE_MANUEL')
    
    # 5. Commit toutes les modifications
    # ──────────────────────────────────────────────────────────────────────────
    db.session.commit()
    
    flash(f'✅ Compte {target.email} débloqué avec succès. {len(alertes_ouvertes)} alerte(s) résolue(s).', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@admin_required
def change_role(user_id):
    """US-44 : Changer le rôle d'un utilisateur"""
    target   = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    try:
        target.role = UserRole(new_role)
        db.session.commit()
        flash(f'Rôle de {target.email} changé en {new_role}.', 'success')
    except ValueError:
        flash('Rôle invalide.', 'danger')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/force-logout', methods=['POST'])
@admin_required
def force_logout(user_id):
    """US-36 : Forcer déconnexion"""
    target = User.query.get_or_404(user_id)
    Session.invalidate_all(target.id)
    _log_admin_action(g.current_user, target, 'FORCE_LOGOUT')
    db.session.commit()
    flash(f'{target.email} déconnecté de tous les appareils.', 'info')
    return redirect(url_for('admin.users'))


# ── API JSON (pour Chart.js) ────────────────────────────────────
@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    """Données pour Chart.js dashboard"""
    return jsonify(_get_chart_data())


# ── Helpers ─────────────────────────────────────────────────────
def _get_chart_data():
    """Prépare les données 7 derniers jours pour Chart.js"""
    from datetime import timedelta
    labels, normal, anomaly = [], [], []
    for i in range(6, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=i)).date()
        labels.append(day.strftime('%d/%m'))
        n = Log.query.filter(
            db.func.date(Log.timestamp) == day,
            Log.is_anomaly == False
        ).count()
        a = Log.query.filter(
            db.func.date(Log.timestamp) == day,
            Log.is_anomaly == True
        ).count()
        normal.append(n)
        anomaly.append(a)
    return {'labels': labels, 'normal': normal, 'anomaly': anomaly}


def _log_admin_action(admin_user, target_user, action: str):
    """Trace les actions admin dans les logs — BF-12"""
    log = Log.create(
        user_id     = target_user.id,
        email_tried = target_user.email,
        ip          = 'ADMIN_ACTION',
        browser     = f'Admin:{admin_user.email}',
        os_name     = action,
        location    = 'Internal',
        success     = True,  # Action admin = succès
    )
    return log
