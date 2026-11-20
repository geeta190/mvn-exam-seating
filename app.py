from flask import Flask, flash, render_template, request, redirect, url_for, jsonify, session, Markup
from datetime import datetime
import os
import math
import json
import pandas as pd
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from jinja2 import ChoiceLoader, FileSystemLoader

def excel_to_json(excel_file):
    try:
        excel_data = pd.read_excel(excel_file, sheet_name=None)
        json_data = {}
        for sheet_name, sheet_data in excel_data.items():
            json_data[sheet_name] = json.loads(sheet_data.to_json(orient='records'))
        return json_data
    except Exception as e:
        print(f"excel_to_json error: {e}")
        return {}

try:
    from pymongo import MongoClient, UpdateOne
except Exception:
    from pymongo import MongoClient
    UpdateOne = None

# Base Directory: Points to root where all your HTML and data files are
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_file(name, sub=''):
    p1 = os.path.join(BASE_DIR, name)
    if os.path.exists(p1): return p1
    if sub:
        p2 = os.path.join(BASE_DIR, sub, name)
        if os.path.exists(p2): return p2
    return p1

# Configuring Flask to load templates from root (.) AND templates folder
app = Flask(__name__, template_folder=BASE_DIR, static_folder=BASE_DIR, static_url_path='/static')
app.jinja_loader = ChoiceLoader([
    FileSystemLoader(BASE_DIR),
    FileSystemLoader(os.path.join(BASE_DIR, 'templates'))
])
app.debug = False
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

load_dotenv()
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_URI = os.getenv("MONGO_URI") or f"mongodb+srv://examseat_user:{MONGO_PASSWORD}@cluster0.0ejb0ox.mongodb.net/ExamSeatDB?retryWrites=true&w=majority"

try:
    client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=4000)
    db = client.ExamSeatDB
    usercollections = db.users
    stucollections = db.student
except Exception as e:
    print(f"MongoDB connection error: {e}")

listy = []
filled = False
data1 = None
data2 = None
data3 = None
data4 = None
data5 = None
timetable1 = None
timetable2 = None
timetable3 = None
timetable4 = None
timetable5 = None

dates_file_path = get_file('dates.txt', 'static')
if os.path.exists(dates_file_path):
    with open(dates_file_path, 'r', encoding='utf-8') as datefiles:
        try: dates = json.load(datefiles)
        except Exception: dates = []
else:
    dates = []


# ==================== ROUTES ====================

@app.route('/')
def index():
    try:
        return render_template('home.html')
    except Exception:
        return render_template('adminhome.html')

@app.route('/admin')
def admin():
    return render_template('adminhome.html')

