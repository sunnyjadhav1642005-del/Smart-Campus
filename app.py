
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)
from werkzeug.security import (
    generate_password_hash, check_password_hash
)
from database import create_database, get_connection
from duplicate_detector import find_duplicate
from pathlib import Path
from functools import wraps
from uuid import uuid4
import os
import pickle
import secrets


app = Flask(__name__)

import secrets

app.secret_key = os.environ.get("SMARTCAMPUS_SECRET_KEY") or secrets.token_hex(32)

ADMIN_EMAIL = os.environ.get(
    "SMARTCAMPUS_ADMIN_EMAIL",
    "admin@smartcampus.com"
)

ADMIN_PASSWORD = os.environ.get(
    "SMARTCAMPUS_ADMIN_PASSWORD",
    "Campus@12345"
)

BASE_DIR = Path(__file__).resolve().parent


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

create_database()

PRINCIPAL_EMAIL = "principal@smartcampus.com"
PRINCIPAL_PASSWORD = "Principal@123"




def create_default_principal():
    connection = get_connection()

    try:
        existing = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (PRINCIPAL_EMAIL,)
        ).fetchone()

        if existing:
            connection.execute("""
                UPDATE users
                SET username = ?,
                    password_hash = ?,
                    role = ?,
                    name = ?
                WHERE email = ?
            """, (
                "principal",
                generate_password_hash("Principal@123"),
                "Principal/Admin",
                "Principal",
                PRINCIPAL_EMAIL
            ))

            connection.commit()
            print("Principal username and password updated!")

        else:
            connection.execute("""
                INSERT INTO users (
                    name, email, username,
                    password_hash, role, department
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "Principal",
                PRINCIPAL_EMAIL,
                "principal",
                generate_password_hash("Principal@123"),
                "Principal/Admin",
                "Administration"
            ))

            connection.commit()
            print("Default Principal account created!")

    finally:
        connection.close()


create_default_principal()



# --------------------------------------------------
# LOAD AI MODELS
# --------------------------------------------------

def load_model(filename):
    model_path = BASE_DIR / filename

    if not model_path.exists():
        raise FileNotFoundError(
            f"{filename} not found. Please train the model first."
        )

    with open(model_path, "rb") as file:
        return pickle.load(file)


category_model = load_model("complaint_model.pkl")
priority_model = load_model("priority_model.pkl")


# --------------------------------------------------
# ACCESS CONTROL
# --------------------------------------------------

def admin_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):

        if not session.get("admin_logged_in"):
            flash("Please login as admin first.")
            return redirect(url_for("login"))

        return route_function(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    def decorator(route_function):

        @wraps(route_function)
        def wrapper(*args, **kwargs):

            if session.get("user_role") not in allowed_roles:
                flash("You are not authorized to access this page.")
                return redirect(url_for("login"))

            return route_function(*args, **kwargs)

        return wrapper

    return decorator


# --------------------------------------------------
# AUTOMATIC ESCALATION
# --------------------------------------------------

def get_escalation_level(age_days):

    if age_days >= 5:
        return "Principal/Director"

    if age_days >= 3:
        return "Admin"

    return "Department/HOD"


# --------------------------------------------------
# STUDENT REGISTRATION
# --------------------------------------------------

@app.route("/student-register", methods=["GET", "POST"])
def student_register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        department = request.form.get("department", "").strip()

        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([
            name, email, department, password, confirm_password
        ]):
            flash("Please fill in all fields.")
            return redirect(url_for("student_register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("student_register"))

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("student_register"))

        connection = get_connection()

        try:
            existing = connection.execute("""
                SELECT id
                FROM users
                WHERE email = ?
            """, (email,)).fetchone()

            if existing:
                flash("This email is already registered.")
                return redirect(url_for("student_register"))

            username = None

            for attempt in range(10):

                candidate = "STU" + str(
                    secrets.randbelow(900000) + 100000
                )

                duplicate = connection.execute("""
                    SELECT id
                    FROM users
                    WHERE username = ?
                """, (candidate,)).fetchone()

                if not duplicate:
                    username = candidate
                    break

            if not username:
                flash("Could not generate username. Please try again.")
                return redirect(url_for("student_register"))

            connection.execute("""
                INSERT INTO users (
                    name, email, username, password_hash,
                    role, department
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                email,
                username,
                generate_password_hash(password),
                "Student",
                department
            ))

            connection.commit()

            flash(
                "Registration successful! "
                "Please login with your email and password."
            )

            return redirect(url_for("login"))

        except Exception:
            connection.rollback()
            app.logger.exception("Student registration failed.")
            flash("Registration failed. Please try again.")

        finally:
            connection.close()

    return render_template("student_register.html")


