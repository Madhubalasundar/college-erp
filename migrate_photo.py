"""
Migration script to add profile_photo column to students table.
Run with: python migrate_photo.py
"""
from app import create_app
from models import db
from sqlalchemy import inspect, text

app = create_app()

with app.app_context():
    db.create_all()

    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('students')]

    if 'profile_photo' not in columns:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE students ADD COLUMN profile_photo VARCHAR(255)"))
            conn.commit()
        print("Added column: profile_photo")
    else:
        print("Column profile_photo already exists")

    # Create upload directory
    import os
    upload_dir = os.path.join(app.root_path, "static", "uploads", "students")
    os.makedirs(upload_dir, exist_ok=True)
    print(f"Upload directory ready: {upload_dir}")

    print("\nMigration complete!")
