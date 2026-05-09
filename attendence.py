from flask import Flask, render_template, request, redirect, session, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret123'

# ==========================================
# 🛡️ MOCK DATABASE (Simulating SQL Tables)
# ==========================================
users = [
    {"usernarne": "admin", "password": "123", "student_id": None},
    {"usernarne": "raju", "password": "123", "student_id": 1}
]

students = [
    {"student_id": 1, "student_name": "Raju", "department": "CSE", "year": 1},
    {"student_id": 2, "student_name": "Satish", "department": "CSE", "year": 1},
    {"student_id": 3, "student_name": "Arun", "department": "ECE", "year": 2},
]

subjects = [
    {"subject_id": 1, "subject_name": "Mathematics"},
    {"subject_id": 2, "subject_name": "Physics"}
]

attendance_records = [] # Stores: {"student_id": 1, "subject_id": 1, "date": "2026-05-09", "status": "Present"}

# ==========================================
# 🏠 ROUTES
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u_input = request.form['username']
        p_input = request.form['password']

        # Simulate: SELECT * FROM users WHERE usernarne=? AND password=?
        user = next((u for u in users if u["usernarne"] == u_input and u["password"] == p_input), None)

        if user:
            session['user'] = user["usernarne"]
            session['student_id'] = user["student_id"]
            
            if user["student_id"] is None:
                return redirect('/dashboard')
            return redirect('/student_dashboard')
        return "Invalid Login ❌"

    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session or session.get('student_id') is not None:
        return redirect('/')

    if request.method == 'POST':
        # ➤ ADD NEW SUBJECT
        if 'add_subject_trigger' in request.form:
            sub_name = request.form.get('new_subject_name')
            if sub_name:
                new_sub_id = len(subjects) + 1
                subjects.append({"subject_id": new_sub_id, "subject_name": sub_name})
        # Simulate: ADD STUDENT
        if 'add_student_trigger' in request.form:
            new_id = len(students) + 1
            name = request.form.get('new_student_name')
            students.append({
                "student_id": new_id,
                "student_name": name,
                "department": request.form.get('new_student_dept'),
                "year": int(request.form.get('new_student_year'))
            })
            users.append({"usernarne": name.lower(), "password": "123", "student_id": new_id})

        # Simulate: BULK ATTENDANCE
        elif 'bulk_attendance_trigger' in request.form:
            sub_id = int(request.form.get('subject_id'))
            s_ids = request.form.getlist('student_ids')
            for s_id in s_ids:
                status = request.form.get(f'status_{s_id}')
                attendance_records.append({
                    "student_id": int(s_id),
                    "subject_id": sub_id,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "status": status
                })
            return redirect('/dashboard')

    # Prepare data for UI (Grouping by Year)
    year_groups = {}
    for s in students:
        # Calculate Percentage manually
        relevant = [a for a in attendance_records if a["student_id"] == s["student_id"]]
        presents = [a for a in relevant if a["status"] == "Present"]
        percent = (len(presents) / len(relevant) * 100) if relevant else 0
        
        # Format: (id, name, dept, year, percent)
        s_data = (s["student_id"], s["student_name"], s["department"], s["year"], percent)
        
        year_label = f"Year {s['year']}"
        if year_label not in year_groups: year_groups[year_label] = []
        year_groups[year_label].append(s_data)

    return render_template('dashboard.html', 
                           year_groups=year_groups, 
                           subjects=[(sub["subject_id"], sub["subject_name"]) for sub in subjects],
                           history=[], # History is simplified for mock
                           username=session['user'])

@app.route('/student_dashboard')
def student_dashboard():
    s_id = session.get('student_id')
    student = next((s for s in students if s["student_id"] == s_id), None)
    
    relevant = [a for a in attendance_records if a["student_id"] == s_id]
    presents = [a for a in relevant if a["status"] == "Present"]
    percent = (len(presents) / len(relevant) * 100) if relevant else 0
    
    data = (student["student_name"] if student else "Guest", percent)
    return render_template('student_dashboard.html', data=data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)