# --------------------------------------------------
# ROLE-BASED LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        role = request.form.get("role", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # ADMIN LOGIN
        if role == "Admin":

            if (
                username.lower() == ADMIN_EMAIL.lower()
                and password == ADMIN_PASSWORD
            ):
                session.clear()

                session["admin_logged_in"] = True
                session["user_role"] = "Admin"
                session["admin_email"] = username

                flash("Admin login successful!")
                return redirect(url_for("dashboard"))

            flash("Invalid Admin username or password.")
                    # ADMIN LOGIN
        if role == "Admin":

            if (
                username.strip().lower() == "admin"
                and password == "Admin@123"
            ):

                session.clear()
                session["admin_logged_in"] = True
                session["user_name"] = "Admin"
                session["user_role"] = "Admin"

                flash("Admin login successful!")
                return redirect(url_for("dashboard"))

            flash("Invalid Admin username or password.")

        # STUDENT / PRINCIPAL LOGIN
        elif role in ["Student", "Principal"]:

            connection = get_connection()

            try:
                user = connection.execute("""
                    SELECT *
                    FROM users
                    WHERE username = ? OR email = ?
                """, (
                    username,
                    username.lower()
                )).fetchone()

            finally:
                connection.close()

            expected_role = (
                "Student"
                if role == "Student"
                else "Principal/Admin"
            )

            if (
                user
                and user["role"] == expected_role
                and check_password_hash(
                    user["password_hash"], password
                )
            ):

                session.clear()

                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_role"] = role
                session["department"] = user["department"]

                flash("Login successful!")

                if role == "Student":
                    return redirect(url_for("student_dashboard"))

                return redirect(url_for("principal_dashboard"))

            flash("Invalid username or password.")

        # HOD LOGIN - USERNAME AND PASSWORD
        elif role == "Department Head":

            connection = get_connection()

            try:
                hod = connection.execute("""
                    SELECT
                        u.id AS user_id,
                        u.name,
                        u.password_hash,
                        h.hod_code,
                        h.department,
                        h.active
                    FROM users u
                    JOIN hod_assignments h
                        ON h.user_id = u.id
                    WHERE (u.username = ? OR u.email = ?)
                    AND u.role = 'Department Head'
                """, (
                    username,
                    username.lower()
                )).fetchone()

            finally:
                connection.close()

            if (
                hod
                and hod["active"] == 1
                and check_password_hash(
                    hod["password_hash"], password
                )
            ):

                session.clear()

                session["user_id"] = hod["user_id"]
                session["user_name"] = hod["name"]
                session["user_role"] = "Department Head"
                session["department"] = hod["department"]
                session["hod_code"] = hod["hod_code"]

                flash("HOD login successful!")
                return redirect(url_for("hod_dashboard"))

            flash("Invalid HOD username or password.")

        else:
            flash("Please select a valid login role.")

    # IMPORTANT: This return handles GET requests
    # and failed login attempts.
    return render_template("login.html")


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/")
@admin_required
def dashboard():

    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT *
            FROM complaints
            ORDER BY id DESC
        """).fetchall()

        # Update escalation levels
        for complaint in rows:

            status = (complaint["status"] or "").strip()
            created_at = complaint["created_at"]

            age_row = connection.execute("""
                SELECT CAST(
                    MAX(0, julianday('now') - julianday(?))
                    AS INTEGER
                ) AS age
            """, (created_at,)).fetchone()

            age_days = int(age_row["age"] or 0)

            if status in ("Pending", "In Progress"):

                level = get_escalation_level(age_days)

                connection.execute("""
                    UPDATE complaints
                    SET escalation_level = ?
                    WHERE id = ?
                """, (level, complaint["id"]))

            else:

                connection.execute("""
                    UPDATE complaints
                    SET escalation_level = 'Resolved'
                    WHERE id = ?
                """, (complaint["id"],))

        connection.commit()

        complaints = connection.execute("""
            SELECT *,
                CAST(
                    MAX(0, julianday('now') - julianday(created_at))
                    AS INTEGER
                ) AS pending_days
            FROM complaints
            ORDER BY id DESC
        """).fetchall()

        total_complaints = connection.execute("""
            SELECT COUNT(*) FROM complaints
        """).fetchone()[0]

        pending_complaints = connection.execute("""
            SELECT COUNT(*) FROM complaints
            WHERE TRIM(status) = 'Pending'
        """).fetchone()[0]

        resolved_complaints = connection.execute("""
            SELECT COUNT(*) FROM complaints
            WHERE TRIM(status) = 'Resolved'
        """).fetchone()[0]

        in_progress_complaints = connection.execute("""
            SELECT COUNT(*) FROM complaints
            WHERE TRIM(status) = 'In Progress'
        """).fetchone()[0]

        category_insight = connection.execute("""
            SELECT
                COALESCE(
                    NULLIF(TRIM(category), ''),
                    'Uncategorized'
                ) AS category_name,
                COUNT(*) AS total
            FROM complaints
            GROUP BY COALESCE(
                NULLIF(TRIM(category), ''),
                'Uncategorized'
            )
            ORDER BY total DESC, category_name ASC
            LIMIT 1
        """).fetchone()

        pending_department_insight = connection.execute("""
            SELECT
                COALESCE(
                    NULLIF(TRIM(department), ''),
                    'Unspecified'
                ) AS department_name,
                COUNT(*) AS total
            FROM complaints
            WHERE TRIM(status) = 'Pending'
            GROUP BY COALESCE(
                NULLIF(TRIM(department), ''),
                'Unspecified'
            )
            ORDER BY total DESC, department_name ASC
            LIMIT 1
        """).fetchone()

        high_priority_pending = connection.execute("""
            SELECT COUNT(*)
            FROM complaints
            WHERE LOWER(TRIM(priority)) = 'high'
            AND TRIM(status) IN ('Pending', 'In Progress')
        """).fetchone()[0]

        department_rows = connection.execute("""
            SELECT
                COALESCE(
                    NULLIF(TRIM(department), ''),
                    'Unspecified'
                ) AS department_name,
                COUNT(*) AS total,
                SUM(
                    CASE WHEN TRIM(status) = 'Pending'
                    THEN 1 ELSE 0 END
                ) AS pending,
                SUM(
                    CASE WHEN TRIM(status) = 'In Progress'
                    THEN 1 ELSE 0 END
                ) AS in_progress,
                SUM(
                    CASE WHEN TRIM(status) = 'Resolved'
                    THEN 1 ELSE 0 END
                ) AS resolved
            FROM complaints
            GROUP BY COALESCE(
                NULLIF(TRIM(department), ''),
                'Unspecified'
            )
            ORDER BY total DESC
        """).fetchall()

    finally:
        connection.close()

    unresolved_complaints = [
        complaint for complaint in complaints
        if (complaint["status"] or "").strip()
        in ("Pending", "In Progress")
    ]

    overdue_alerts = [
        complaint for complaint in unresolved_complaints
        if int(complaint["pending_days"] or 0) >= 3
    ]

    department_labels = [
        row["department_name"] for row in department_rows
    ]

    department_totals = [
        row["total"] for row in department_rows
    ]

    department_pending = [
        row["pending"] or 0 for row in department_rows
    ]

    department_in_progress = [
        row["in_progress"] or 0 for row in department_rows
    ]

    department_resolved = [
        row["resolved"] or 0 for row in department_rows
    ]

    return render_template(
        "dashboard.html",
        complaints=complaints,
        total=total_complaints,
        pending=pending_complaints,
        resolved=resolved_complaints,
        in_progress=in_progress_complaints,
        department_rows=department_rows,
        department_labels=department_labels,
        department_totals=department_totals,
        department_pending=department_pending,
        department_in_progress=department_in_progress,
        department_resolved=department_resolved,
        category_insight=category_insight,
        pending_department_insight=pending_department_insight,
        high_priority_pending=high_priority_pending,
        overdue_alerts=overdue_alerts,
        overdue_count=len(overdue_alerts)
    )


# --------------------------------------------------
# NEW COMPLAINT
# --------------------------------------------------


@app.route("/new-complaint", methods=["GET", "POST"])
def new_complaint():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        department = request.form.get("department", "").strip()
        academic_year = request.form.get("academic_year", "").strip()
        division = request.form.get("division", "").strip()
        location_type = request.form.get("location_type", "").strip()
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()

        if not all([
            title, department, academic_year, division,
            location_type, location, description
        ]):
            flash("Please fill in all required fields.")
            return render_template("new_complaint.html")

        # STUDENT PHOTO UPLOAD
        complaint_photo = None
        photo_path = None

        photo_file = request.files.get("complaint_photo")

        if photo_file and photo_file.filename:

            photo_data = photo_file.read(5 * 1024 * 1024 + 1)

            if len(photo_data) > 5 * 1024 * 1024:
                flash("Photo size must not exceed 5 MB.")
                return render_template("new_complaint.html")

            # Verify actual image format using file signature
            if photo_data.startswith(b"\xff\xd8\xff"):
                extension = ".jpg"

            elif photo_data.startswith(
                b"\x89PNG\r\n\x1a\n"
            ):
                extension = ".png"

            elif (
                photo_data[:4] == b"RIFF"
                and photo_data[8:12] == b"WEBP"
            ):
                extension = ".webp"

            else:
                flash("Invalid photo. Upload JPG, PNG or WEBP only.")
                return render_template("new_complaint.html")

            upload_folder = (
                Path(__file__).resolve().parent
                / "static"
                / "uploads"
                / "complaints"
            )

            upload_folder.mkdir(parents=True, exist_ok=True)

            photo_name = f"{uuid4().hex}{extension}"

            photo_path = upload_folder / photo_name

            photo_path.write_bytes(photo_data)

            complaint_photo = (
                f"uploads/complaints/{photo_name}"
            )

        complaint_text = f"{title} {description}"
        text_lower = complaint_text.lower()

        # AI CATEGORY PREDICTION
        network_keywords = [
            "wifi", "wi-fi", "internet", "network", "router",
            "connectivity", "no internet", "signal is weak"
        ]

        if any(word in text_lower for word in network_keywords):
            predicted_category = "Internet / Network"
        else:
            predicted_category = category_model.predict(
                [complaint_text]
            )[0]

        # AI PRIORITY PREDICTION
        predicted_priority = priority_model.predict(
            [complaint_text]
        )[0]

        high_priority_keywords = [
            "complete power failure",
            "entire lab has no electricity",
            "all computers are switched off",
            "power outage affecting all computers",
            "electricity supply completely stopped",
            "practical sessions are stopped",
            "major power failure",
            "electrical sparks",
            "burning smell from electrical wiring",
            "exposed live wire",
            "fire alarm is not working",
            "equipment overheating and smoking"
        ]

        if any(
            word in text_lower
            for word in high_priority_keywords
        ):
            predicted_priority = "High"

        # DUPLICATE DETECTION
        duplicate = None

        try:
            duplicate = find_duplicate(
                title=title,
                description=description,
                location=location
            )

        except Exception:
            app.logger.exception("Duplicate detection failed.")

            flash(
                "Duplicate detection could not run. "
                "Your complaint can still be submitted."
            )

        # SAVE COMPLAINT
        connection = get_connection()

        try:
            cursor = connection.execute("""
                INSERT INTO complaints (
                    title,
                    category,
                    department,
                    academic_year,
                    division,
                    location,
                    description,
                    priority,
                    status,
                    location_type,
                    escalation_level,
                    student_id,
                    complaint_photo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                predicted_category,
                department,
                academic_year,
                division,
                location,
                description,
                predicted_priority,
                "Pending",
                location_type,
                "Department/HOD",
                session.get("user_id")
                if session.get("user_role") == "Student"
                else None,
                complaint_photo
            ))

            complaint_id = cursor.lastrowid
            connection.commit()

        except Exception:
            connection.rollback()

            # Remove uploaded file if database save fails
            if photo_path and photo_path.exists():
                photo_path.unlink()

            app.logger.exception("Complaint could not be saved.")
            flash("Complaint submission failed. Please try again.")

            return render_template("new_complaint.html")

        finally:
            connection.close()

        # SUBMISSION MESSAGE
        if duplicate:
            flash(
                f"Complaint SC-{complaint_id:03d} submitted! "
                f"AI Category: {predicted_category}; "
                f"AI Priority: {predicted_priority}. "
                f"Possible duplicate of SC-{duplicate['id']:03d}: "
                f"{duplicate['title']} "
                f"({duplicate['similarity']}% similarity)."
            )
        else:
            flash(
                f"Complaint SC-{complaint_id:03d} submitted! "
                f"AI Category: {predicted_category}; "
                f"AI Priority: {predicted_priority}. "
                f"No likely duplicate found."
            )

        if session.get("user_role") == "Student":
            return redirect(url_for("student_dashboard"))

        if session.get("admin_logged_in"):
            return redirect(url_for("dashboard"))

        return redirect(url_for("new_complaint"))

    return render_template("new_complaint.html")



