from app import create_app
from extensions import db
from models import User, UserRole

app = create_app()
with app.app_context():
    admin = User.query.filter_by(role=UserRole.ADMIN).first()
    admin.is_blocked = False
    db.session.commit()
    print('Admin debloque :', admin.email)
