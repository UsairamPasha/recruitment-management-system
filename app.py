from datetime import datetime
from flask import Flask, render_template, request, redirect, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import get_db
from utils.merit import calculate_merit

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Change this to a secure key

@app.route("/")
def home():
    return render_template("index.html")

#________________________Register______________________________________
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # 🔒 Password length validation
        if len(password) < 8:
            flash("Password must be at least 8 characters long")
            return redirect("/register")

        # 🔁 Password match validation
        if password != confirm_password:
            flash("Passwords do not match")
            return redirect("/register")

        hashed_password = generate_password_hash(password)

        db = get_db()
        try:
            db.execute("""
                INSERT INTO users (first_name, last_name, username, email, password, role)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (first_name, last_name, username, email, hashed_password, "candidate"))
            db.commit()
        except Exception:
            flash("Username or Email already exists")
            return redirect("/register")
        finally:
            db.close()

        flash("Registration successful! Please login.")
        return redirect("/login/candidate")

    return render_template("auth/register.html")

@app.route("/register/employee", methods=["GET", "POST"])
def register_employee():
    if request.method == "POST":
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if len(password) < 8:
            flash("Password must be at least 8 characters long")
            return redirect("/register/employee")

        if password != confirm_password:
            flash("Passwords do not match")
            return redirect("/register/employee")

        db = get_db()

        user_exists = db.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if user_exists:
            flash("Username or Email already exists")
            db.close()
            return redirect("/register/employee")

        db.execute("""
            INSERT INTO users 
            (first_name, last_name, username, email, password, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            first_name,
            last_name,
            username,
            email,
            generate_password_hash(password),
            "employee"
        ))

        db.commit()
        db.close()

        flash("Employee account created successfully")
        return redirect("/login/employee")

    return render_template("auth/register_employee.html")

#_________________________________Login_____________________________________
@app.route("/login", methods=["GET"])
def login_landing():
    """Generic /login page shows 3 role boxes."""
    return render_template("auth/login_landing.html")

# Admin login
@app.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=? AND role='admin'", (email,)).fetchone()
        db.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = "admin"
            session["username"] = user["username"]
            return redirect("/admin/dashboard")

        flash("Invalid admin credentials")

    return render_template("auth/login_admin.html")

# employee login
@app.route("/login/employee", methods=["GET", "POST"])
def login_employee():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ? AND role = ?",
            (email, "employee")
        ).fetchone()
        db.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["username"] = user["username"]
            return redirect("/employee/dashboard")

        flash("Invalid employee credentials")

    return render_template("auth/login_employee.html")

# Candidate login
@app.route("/login/candidate", methods=["GET", "POST"])
def login_candidate():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=? AND role='candidate'", (email,)).fetchone()
        db.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = "candidate"
            session["username"] = user["username"]
            return redirect("/candidate/dashboard")

        flash("Invalid candidate credentials")

    return render_template("auth/login_candidate.html")

#______________________________________Logout____________________________________
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully")
    return redirect("/login")

#__________________________________Dashboard routes_______________________________
@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect("/login")
    return render_template("admin/dashboard.html")

