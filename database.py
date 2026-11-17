
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "smart_campus.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                department TEXT NOT NULL,
                academic_year TEXT NOT NULL,
                division TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Medium',
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add missing columns without deleting existing data.
        columns = connection.execute(
            "PRAGMA table_info(complaints)"
        ).fetchall()

        column_names = [column["name"] for column in columns]

        new_columns = {
            "location_type": "TEXT NOT NULL DEFAULT 'Other Campus Area'",
            "escalation_level": "TEXT NOT NULL DEFAULT 'Department/HOD'",
            "escalated_at": "TEXT",
            "student_id": "INTEGER",
            "assigned_to": "INTEGER",
            "assigned_department": "TEXT",
            "assigned_at": "TEXT",
            "updated_at": "TEXT",

            # NEW: Student complaint photo
            "complaint_photo": "TEXT",

            # NEW: HOD resolution proof photo
            "resolution_photo": "TEXT",
        }

        for column_name, column_definition in new_columns.items():
            if column_name not in column_names:
                connection.execute(
                    f"ALTER TABLE complaints ADD COLUMN "
                    f"{column_name} {column_definition}"
                )

        # User accounts
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (
                    role IN (
                        'Student',
                        'Principal/Admin',
                        'Department Head'
                    )
                ),
                department TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Notifications
        connection.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                complaint_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (complaint_id) REFERENCES complaints(id)
            )
        """)

        # Student username
        user_columns = connection.execute(
            "PRAGMA table_info(users)"
        ).fetchall()

        user_column_names = [
            column["name"] for column in user_columns
        ]

        if "username" not in user_column_names:
            connection.execute("""
                ALTER TABLE users ADD COLUMN username TEXT
            """)

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_users_username
            ON users(username)
            WHERE username IS NOT NULL
        """)

        # HOD assignments
        connection.execute("""
            CREATE TABLE IF NOT EXISTS hod_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                hod_code TEXT NOT NULL UNIQUE,
                pin_hash TEXT NOT NULL,
                department TEXT NOT NULL,
                assigned_by INTEGER,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (assigned_by) REFERENCES users(id)
            )
        """)

        # Complaint status history
        connection.execute("""
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id INTEGER NOT NULL,
                changed_by INTEGER,
                old_status TEXT,
                new_status TEXT NOT NULL,
                note TEXT,
                changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (complaint_id) REFERENCES complaints(id),
                FOREIGN KEY (changed_by) REFERENCES users(id)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaints_student
            ON complaints(student_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaints_assigned
            ON complaints(assigned_to)
        """)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    create_database()
    print("SmartCampus database updated successfully!")
