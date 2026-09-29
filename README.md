# Vertex College ERP — Python Full-Stack (SQLite Edition)

The same Flask app as the MySQL version, reconfigured to run on **SQLite**
— a single local database file, nothing to install or configure. Good
for local development, demos, or small deployments where a separate
MySQL server is overkill.

## Tech Stack

- **Backend:** Python 3.10+, Flask, Flask-SQLAlchemy, Flask-Login
- **Database:** SQLite (built into Python — no server, no separate install)
- **Frontend:** Server-rendered Jinja2 templates, vanilla CSS/JS, Font Awesome

## What's included

Identical feature set to the MySQL version:

- Single login page with 6 role selectors: Student, Faculty, HOD, Principal,
  Office Staff, Admin — each redirects to its own dashboard.
- **Student:** dashboard, attendance, internal marks, semester results,
  fee payment, timetable, profile.
- **Faculty:** dashboard, attendance entry, marks entry, timetable.
- **HOD:** department dashboard, faculty management, student reports,
  department attendance & results analytics.
- **Principal:** college-wide dashboard, finance overview, attendance analytics.
- **Office Staff:** fee collection desk (search by roll number, collect payment).
- **Admin:** full CRUD for users (search/filter/paginate), departments,
  courses, subjects.
- Security: password hashing (Werkzeug), session-based auth (Flask-Login),
  parameterized queries (SQLAlchemy ORM), role-based route guards on
  every blueprint.

## Setup

1. **Install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Create the database** (creates `instance/college_erp.db` and all
   tables, plus base departments/courses/subjects):
   ```bash
   python init_db.py
   ```

3. **Seed demo data** (creates one login per role, sample attendance/
   marks/fees/timetable):
   ```bash
   python seed_data.py
   ```

4. **Run the app:**
   ```bash
   python app.py
   ```
   Visit `http://localhost:5000`

That's it — no database server, no `mysql -u root -p`, nothing else to
configure. The whole database lives in one file: `instance/college_erp.db`.

## Demo logins

| Role         | Username    | Password    |
|--------------|-------------|-------------|
| Admin        | admin       | Admin@123   |
| Student      | student1    | Passw0rd!   |
| Faculty      | faculty1    | Passw0rd!   |
| HOD          | hod_cse     | Passw0rd!   |
| Principal    | principal   | Passw0rd!   |
| Office Staff | office1     | Passw0rd!   |

## Resetting the database

Just delete the file and re-run the two setup scripts:

```bash
rm instance/college_erp.db
python init_db.py
python seed_data.py
```

## Switching to MySQL/Postgres later

The app doesn't hard-code SQLite — `config.py` reads `DATABASE_URL` from
the environment and only falls back to a local SQLite file if it's unset.
To point it at MySQL instead:

```bash
pip install pymysql
export DATABASE_URL="mysql+pymysql://user:password@localhost/college_erp"
python init_db.py
python seed_data.py
python app.py
```

## Folder structure

```
college-erp-sqlite/
├── app.py                 # App factory & entry point
├── config.py                # Configuration (SQLite by default, env-driven)
├── models.py                  # SQLAlchemy models (includes Result, fixed vs. earlier build)
├── auth.py                      # Login/logout/change-password + role guard
├── init_db.py                     # Creates tables + reference data (departments/courses/subjects)
├── seed_data.py                     # Demo login + sample data seeder
├── requirements.txt
├── instance/                          # SQLite .db file lives here (created on first run)
├── blueprints/
│   ├── student.py
│   ├── faculty.py
│   ├── hod.py
│   ├── principal.py
│   ├── office.py
│   └── admin.py
├── static/
│   ├── css/main.css
│   └── js/main.js
└── templates/
    ├── layout_public.html / layout_app.html
    ├── landing.html / login.html / change_password.html
    ├── partials/            # per-role sidebar navs
    ├── student/ faculty/ hod/ principal/ office/ admin/
    └── errors/
```

## What changed from the MySQL version

This isn't just a config swap — a few things needed real fixes to work
correctly on SQLite (and were genuine bugs in the original build, now
fixed here too):

- **`func.if_()` → `case()`** — MySQL's `IF()` function isn't portable;
  the HOD and Principal attendance-percentage queries now use SQLAlchemy's
  standard `case()` expression, which works on SQLite, MySQL, and Postgres.
- **Missing `Result` model** — the Student "Semester Results" page queried
  a `results` table via raw SQL that was never actually created by the
  ORM (no matching model existed). Added a proper `Result` model and
  switched that route to a normal ORM query.
- **Principal dashboard join bug** — the department/student breakdown
  query was accidentally joining the `Department` table against itself
  instead of through `Course.dept_id`, which returned wrong/empty results.
  Fixed to join `Student → Course → Department` correctly.

All of this was verified end-to-end with the Flask test client — every
route for all 6 roles (GET) and the main write actions (fee payment,
attendance entry, admin CRUD) were actually exercised against a real
SQLite database before packaging, not just assumed to work.

## Extending this project

Same pattern as before, applies to both DB backends since this project
doesn't use any MySQL-only SQL now:
1. Add model(s) to `models.py`
2. Run migrations manually (or just delete `instance/college_erp.db` and
   re-run `init_db.py` in development)
3. Add routes to the relevant blueprint in `blueprints/`
4. Add templates under `templates/<role>/`
5. Add a sidebar link in `templates/partials/sidebar_<role>.html`
