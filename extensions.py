"""extensions.py — Instances partagées Flask (évite les imports circulaires)"""
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail

db   = SQLAlchemy()
bcrypt = Bcrypt()
mail   = Mail()