@app.route("/candidate/dashboard")
def candidate_dashboard():
    if session.get("role") != "candidate":
        return redirect("/login")
    
    db = get_db()
    
    # 1️⃣ Promote candidate to employee if interview_time has passed
    now = datetime.now().isoformat()  # Current timestamp
    db.execute("""
        UPDATE users
        SET role='employee'
        WHERE id IN (
            SELECT user_id 
            FROM applications
            WHERE status='approved' 
            AND interview_time IS NOT NULL
            AND interview_time <= ?
        )
    """, (now,))
    db.commit()
    
    # Check if logged-in user was promoted
    current_user = db.execute("SELECT role FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if current_user and current_user["role"] == "employee":
        session["role"] = "employee"
        db.close()
        flash("Congratulations! You have been promoted to Employee after your interview.")
        return redirect("/employee/dashboard")

    # 2️⃣ Fetch candidate's applications for dashboard display
    applications = db.execute("""
        SELECT a.*, j.title
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.user_id=?
    """, (session["user_id"],)).fetchall()
    
    db.close()
    
    return render_template("candidate/dashboard.html", applications=applications)

@app.route("/employee/dashboard")
def employee_dashboard():
    if session.get("role") != "employee":
        return redirect("/login")

    db = get_db()
    # Show jobs created by this employee
    jobs = db.execute("""
        SELECT * FROM jobs WHERE created_by=?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()
    db.close()

    return render_template("employee/dashboard.html", jobs=jobs)

#____________________________Admin – Create Job_________________________________
@app.route("/admin/jobs/create", methods=["GET", "POST"])
def create_job():
    if session.get("role") != "admin":
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        min_merit = float(request.form["min_merit"])
        max_applicants = int(request.form["max_applicants"])

        db = get_db()
        db.execute("""
            INSERT INTO jobs (title, description, min_merit, max_applicants, created_by, status)
            VALUES (?, ?, ?, ?, ?, 'open')
        """, (title, description, min_merit, max_applicants, session["user_id"]))
        db.commit()
        db.close()

        flash("Job created successfully")
        return redirect("/admin/jobs")

    return render_template("admin/create_job.html")

#Employee Job create
@app.route("/employee/jobs/create", methods=["GET", "POST"])
def create_job_emp():
    if session.get("role") != "employee":
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        min_merit = float(request.form["min_merit"])
        max_applicants = int(request.form["max_applicants"])

        db = get_db()
        db.execute("""
            INSERT INTO jobs (title, description, min_merit, max_applicants, created_by, status)
            VALUES (?, ?, ?, ?, ?, 'open')
        """, (title, description, min_merit, max_applicants, session["user_id"]))
        db.commit()
        db.close()

        flash("Job created successfully")
        return redirect("/employee/jobs")

    return render_template("employee/create_job.html")

#______________________________Admin – View Jobs___________________________________
@app.route("/admin/jobs")
def admin_jobs():
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    jobs = db.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    db.close()

    return render_template("admin/jobs.html", jobs=jobs)

#______________________________Candidate – View Jobs______________________________
@app.route("/candidate/jobs")
def candidate_jobs():
    if session.get("role") != "candidate":
        return redirect("/login")

    db = get_db()

    # Jobs NOT applied by candidate
    available_jobs = db.execute("""
        SELECT j.*,
        (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id) AS applied_count
        FROM jobs j
        WHERE j.status='open'
        AND j.id NOT IN (
            SELECT job_id FROM applications WHERE user_id=?
        )
    """, (session["user_id"],)).fetchall()

    # Jobs already applied by candidate
    applied_jobs = db.execute("""
        SELECT j.*,
        (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id) AS applied_count
        FROM jobs j
        JOIN applications a ON a.job_id = j.id
        WHERE a.user_id=?
    """, (session["user_id"],)).fetchall()

    db.close()

    return render_template(
        "candidate/jobs.html",
        available_jobs=available_jobs,
        applied_jobs=applied_jobs
    )

#_______________________________Candidate – Apply for Job________________________
@app.route("/candidate/apply/<int:job_id>", methods=["GET", "POST"])
def apply_job(job_id):
    if session.get("role") != "candidate":
        return redirect("/login")

    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()

    if not job:
        flash("Job not found or no longer available")
        db.close()
        return redirect("/candidate/jobs")

    applied_count_row = db.execute("SELECT COUNT(*) as count FROM applications WHERE job_id=?", (job_id,)).fetchone()
    applied_count = applied_count_row["count"] if applied_count_row else 0

    if applied_count >= job["max_applicants"]:
        flash("This job is no longer accepting applications")
        db.close()
        return redirect("/candidate/jobs")

    already_applied = db.execute("SELECT * FROM applications WHERE user_id=? AND job_id=?",
                                 (session["user_id"], job_id)).fetchone()
    if already_applied:
        flash("You have already applied for this job")
        db.close()
        return redirect("/candidate/jobs")

    if request.method == "POST":
        matric = request.form["matric_div"]
        inter = request.form["inter_div"]
        grad = request.form["grad_div"]
        master = request.form["master_div"]
        merit_val = calculate_merit(matric, inter, grad, master)

        # 1️⃣ Insert candidate application
        db.execute("""
            INSERT INTO applications (user_id, job_id, matric_div, inter_div, grad_div, master_div, merit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session["user_id"], job_id, matric, inter, grad, master, merit_val))

        # 2️⃣ Notify all admins
        admins = db.execute("SELECT id FROM users WHERE role='admin'").fetchall()
        for admin_user in admins:
            db.execute(
                "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                (admin_user["id"], f"New application received for job: {job['title']}")
            )

        db.commit()
        db.close()

        flash("Application submitted successfully")
        return redirect("/candidate/jobs")

    db.close()
    return render_template("candidate/apply_job.html", job=job)

#__________________________________View Applications for a Job______________________
@app.route("/admin/job/<int:job_id>/applications")
def view_applications(job_id):
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    applications = db.execute("""
        SELECT a.*, u.first_name, u.last_name, u.username, u.email
        FROM applications a
        JOIN users u ON a.user_id = u.id
        WHERE a.job_id=?
    """, (job_id,)).fetchall()
    db.close()

    apps_with_merit = []
    for app in applications:
        merit = calculate_merit(
            app["matric_div"], app["inter_div"], app["grad_div"], app["master_div"]
        )
        apps_with_merit.append({
            "id": app["id"],
            "name": f"{app['first_name']} {app['last_name']}",
            "username": app["username"],
            "email": app["email"],
            "matric_div": app["matric_div"],
            "inter_div": app["inter_div"],
            "grad_div": app["grad_div"],
            "master_div": app["master_div"],
            "merit": merit,
            "status": app["status"]
        })

    return render_template("admin/view_applications.html", job=job, applications=apps_with_merit)

#___________________________Approve/Reject Application___________________________
@app.route("/admin/application/<int:app_id>/approve", methods=["POST"])
def approve_application(app_id):
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "Access denied"}), 403

    data = request.get_json()
    interview_time = data.get("interview_time") if data else None
    if not interview_time:
        return jsonify({"success": False, "error": "No interview time provided"}), 400

    db = get_db()
    application = db.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
    if not application:
        db.close()
        return jsonify({"success": False, "error": "Application not found"}), 404

    db.execute("""
        UPDATE applications
        SET status='approved', interview_time=?
        WHERE id=?
    """, (interview_time, app_id))

    # Send notification to candidate
    db.execute(
        "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
        (application["user_id"], f"You are approved for the job! Interview at {interview_time}")
    )

    db.commit()
    db.close()

    return jsonify({"success": True})