# --------------------------------------------------
# UPDATE COMPLAINT STATUS
# --------------------------------------------------

@app.route("/update-status/<int:complaint_id>", methods=["POST"])
@admin_required
def update_status(complaint_id):

    new_status = request.form.get("status", "").strip()

    allowed_statuses = [
        "Pending",
        "In Progress",
        "Resolved"
    ]

    if new_status not in allowed_statuses:
        flash("Invalid complaint status.")
        return redirect(url_for("dashboard"))

    connection = get_connection()

    try:
        cursor = connection.execute("""
            UPDATE complaints
            SET status = ?,
                escalation_level = CASE
                    WHEN ? = 'Resolved' THEN 'Resolved'
                    ELSE escalation_level
                END
            WHERE id = ?
        """, (
            new_status,
            new_status,
            complaint_id
        ))

        connection.commit()

        if cursor.rowcount == 0:
            flash("Complaint not found.")
        else:
            flash("Complaint status updated successfully.")

    finally:
        connection.close()

    return redirect(url_for("dashboard"))


# --------------------------------------------------
# HOD UPDATE COMPLAINT STATUS
# --------------------------------------------------



@app.route("/hod/update-status/<int:complaint_id>", methods=["POST"])
@role_required("Department Head")
def hod_update_status(complaint_id):

    new_status = request.form.get("status", "").strip()
    resolution_file = request.files.get("resolution_photo")

    print("HOD STATUS:", new_status)
    print("HOD PHOTO:", resolution_file.filename if resolution_file else "No file")

    if new_status not in ["Pending", "In Progress", "Resolved"]:
        flash("Invalid complaint status.")
        return redirect(url_for("hod_dashboard"))

    connection = get_connection()
    saved_photo_path = None

    try:
        complaint = connection.execute("""
            SELECT resolution_photo
            FROM complaints
            WHERE id = ? AND assigned_to = ?
        """, (complaint_id, session["user_id"])).fetchone()

        if complaint is None:
            flash("Complaint not assigned to your account.")
            return redirect(url_for("hod_dashboard"))

        photo_path = None

        if resolution_file and resolution_file.filename:
            photo_data = resolution_file.stream.read(5 * 1024 * 1024 + 1)

            if len(photo_data) > 5 * 1024 * 1024:
                flash("Photo must be smaller than 5 MB.")
                return redirect(url_for("hod_dashboard"))

            if photo_data.startswith(b"\xff\xd8\xff"):
                extension = ".jpg"
            elif photo_data.startswith(b"\x89PNG\r\n\x1a\n"):
                extension = ".png"
            elif (
                len(photo_data) >= 12
                and photo_data[:4] == b"RIFF"
                and photo_data[8:12] == b"WEBP"
            ):
                extension = ".webp"
            else:
                flash("Only JPG, PNG and WEBP photos are allowed.")
                return redirect(url_for("hod_dashboard"))

            upload_folder = BASE_DIR / "static" / "uploads" / "resolutions"
            upload_folder.mkdir(parents=True, exist_ok=True)

            photo_name = f"{uuid4().hex}{extension}"
            photo_file = upload_folder / photo_name

            with open(photo_file, "wb") as file:
                file.write(photo_data)

            saved_photo_path = photo_file
            photo_path = f"uploads/resolutions/{photo_name}"

        if (
            new_status == "Resolved"
            and not photo_path
            and not complaint["resolution_photo"]
        ):
            flash("Please upload resolution photo.")
            return redirect(url_for("hod_dashboard"))

        connection.execute("""
            UPDATE complaints
            SET status = ?,
                resolution_photo = COALESCE(?, resolution_photo),
                escalation_level = CASE
                    WHEN ? = 'Resolved' THEN 'Resolved'
                    ELSE escalation_level
                END
            WHERE id = ? AND assigned_to = ?
        """, (
            new_status,
            photo_path,
            new_status,
            complaint_id,
            session["user_id"]
        ))

        connection.commit()
        flash("Complaint status and resolution photo updated successfully!")

    except Exception as error:
        connection.rollback()

        if saved_photo_path and saved_photo_path.exists():
            saved_photo_path.unlink()

        print("HOD UPDATE ERROR:", error)
        flash("Error updating complaint. Check VS Code terminal.")

    finally:
        connection.close()

    return redirect(url_for("hod_dashboard"))



# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out successfully.")

    return redirect(url_for("login"))


# --------------------------------------------------
# RESOLVED COMPLAINTS
# --------------------------------------------------

@app.route("/resolved-complaints")
@admin_required
def resolved_complaints():

    connection = get_connection()

    try:
        complaints = connection.execute("""
            SELECT *
            FROM complaints
            WHERE LOWER(TRIM(status)) = 'resolved'
            ORDER BY id DESC
        """).fetchall()

    finally:
        connection.close()

    return render_template(
        "resolved_complaints.html",
        complaints=complaints
    )


# --------------------------------------------------
# STUDENT DASHBOARD
# --------------------------------------------------

@app.route("/student-dashboard")
@role_required("Student")
def student_dashboard():

    connection = get_connection()

    try:
        complaints = connection.execute("""
            SELECT *
            FROM complaints
            WHERE student_id = ?
            ORDER BY id DESC
        """, (
            session["user_id"],
        )).fetchall()

    finally:
        connection.close()

    return render_template(
        "student_dashboard.html",
        complaints=complaints
    )


# --------------------------------------------------
# HOD DASHBOARD
# --------------------------------------------------

@app.route("/hod-dashboard")
@role_required("Department Head")
def hod_dashboard():

    connection = get_connection()

    try:
        complaints = connection.execute("""
            SELECT *
            FROM complaints
            WHERE assigned_to = ?
            ORDER BY id DESC
        """, (
            session["user_id"],
        )).fetchall()

    finally:
        connection.close()

    return render_template(
        "hod_dashboard.html",
        complaints=complaints
    )



