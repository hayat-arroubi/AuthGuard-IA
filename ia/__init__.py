"""ia/__init__.py — Sprint 4 : Isolation Forest"""
from flask import Blueprint
ia_bp = Blueprint('ia', __name__, url_prefix='/ia')

from ia import routes  # noqa: F401, E402
