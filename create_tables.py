from app import app, db
from models import AuditLog

with app.app_context():
    db.create_all()
    print("Database tables updated (AuditLog created if not exists).")
