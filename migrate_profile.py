"""
Migration script to add Faculty Profile fields and new tables.
Run with: python migrate_profile.py
"""
from app import create_app
from models import db

app = create_app()

with app.app_context():
    # Create all tables (this will create new tables but not alter existing ones)
    db.create_all()

    # Check if columns exist and add them if missing
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('faculty')]

    new_columns = {
        'date_of_birth': 'DATE',
        'gender': 'VARCHAR(10)',
        'address': 'VARCHAR(255)',
        'city': 'VARCHAR(100)',
        'state': 'VARCHAR(100)',
        'emergency_contact': 'VARCHAR(20)',
        'qualification': 'VARCHAR(200)',
        'specialization': 'VARCHAR(200)',
        'experience_years': 'INTEGER DEFAULT 0',
        'profile_photo': 'VARCHAR(255)',
    }

    with db.engine.connect() as conn:
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                try:
                    conn.execute(text(f"ALTER TABLE faculty ADD COLUMN {col_name} {col_type}"))
                    print(f"Added column: {col_name}")
                except Exception as e:
                    print(f"Column {col_name} may already exist: {e}")
            else:
                print(f"Column {col_name} already exists")

        conn.commit()

    print("\nMigration complete!")
    print("New tables created: faculty_documents, faculty_attendance")
    print("New columns added to faculty table: date_of_birth, gender, address, city, state, emergency_contact, qualification, specialization, experience_years, profile_photo")
