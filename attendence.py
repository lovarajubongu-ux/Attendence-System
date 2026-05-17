from flask import Flask, render_template, request, redirect, session, url_for
from datetime import datetime
import json
import os
import platform
import threading
import webbrowser

app = Flask(__name__)
app.secret_key = 'secret123'

DB_FILE = 'database.json'

def load_db():
    if not os.path.exists(DB_FILE):
        default_data = {
            "users": [
                {"usernarne": "admin", "password": "123", "student_id": None},
                {"usernarne": "raju", "password": "123", "student_id": 1}
            ],
            "students": [
                {"student_id": 1, "student_name": "Raju", "department": "CSE", "year": 1},
                {"student_id": 2, "student_name": "Satish", "department": "CSE", "year": 1},
                {"student_id": 3, "student_name": "Arun", "department": "ECE", "year": 2},
            ],
            "subjects": [
                {"subject_id": 1, "subject_name": "Mathematics"},
                {"subject_id": 2, "subject_name": "Physics"}
            ],
            "departments": ["CSE", "ECE", "MECH", "IT"],
            "years": [1, 2, 3, 4],
            "attendance_records": []
        }
        save_db(default_data)
        return default_data
    
    with open(DB_FILE, 'r') as f:
        data = json.load(f)
        # Ensure new lists exist if upgrading an older json file
        if "departments" not in data: data["departments"] = ["CSE", "ECE", "MECH", "IT"]
        if "years" not in data: data["years"] = [1, 2, 3, 4]
        return data

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u_input = request.form['username']
        p_input = request.form['password']
        db = load_db()
        user = next((u for u in db["users"] if u["usernarne"] == u_input and u["password"] == p_input), None)
        if user:
            session['user'] = user["usernarne"]
            session['student_id'] = user["student_id"]
            if user["student_id"] is None: return redirect('/dashboard')
            return redirect('/student_dashboard')
        return "Invalid Login ❌"
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session or session.get('student_id') is not None:
        return redirect('/')

    db = load_db()

    if request.method == 'POST':
        # 1. ADD STUDENT
        if 'add_student_trigger' in request.form:
            new_id = max([s["student_id"] for s in db["students"]], default=0) + 1
            name = request.form.get('new_student_name')
            db["students"].append({
                "student_id": new_id,
                "student_name": name,
                "department": request.form.get('new_student_dept'),
                "year": int(request.form.get('new_student_year'))
            })
            db["users"].append({"usernarne": name.lower().replace(" ", ""), "password": "123", "student_id": new_id})
            save_db(db)

        # 2. ADD SUBJECT
        elif 'add_subject_trigger' in request.form:
            sub_name = request.form.get('new_subject_name')
            if sub_name:
                new_sub_id = max([sub["subject_id"] for sub in db["subjects"]], default=0) + 1
                db["subjects"].append({"subject_id": new_sub_id, "subject_name": sub_name})
                save_db(db)

        # 3. ADD DEPARTMENT
        elif 'add_dept_trigger' in request.form:
            dept_name = request.form.get('new_dept_name').upper().strip()
            if dept_name and dept_name not in db["departments"]:
                db["departments"].append(dept_name)
                save_db(db)

        # 4. ADD YEAR
        elif 'add_year_trigger' in request.form:
            year_num = request.form.get('new_year_num')
            if year_num and int(year_num) not in db["years"]:
                db["years"].append(int(year_num))
                db["years"].sort()
                save_db(db)

        # 5. BULK ATTENDANCE
        elif 'bulk_attendance_trigger' in request.form:
            sub_id = int(request.form.get('subject_id'))
            s_ids = request.form.getlist('student_ids')
            for s_id in s_ids:
                status = request.form.get(f'status_{s_id}')
                db["attendance_records"].append({
                    "student_id": int(s_id),
                    "subject_id": sub_id,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "status": status
                })
            save_db(db)
            return redirect('/dashboard')

    # Prepare interface UI data
    year_groups = {}
    for s in db["students"]:
        relevant = [a for a in db["attendance_records"] if a["student_id"] == s["student_id"]]
        presents = [a for a in relevant if a["status"] == "Present"]
        percent = (len(presents) / len(relevant) * 100) if relevant else 0
        
        s_data = (s["student_id"], s["student_name"], s["department"], s["year"], percent)
        year_label = f"Year {s['year']}"
        if year_label not in year_groups: year_groups[year_label] = []
        year_groups[year_label].append(s_data)

    return render_template(
        'dashboard.html', 
        year_groups=year_groups, 
        subjects=[(sub["subject_id"], sub["subject_name"]) for sub in db["subjects"]],
        departments=db["departments"],
        years=db["years"],
        username=session['user']
    )

@app.route('/student_dashboard')
def student_dashboard():
    s_id = session.get('student_id')
    if s_id is None: return redirect('/')
    db = load_db()
    student = next((s for s in db["students"] if s["student_id"] == s_id), None)
    relevant = [a for a in db["attendance_records"] if a["student_id"] == s_id]
    presents = [a for a in relevant if a["status"] == "Present"]
    percent = (len(presents) / len(relevant) * 100) if relevant else 0
    data = (student["student_name"] if student else "Student", percent)
    return render_template('student_dashboard.html', data=data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def open_in_edge(url):
    if platform.system() == 'Windows':
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]
        edge_exe = next((p for p in edge_paths if os.path.exists(p)), None)
        if edge_exe:
            webbrowser.register('edge', None, webbrowser.BackgroundBrowser(edge_exe))
            webbrowser.get('edge').open(url)
            return
    webbrowser.open(url)


if __name__ == '__main__':
    port = 5000
    url = f'http://127.0.0.1:{port}'
    threading.Timer(1.0, lambda: open_in_edge(url)).start()
    app.run(debug=True, port=port)
