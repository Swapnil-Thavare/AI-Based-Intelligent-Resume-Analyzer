from flask import Flask, render_template, request, redirect, session
from utils.nlp import calculate_score
import datetime
import mysql.connector
import fitz

# =========================
# DATABASE CONNECTION
# =========================
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1809",
    database="resume_analyzer"
)

# =========================
# FLASK APP
# =========================
app = Flask(__name__)
app.secret_key = "secret123"


# =========================
# PDF TEXT EXTRACTION
# =========================
def extract_text_from_pdf(file):

    text = ""

    pdf = fitz.open(stream=file.read(), filetype="pdf")

    for page in pdf:
        text += page.get_text()

    return text


# =========================
# LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')

        cursor = db.cursor(buffered=True)

        cursor.execute(
            """
            SELECT username, email
            FROM users
            WHERE username=%s AND password=%s
            """,
            (username, password)
        )

        user = cursor.fetchone()

        cursor.close()

        if user:

            session['user'] = user[0]
            session['email'] = user[1]

            return redirect('/dashboard')

        else:
            return render_template(
                "login.html",
                error="Invalid username or password"
            )

    return render_template("login.html")


# =========================
# REGISTER
# =========================
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if password != confirm:

            return render_template(
                'register.html',
                error="Passwords do not match",
                username=username,
                email=email
            )

        cursor = db.cursor(buffered=True)

        # CHECK DUPLICATE EMAIL
        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()

            return render_template(
                'register.html',
                error="Email already registered",
                username=username
            )

        # INSERT USER
        cursor.execute(
            """
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s)
            """,
            (username, email, password)
        )

        db.commit()

        cursor.close()

        return render_template(
            'register.html',
            success="Registered successfully! Please login."
        )

    return render_template('register.html')


# =========================
# DASHBOARD
# =========================
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():

    if 'user' not in session:
        return redirect('/')

    cursor = db.cursor(buffered=True)

    cursor.execute("""
        SELECT id, job_desc, resume_name, score, created_at
        FROM history
        WHERE username=%s
        ORDER BY id DESC
    """, (session['user'],))

    history = cursor.fetchall()

    cursor.close()

    return render_template(
        "dashboard.html",
        history=history,
        user=session['user']
    )


# =========================
# ANALYZE RESUME
# =========================
@app.route('/analyze', methods=['POST'])
def analyze():

    if 'user' not in session:
        return redirect('/')

    jd = request.form.get('job_desc')
    file = request.files.get('resume')

    # VALIDATION
    if not jd or jd.strip() == "" or not file or file.filename == "":

        return render_template(
            "dashboard.html",
            error="Job Description and Resume are required!"
        )

    # =========================
    # EXTRACT PDF TEXT
    # =========================
    try:

        resume_text = extract_text_from_pdf(file)

    except Exception as e:

        return f"PDF Reading Error: {str(e)}"

    # DEBUG CHECK
    print("\n================ RESUME TEXT ================\n")
    print(resume_text[:1000])

    # =========================
    # NLP SCORE
    # =========================
    score, suggestions = calculate_score(jd, resume_text)

    score = float(score)

    # SAFETY
    score = max(0, min(score, 100))

    # =========================
    # SAVE HISTORY
    # =========================
    cursor = db.cursor(buffered=True)

    cursor.execute("""
        INSERT INTO history
        (
            username,
            job_desc,
            resume_text,
            resume_name,
            score,
            suggestions,
            created_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        session['user'],
        jd,
        resume_text,
        file.filename,
        score,
        "\n".join(suggestions),
        datetime.datetime.now()
    ))

    db.commit()

    cursor.close()

    return render_template(
        "result.html",
        score=score,
        suggestions=suggestions
    )


# =========================
# LOGOUT
# =========================
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')


# =========================
# RUN APP
# =========================
if __name__ == '__main__':

    app.run(debug=True)