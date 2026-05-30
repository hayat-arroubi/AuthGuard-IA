"""auth/__init__.py — Blueprint authentification"""
from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

from auth import routes  # noqa: F401, E402
