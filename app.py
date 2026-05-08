from flask import Flask, render_template, request, redirect, session
from utils.nlp import calculate_score
import datetime
import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1809",
    database="resume_analyzer"
)

app = Flask(__name__)
app.secret_key = "secret123"


@app.route('/login', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        cursor = db.cursor()

        cursor.execute(
            "SELECT username, email FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()

        if user:
            session['user'] = user[0]
            session['email'] = user[1]
            return redirect('/dashboard')
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if password != confirm:
            return render_template('register.html', error="Passwords do not match", username=username, email=email)

        cursor = db.cursor()

        # Check duplicate email
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            return render_template('register.html', error="Email already registered", username=username)

        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                       (username, email, password))
        db.commit()

        return render_template('register.html', success="Registered successfully! Please login.")

    return render_template('register.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/')

    cursor = db.cursor()

    cursor.execute("SELECT id, job_desc, resume_name, score, created_at FROM history WHERE username=%s ORDER BY id DESC",
                   (session['user'],))
    history = cursor.fetchall()

    return render_template("dashboard.html", history=history, user=session['user'])


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'user' not in session:
        return redirect('/')

    jd = request.form.get('job_desc')
    file = request.files.get('resume')

    if not jd or jd.strip() == "" or not file or file.filename == "":
        return "Job Description and Resume are required!"

    resume_text = file.read().decode(errors='ignore')
    score, suggestions = calculate_score(jd, resume_text)
    score = float(score)

    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO history (username, job_desc, resume_text, resume_name, score, suggestions, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        session['user'],
        jd,
        resume_text,
        file.filename,
        float(score),
        "\n".join(suggestions),
        datetime.datetime.now()
    ))

    db.commit()

    cursor = db.cursor()
    cursor.execute("SELECT email FROM users WHERE username=%s", (session['user'],))
    email = cursor.fetchone()[0]
    return render_template("result.html", score=score, suggestions=suggestions)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
    

if __name__ == '__main__':
    app.run(debug=True)