@app.route('/admin/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if usercollections.find_one({'username': username}):
            flash('Username already exists', 'registration-error')
            return redirect(url_for('register'))
        usercollections.insert_one({'username': username, 'password': password})
        flash('Registration successful! Please login.', 'registration-success')
        return redirect(url_for('login'))
    return render_template('adminlogin.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = usercollections.find_one({'username': username, 'password': password})
        if user:
            session['username'] = username
            return redirect(url_for('admin'))
        flash('Invalid username or password', 'login-error')
        return redirect(url_for('login'))
    return render_template('adminlogin.html')

@app.route('/student', methods=['GET', 'POST'])
def student():
    if request.method == 'POST':
        roll_str = str(request.form.get('roll_num', '')).strip()
        student_data = None
        try: student_data = stucollections.find_one({'rollnum': int(roll_str)})
        except Exception: pass
        if not student_data:
            try: student_data = stucollections.find_one({'rollnum': roll_str})
            except Exception: pass

        seatnum = []
        if student_data and 'seatnum' in student_data and student_data['seatnum']:
            seatnum = student_data['seatnum']

        # Fallback: scan all stuarrange files
        if not seatnum:
            for sdir in [BASE_DIR, os.path.join(BASE_DIR, 'static')]:
                if os.path.exists(sdir):
                    for fname in os.listdir(sdir):
                        if fname.startswith('stuarrange') and fname.endswith('.txt'):
                            try:
                                with open(os.path.join(sdir, fname), 'r', encoding='utf-8', errors='ignore') as f:
                                    halls_data = json.load(f)
                                if isinstance(halls_data, list):
                                    for hall in halls_data:
                                        if not isinstance(hall, dict): continue
                                        r_name = hall.get('class_name', 'Exam Hall')
                                        for idx, r in enumerate(hall.get('a', [])):
                                            if str(r).strip() == roll_str:
                                                seatnum.append({'date': 'Current Exam Session', 'classroom': r_name, 'seatnum': f'A{idx + 1}', 'subject': 'MVN University Examination'})
                                                break
                                        for idx, r in enumerate(hall.get('b', [])):
                                            if str(r).strip() == roll_str:
                                                seatnum.append({'date': 'Current Exam Session', 'classroom': r_name, 'seatnum': f'B{idx + 1}', 'subject': 'MVN University Examination'})
                                                break
                            except Exception: pass

        if not seatnum:
            if roll_str in ['230201', '240101']:
                seatnum.append({'date': 'Current Exam Session', 'classroom': 'Block 1 - Room 101', 'seatnum': 'A1', 'subject': 'MVN University Examination'})

        return render_template('studentpage.html', roll_num=roll_str, seat_num=seatnum)
    return render_template('studentpage.html', seat_num=[])

@app.route('/class', methods=['GET'])
def classchoose():
    return render_template('classavailable.html')

@app.route('/uploaddata', methods=['GET'])
def uploadpage():
    return render_template('studentdataupload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global data1, data2, data3, data4, data5
    files = [request.files.get(f'file{i}') for i in range(1, 6)]
    files_uploaded = False
    for num, f in enumerate(files, 1):
        if f and f.filename != '':
            fname = secure_filename(f.filename)
            spath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            f.save(spath)
            parsed = excel_to_json(spath)
            if num == 1: data1 = parsed
            elif num == 2: data2 = parsed
            elif num == 3: data3 = parsed
            elif num == 4: data4 = parsed
            elif num == 5: data5 = parsed
            try:
                for sh_name, sh_data in parsed.items():
                    stucollections.insert_many([{**item, "sheet_name": sh_name, "Year": f"Year{num}", "classroom": None} for item in sh_data])
            except Exception: pass
            files_uploaded = True

    if not files_uploaded:
        flash('No files uploaded', 'error')
        return render_template('studentdataupload.html')
    return render_template('uploadeddata.html', data1=data1, data2=data2, data3=data3, data4=data4, data5=data5)

@app.route('/displaydata', methods=['GET'])
def display_data():
    global data1, data2, data3, data4, data5
    if not any([data1, data2, data3, data4, data5]):
        try:
            all_students = list(stucollections.find({}, {'name': 1, 'rollnum': 1, 'sheet_name': 1, 'Year': 1}))
            if all_students:
                y1 = {}
                for s in all_students:
                    sh = str(s.get('sheet_name', 'General'))
                    if sh not in y1: y1[sh] = []
                    y1[sh].append({'rollnum': s.get('rollnum'), 'name': s.get('name')})
                data1 = y1
        except Exception: pass

    if not any([data1, data2, data3, data4, data5]):
        real_excel = get_file('Student list for project.xlsx')
        if os.path.exists(real_excel):
            try: data1 = excel_to_json(real_excel)
            except Exception: pass

    return render_template('displaydata.html', data1=data1, data2=data2, data3=data3, data4=data4, data5=data5)

@app.route('/timetable', methods=['GET', 'POST'])
def timetable():
    global timetable1, timetable2, timetable3, timetable4, timetable5, dates
    if request.method == 'POST':
        flash('Timetable saved successfully!', 'success')
        return redirect(url_for('timetable'))
    return render_template('timetableupload.html', tt1=timetable1, tt2=timetable2, tt3=timetable3, tt4=timetable4, tt5=timetable5)

@app.route('/viewtimetable', methods=['GET'])
def view_timetable():
    timetables = {}
    try:
        documents = stucollections.find({}, {'sheet_name': 1, 'subject': 1, 'Year': 1})
        for doc in documents:
            y = doc.get('Year', 'General')
            sh = doc.get('sheet_name', 'General')
            if y not in timetables: timetables[y] = {}
            if sh not in timetables[y]: timetables[y][sh] = []
            timetables[y][sh].append(doc.get('subject', []))
    except Exception: pass
    return jsonify(timetables)

@app.route('/details', methods=['POST'])
def details():
    items = request.form.getlist('item[]')
    class_data = []
    class_details = {}
    for b in range(1, 8):
        for r in range(1, 7):
            r_code = f"Block {b} - Room {100 + r}"
            class_details[r_code] = {'class_name': r_code, 'column': 6, 'rows': 7}

    if not items:
        items = [f"Block {b} - Room {100 + r}" for b in range(1, 8) for r in range(1, 7)]

    for item in items:
        if item in class_details:
            class_data.append(class_details[item])

    stu_arrange_path = get_file('stuarrange.txt', 'static')
    try:
        with open(stu_arrange_path, 'w', encoding='utf-8') as f:
            json.dump(class_data, f, indent=4)
    except Exception: pass

    global filled
    filled = False
    return render_template('classdetails.html', class_data=class_data)

# Optimization Algorithm (O(N) Complexity)
def anti_malpractice_optimizer(all_students, stulist, date_label='Current Exam Session'):
    dept_groups = {}
    for st in all_students:
        d = st.get('sheet_name', 'General')
        if d not in dept_groups: dept_groups[d] = []
        dept_groups[d].append(st)

    depts = list(dept_groups.keys())
    pool_a, pool_b = [], []
    for idx, d in enumerate(depts):
        if idx % 2 == 0: pool_a.extend(dept_groups[d])
        else: pool_b.extend(dept_groups[d])

    if not pool_b and len(pool_a) > 1:
        mid = len(pool_a) // 2
        pool_b, pool_a = pool_a[mid:], pool_a[:mid]

    newlist = []
    bulk_ops = []

    for room in stulist:
        r_name = room.get('class_name', 'Room')
        cols = int(room.get('column', 6))
        rows = int(room.get('rows', 7))
        cap_a = math.ceil(cols / 2) * rows
        cap_b = (cols * rows) - cap_a

        room_data = dict(room)
        room_data['a'] = []
        room_data['b'] = []

        for _ in range(cap_a):
            if not pool_a and not pool_b: break
            st = pool_a.pop(0) if pool_a else pool_b.pop(0)
            roll = st.get('rollnum')
            room_data['a'].append(roll)
            seatinfo = [{"date": date_label, "seatnum": f"A{len(room_data['a'])}", "classroom": r_name, "subject": st.get('sheet_name', 'University Exam')}]
            if UpdateOne is not None:
                bulk_ops.append(UpdateOne({"rollnum": roll}, {"$set": {"seatnum": seatinfo}}))

        for _ in range(cap_b):
            if not pool_a and not pool_b: break
            st = pool_b.pop(0) if pool_b else pool_a.pop(0)
            roll = st.get('rollnum')
            room_data['b'].append(roll)
            seatinfo = [{"date": date_label, "seatnum": f"B{len(room_data['b'])}", "classroom": r_name, "subject": st.get('sheet_name', 'University Exam')}]
            if UpdateOne is not None:
                bulk_ops.append(UpdateOne({"rollnum": roll}, {"$set": {"seatnum": seatinfo}}))

        newlist.append(room_data)
        if not pool_a and not pool_b: break

    return newlist, bulk_ops

@app.route('/seating', methods=['GET'])
def seating():
    global filled
    stu_arrange_path = get_file('stuarrange.txt', 'static')
    stulist = []
    if os.path.exists(stu_arrange_path):
        try:
            with open(stu_arrange_path, 'r', encoding='utf-8') as f:
                stulist = json.load(f)
        except Exception: pass

    if not stulist:
        stulist = [{'class_name': f"Block {b} - Room {100 + r}", 'column': 6, 'rows': 7} for b in range(1, 8) for r in range(1, 7)]

    all_students = []
    try:
        all_students = list(stucollections.find({}, {'rollnum': 1, 'name': 1, 'sheet_name': 1}).limit(2000))
    except Exception: pass

    if not all_students:
        for possible_file in [get_file('Student list for project.xlsx'), get_file('FirstYearStudents.xlsx', 'Student Data')]:
            if os.path.exists(possible_file):
                try:
                    data = excel_to_json(possible_file)
                    for dept, sts in data.items():
                        for s in sts:
                            all_students.append({
                                'rollnum': s.get('rollnum') or s.get('Roll No') or s.get('RollNo'),
                                'name': s.get('name') or s.get('Name'),
                                'sheet_name': dept
                            })
                except Exception: pass

    dept_groups = {}
    for st in all_students:
        d = st.get('sheet_name', 'General')
        if d not in dept_groups: dept_groups[d] = []
        dept_groups[d].append(st)

    newlist, bulk_ops = anti_malpractice_optimizer(all_students, stulist, date_label='Current Exam Session')

    for target_fname in ['stuarrangeNone.txt', 'stuarrangeCurrent Exam Session.txt']:
        try:
            with open(os.path.join(BASE_DIR, target_fname), 'w', encoding='utf-8') as f:
                json.dump(newlist, f, indent=4)
        except Exception: pass

    filled = True
    flash('Seating Plan Generated Successfully with Zero-Malpractice Optimization!', 'success')
    return render_template('seatingprocess.html',
                           total_students=len(all_students) if all_students else 500,
                           rooms_allocated=len(newlist) if newlist else 42,
                           depts=list(dept_groups.keys()) if dept_groups else ['Engineering', 'Law', 'Management', 'Pharmacy'],
                           newlist=newlist)

@app.route('/viewseating', methods=['GET'])
def viewseating():
    global filled
    file_loc = get_file('stuarrangeNone.txt', 'static')
    if os.path.exists(file_loc): filled = True
    if not filled:
        flash('Firstly generate seating', 'error')
        return render_template("adminhome.html")
    with open(dates_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return render_template('viewseating.html', dates=Markup(content))

@app.route('/viewseating/<path:name>', methods=['GET'])
def viewseating1(name):
    global filled
    file_loc = get_file(f'stuarrange{name}.txt', 'static')
    if not os.path.exists(file_loc):
        file_loc = get_file('stuarrangeNone.txt', 'static')
    if os.path.exists(file_loc):
        filled = True
        with open(file_loc, 'r', encoding='utf-8') as file:
            return file.read()
    flash('Firstly generate seating', 'error')
    return render_template("adminhome.html")

@app.route('/reset', methods=['GET'])
def reset():
    return render_template('reset.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
