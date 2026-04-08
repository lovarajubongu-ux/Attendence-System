from flask import Flask, render_template, request, redirect, session, url_for
import pyodbc
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret123'

def connect_db():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=AttendanceDB;'
        'Trusted_Connection=yes;'
        'TrustServerCertificate=yes;'
        'Encrypt=no;'
    )

# -------- LOGIN --------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT username, password, student_id FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()

        # ✅ ADD HERE
        if user:
            session['user'] = user[0]
            session['student_id'] = user[2]

            if user[2] is None:
                return redirect('/dashboard')           # Admin
            else:
                return redirect('/student_dashboard')   # Student
        else:
            return "Invalid Login ❌"

    return render_template('login.html')

# -------- REGISTER --------
@app.route('/register', methods=['GET','POST'])
def register():
    error = None
    success = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        existing_user = c.fetchone()

        if existing_user:
            error = "Username already exists ❌"
        else:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            success = "Account created ✅ You can login now"
        conn.close()

    return render_template('register.html', error=error, success=success)

# -------- DASHBOARD --------
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # 🛡️ Security: If not logged in OR if user is a student, redirect to login
    if 'user' not in session or session.get('student_id') is not None:
        return redirect('/')

    conn = connect_db()
    cursor = conn.cursor()

    # ======= 1. HANDLE POST REQUESTS (Add Student / Attendance) =======
    if request.method == 'POST':

        # ➤ ADD STUDENT & AUTO-CREATE LOGIN
        if 'add_student_trigger' in request.form:
            name = request.form.get('new_student_name')
            dept = request.form.get('new_student_dept')
            year = request.form.get('new_student_year')

            if name and dept and year:
                # Insert Student
                cursor.execute("""
                    INSERT INTO students (student_name, department, [year])
                    OUTPUT INSERTED.student_id
                    VALUES (?, ?, ?)
                """, (name, dept, year))
                
                new_id = cursor.fetchone()[0]

                # Auto-create login for the student (Username: name, Pwd: 123)
                cursor.execute("""
                    INSERT INTO users (username, password, student_id)
                    VALUES (?, ?, ?)
                """, (name.lower().replace(" ", ""), '123', new_id))
                conn.commit()

        # ➤ BULK ATTENDANCE SUBMISSION
        elif 'bulk_attendance_trigger' in request.form:
            subject_id = request.form.get('subject_id')
            student_ids = request.form.getlist('student_ids')
            current_date = datetime.now().strftime("%Y-%m-%d")

            for s_id in student_ids:
                status = request.form.get(f'status_{s_id}')
                if status:
                    cursor.execute("""
                        INSERT INTO attendance (student_id, subject_id, [date], status)
                        VALUES (?, ?, ?, ?)
                    """, (s_id, subject_id, current_date, status))
            conn.commit()
            return redirect(url_for('dashboard'))

    # ======= 2. FETCH DATA FOR THE TABLES =======

    # 📊 Query 1: Students with Attendance Percentage (Fixed Syntax)
    cursor.execute("""
        SELECT 
            s.student_id, 
            s.student_name, 
            s.department, 
            s.year,
            COALESCE(
                (SUM(CASE WHEN a.status = 'Present' THEN 1.0 ELSE 0.0 END) / 
                NULLIF(COUNT(a.status), 0)) * 100, 
            0) AS AttendancePercentage
        FROM students s
        LEFT JOIN attendance a ON s.student_id = a.student_id
        GROUP BY s.student_id, s.student_name, s.department, s.year
        ORDER BY s.student_name
    """)
    all_students = cursor.fetchall()

    # Group students by Year for the UI
    students_by_year = {}
    for s in all_students:
        year_key = f"Year {s[3]}"
        if year_key not in students_by_year:
            students_by_year[year_key] = []
        students_by_year[year_key].append(s)

    # 📚 Query 2: Subjects List for dropdown
    cursor.execute("SELECT subject_id, subject_name FROM subjects")
    subjects_list = cursor.fetchall()

    # 🕒 Query 3: Recent Attendance History
    cursor.execute("""
        SELECT TOP 10 s.student_name, sub.subject_name, a.date, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        JOIN subjects sub ON a.subject_id = sub.subject_id
        ORDER BY a.date DESC
    """)
    history = cursor.fetchall()

    conn.close()

    # ======= 3. RENDER THE DASHBOARD =======
    return render_template(
        'dashboard.html',
        year_groups=students_by_year,
        subjects=subjects_list,
        history=history,
        username=session['user']
    )
# -------- STUDENT DASHBOARD --------
@app.route('/student_dashboard')
def student_dashboard():
    if 'student_id' not in session or session.get('student_id') is None:
        return redirect('/')

    student_id = session['student_id']

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            s.student_name,

            COALESCE(
                (CAST(COUNT(CASE WHEN a.status='Present' THEN 1 END) AS FLOAT)
                / NULLIF(COUNT(a.student_id), 0)) * 100,
            0) AS percentage

        FROM students s
        LEFT JOIN attendance a ON s.student_id = a.student_id
        WHERE s.student_id = ?
        GROUP BY s.student_name
    """, (student_id,))

    data = cursor.fetchone()

    conn.close()

    # ✅ HANDLE EMPTY DATA
    if data is None:
        data = ("No Name", 0)

    return render_template('student_dashboard.html', data=data)

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('student_id', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)