"""logs/__init__.py — Sprint 3"""
from flask import Blueprint
logs_bp = Blueprint('logs', __name__, url_prefix='/logs')
