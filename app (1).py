import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "sua_chave_secreta"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "dating_app.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/images")
CHAT_IMAGE_FOLDER = os.path.join(BASE_DIR, "static/images")
GIFT_FOLDER = os.path.join(BASE_DIR, "static/images")

for folder in [UPLOAD_FOLDER, CHAT_IMAGE_FOLDER, GIFT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        numero TEXT UNIQUE,
        sexo TEXT,
        interesse TEXT,
        provincia TEXT,
        pais TEXT,
        senha TEXT,
        birth_date TEXT,
        image TEXT DEFAULT 'default.jpg'
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        content TEXT,
        timestamp TEXT,
        type TEXT DEFAULT 'text'
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1_id INTEGER,
        user2_id INTEGER,
        timestamp TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_by_id(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_compatible_users(current_user):
    if not current_user:
        return []
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM users WHERE sexo=? AND id!=?",
        (current_user[4], current_user[0])
    )
    users = c.fetchall()
    conn.close()
    return users

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        numero = request.form["numero"]
        senha = request.form["senha"]
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE numero=? AND senha=?", (numero, senha))
        user = c.fetchone()
        conn.close()
        if user:
            session["user_id"] = user[0]
            return redirect(url_for("home"))
        flash("Credenciais inválidas")
    return render_template("login.html")

@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = get_user_by_id(session["user_id"])
    users = get_compatible_users(user)
    return render_template("home.html", users=users, current_user=user)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)