#______________________________Admin Notifications Route____________________________
@app.route("/admin/notifications")
def admin_notifications():
    if session.get("role") != "admin":
        return redirect("/login")
    db = get_db()

    # 1️⃣ Delete old notifications (older than 1 days)
    db.execute("DELETE FROM notifications WHERE created_at <= datetime('now', '-1 days')")
    db.commit()
    
    # Fetch ONLY notifications for logged-in admin
    notifications = db.execute("""
        SELECT * FROM notifications
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()
    
    # 3️⃣ Mark unread notifications as read
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (session["user_id"],))
    db.commit()
    
    db.close()
    return render_template("admin/notifications.html", notifications=notifications)

#__________________________Candidate Notifications Route________________________________
@app.route("/candidate/notifications")
def candidate_notifications():
    if session.get("role") != "candidate":
        return redirect("/login")
    
    db = get_db()

    # 1️⃣ Delete old notifications (older than 1 days)
    db.execute("DELETE FROM notifications WHERE created_at <= datetime('now', '-1 days')")
    db.commit()

    notifications = db.execute("""
        SELECT * FROM notifications
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()

    # 3️⃣ Mark unread as read
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (session["user_id"],))
    db.commit()

    db.close()
    
    return render_template("candidate/notifications.html", notifications=notifications)

#_______________________________interview_________________________________________
@app.route("/candidate/interview")
def candidate_interview():
    if session.get("role") != "candidate":
        return redirect("/login")
    
    db = get_db()
    interviews = db.execute("""
        SELECT a.interview_time, j.title, j.description
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.user_id=? AND a.status='approved'
        ORDER BY a.applied_at DESC
    """, (session["user_id"],)).fetchall()
    db.close()
    
    return render_template("candidate/interview.html", interviews=interviews)

#__________________________Employee view jobs_____________________________
@app.route("/employee/jobs")
def employee_jobs():
    if session.get("role") != "employee":
        flash("Access denied")
        return redirect("/login")
    
    db = get_db()
    
    jobs = db.execute("""
        SELECT j.*,
        CASE 
            WHEN j.created_by = ? THEN 1
            ELSE 0
        END AS editable
        FROM jobs j
        WHERE j.status='open'
        ORDER BY j.created_at DESC
    """, (session["user_id"],)).fetchall()
    
    db.close()
    return render_template("employee/jobs.html", jobs=jobs)

#________________________________Employee Edit Job Route___________________________
@app.route("/employee/job/<int:job_id>/edit", methods=["GET", "POST"])
def edit_job(job_id):
    if session.get("role") != "employee":
        return redirect("/login")

    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()

    if not job:
        db.close()
        flash("Job not found")
        return redirect("/employee/jobs")

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        db.execute("UPDATE jobs SET title=?, description=? WHERE id=?", (title, description, job_id))
        db.commit()
        db.close()
        flash("Job updated successfully")
        return redirect("/employee/jobs")

    db.close()
    return render_template("employee/edit_job.html", job=job)