# --------------------------------------------------
# PRINCIPAL DASHBOARD
# --------------------------------------------------

@app.route("/principal-dashboard")
@role_required("Principal")
def principal_dashboard():

    connection = get_connection()

    try:
        complaints = connection.execute("""
            SELECT *
            FROM complaints
            ORDER BY id DESC
        """).fetchall()

        hods = connection.execute("""
            SELECT id, name, department
            FROM users
            WHERE role = 'Department Head'
            ORDER BY department, name
        """).fetchall()

    finally:
        connection.close()

    return render_template(
        "principal_dashboard.html",
        complaints=complaints,
        hods=hods
    )



# --------------------------------------------------
# CREATE HOD ACCOUNT
# --------------------------------------------------


# --------------------------------------------------
# CREATE HOD ACCOUNT
# --------------------------------------------------

@app.route("/create-hod", methods=["POST"])
@role_required("Principal")
def create_hod():

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    department = request.form.get("department", "").strip()

    if not all([name, email, username, password, department]):
        flash("Please fill in all HOD details.")
        return redirect(url_for("principal_dashboard"))

    if len(password) < 8:
        flash("Password must contain at least 8 characters.")
        return redirect(url_for("principal_dashboard"))

    connection = get_connection()

    try:
        existing = connection.execute("""
            SELECT id FROM users
            WHERE email = ? OR username = ?
        """, (email, username)).fetchone()

        if existing:
            flash("Email or username already exists.")
            return redirect(url_for("principal_dashboard"))

        hod_code = "HOD-" + secrets.token_hex(4).upper()

        unused_pin_hash = generate_password_hash(
            secrets.token_urlsafe(32)
        )

        cursor = connection.execute("""
            INSERT INTO users (
                name, email, username, password_hash,
                role, department
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            email,
            username,
            generate_password_hash(password),
            "Department Head",
            department
        ))

        user_id = cursor.lastrowid

        connection.execute("""
            INSERT INTO hod_assignments (
                user_id, hod_code, pin_hash,
                department, assigned_by, active
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            hod_code,
            unused_pin_hash,
            department,
            session.get("user_id"),
            1
        ))

        connection.commit()
        flash("HOD account created successfully!")

    except Exception:
        connection.rollback()
        app.logger.exception("HOD account creation failed.")
        flash("Could not create HOD account. Please check the details.")

    finally:
        connection.close()

    return redirect(url_for("principal_dashboard"))