#_____________________Admin delete with demotion________________________________
@app.route("/admin/job/<int:job_id>/delete")
def admin_delete_job(job_id):
    if session.get("role") != "admin":
        flash("Access denied")
        return redirect("/login")

    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not job:
        flash("Job not found")
        db.close()
        return redirect("/admin/jobs")

    employees = db.execute("""
        SELECT u.id 
        FROM users u
        JOIN applications a ON u.id = a.user_id
        WHERE u.role='employee' AND a.job_id=?
    """, (job_id,)).fetchall()

    for emp in employees:
        db.execute("UPDATE users SET role='candidate' WHERE id=?", (emp["id"],))

    db.execute("DELETE FROM applications WHERE job_id=?", (job_id,))
    db.execute("DELETE FROM jobs WHERE id=?", (job_id,))

    db.commit()
    db.close()

    flash("Job deleted successfully. Linked employees demoted to candidates.")
    return redirect("/admin/jobs")

#_________________________admin edit post___________________________________________
@app.route("/admin/job/<int:job_id>/edit", methods=["GET", "POST"])
def admin_edit_job(job_id):
    if session.get("role") != "admin":
        flash("Access denied")
        return redirect("/login")

    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not job:
        flash("Job not found")
        db.close()
        return redirect("/admin/jobs")

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        min_merit = float(request.form["min_merit"])
        max_applicants = int(request.form["max_applicants"])

        db.execute("""
            UPDATE jobs 
            SET title=?, description=?, min_merit=?, max_applicants=? 
            WHERE id=?
        """, (title, description, min_merit, max_applicants, job_id))
        db.commit()
        db.close()

        flash("Job updated successfully")
        return redirect("/admin/jobs")

    db.close()
    return render_template("admin/edit_job.html", job=job)

#___________________________Admin reject post_______________________________________
@app.route("/admin/application/<int:app_id>/action/reject")
def reject_application(app_id):
    if session.get("role") != "admin":
        flash("Access denied")
        return redirect("/login")

    db = get_db()
    application = db.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
    if not application:
        flash("Application not found")
        db.close()
        return redirect("/admin/jobs")

    db.execute("UPDATE applications SET status='rejected' WHERE id=?", (app_id,))
    db.execute(
        "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
        (application["user_id"], "Sorry! Your application has been rejected.")
    )
    db.commit()
    db.close()

    flash("Application rejected successfully")
    return redirect(f"/admin/job/{application['job_id']}/applications")

#__________________________Admin – View Employee List and Delete Employee__________________
@app.route("/admin/employees")
def admin_employees():
    if session.get("role") != "admin":
        return redirect("/login")
    
    db = get_db()
    employees = db.execute("SELECT * FROM users WHERE role='employee'").fetchall()
    db.close()
    
    return render_template("admin/employees.html", employees=employees)

@app.route("/admin/employee/<int:user_id>/delete")
def admin_delete_employee(user_id):
    if session.get("role") != "admin":
        flash("Access denied")
        return redirect("/login")

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=? AND role='employee'", (user_id,)).fetchone()
    if not user:
        flash("Employee not found")
        db.close()
        return redirect("/admin/employees")
    
    db.execute("DELETE FROM applications WHERE user_id=?", (user_id,))
    db.execute("DELETE FROM notifications WHERE user_id=?", (user_id,))
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    db.close()
    
    flash("Employee removed successfully")
    return redirect("/admin/employees")

#_____________________________Employee – View Employee List_________________________
@app.route("/employee/employees")
def employee_employees():
    if session.get("role") != "employee":
        return redirect("/login")

    db = get_db()
    employees = db.execute("SELECT id, first_name, last_name, email, username FROM users WHERE role='employee'").fetchall()
    db.close()
    return render_template("employee/employees.html", employees=employees)

#_______________________Employe leave job__________________________________________
@app.route("/employee/leave-job", methods=["GET", "POST"])
def employee_leave_job():
    if session.get("role") != "employee":
        return redirect("/login")

    if request.method == "POST":
        db = get_db()

        db.execute(
            "UPDATE users SET role='candidate' WHERE id=?",
            (session["user_id"],)
        )
        db.execute(
            "DELETE FROM applications WHERE user_id=?",
            (session["user_id"],)
        )

        db.commit()
        db.close()

        session["role"] = "candidate"

        flash("You have left the job and are now a candidate.")
        return redirect("/candidate/dashboard")

    return render_template("employee/leave_job.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