# --------------------------------------------------
# ASSIGN COMPLAINT TO HOD
# --------------------------------------------------

@app.route("/assign-complaint", methods=["POST"])
@role_required("Principal")
def assign_complaint():

    complaint_id = request.form.get("complaint_id", type=int)
    hod_id = request.form.get("hod_id", type=int)

    if not complaint_id or not hod_id:
        flash("Please select a complaint and HOD.")
        return redirect(url_for("principal_dashboard"))

    connection = get_connection()

    try:
        complaint = connection.execute("""
            SELECT id, title, department
            FROM complaints
            WHERE id = ?
        """, (complaint_id,)).fetchone()

        hod = connection.execute("""
            SELECT id, name, department
            FROM users
            WHERE id = ?
            AND role = 'Department Head'
        """, (hod_id,)).fetchone()

        if not complaint or not hod:
            flash("Invalid complaint or HOD.")
            return redirect(url_for("principal_dashboard"))

        department_aliases = {
            "computer": "computer engineering",
            "it": "information technology",
            "entc": "electronics"
        }

        complaint_department = (
            complaint["department"] or ""
        ).strip().lower()

        hod_department = (
            hod["department"] or ""
        ).strip().lower()

        complaint_department = department_aliases.get(
            complaint_department, complaint_department
        )

        hod_department = department_aliases.get(
            hod_department, hod_department
        )

        if complaint_department != hod_department:
            flash("Please select an HOD from the same department.")
            return redirect(url_for("principal_dashboard"))

        connection.execute("""
            UPDATE complaints
            SET assigned_to = ?,
                assigned_department = ?,
                assigned_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            hod["id"],
            hod["department"],
            complaint_id
        ))

        connection.execute("""
            INSERT INTO notifications (
                user_id, complaint_id, message
            )
            VALUES (?, ?, ?)
        """, (
            hod["id"],
            complaint_id,
            "New complaint assigned: " + complaint["title"]
        ))

        connection.commit()
        flash("Complaint assigned to HOD successfully!")

    except Exception:
        connection.rollback()
        app.logger.exception("Complaint assignment failed.")
        flash("Could not assign complaint.")

    finally:
        connection.close()

    return redirect(url_for("principal_dashboard"))


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
