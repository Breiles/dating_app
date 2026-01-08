import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from datetime import datetime

# --------- CRIA O FLASK APP ---------
app = Flask(__name__)
app.secret_key = "sua_chave_secreta"

# --------- CONFIGURA UPLOADS ---------
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static/images")
CHAT_IMAGE_FOLDER = os.path.join("static", "chat-image")
GIFT_FOLDER = os.path.join("static", "gift")

for folder in [UPLOAD_FOLDER, CHAT_IMAGE_FOLDER, GIFT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

# --------- DATABASE ---------
DB_NAME = "dating_app.db"

# ----------------- Banco de Dados -----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
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

def add_type_column():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE messages ADD COLUMN type TEXT DEFAULT 'text'")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

# Inicializa DB
init_db()
add_type_column()

# ----------------- Usuários fictícios -----------------
def insert_test_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    test_users = [
        ("Alice", "1111", "F", "M", "Maputo", "Moçambique", "1234", "2000-05-10", "user1.jpg"),
        ("Bob", "2222", "M", "F", "Maputo", "Moçambique", "1234", "1998-07-15", "user2.jpg"),
        ("Carol", "3333", "F", "M", "Gaza", "Moçambique", "1234", "1995-12-20", "user3.jpg")
    ]
    for user in test_users:
        try:
            c.execute("INSERT INTO users (nome, numero, sexo, interesse, provincia, pais, senha, birth_date, image) VALUES (?,?,?,?,?,?,?,?,?)", user)
        except sqlite3.IntegrityError:
            continue
    conn.commit()
    conn.close()

insert_test_users()

# ----------------- Auxiliares -----------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_compatible_users(current_user):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE sexo=? AND id!=?", (current_user[4], current_user[0]))
    users = c.fetchall()
    conn.close()
    return users

def create_match(user1_id, user2_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO matches (user1_id, user2_id, timestamp) VALUES (?,?,?)",
              (user1_id, user2_id, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

# ----------------- Rotas -----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form["nome"]
        numero = request.form["numero"]
        sexo = request.form["sexo"]
        interesse = request.form["interesse"]
        provincia = request.form["provincia"]
        pais = request.form["pais"]
        senha = request.form["senha"]
        birth_date = request.form["birth_date"]

        image_file = request.files.get("image")
        filename = "default.jpg"
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(image_path)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            INSERT INTO users (nome, numero, sexo, interesse, provincia, pais, senha, birth_date, image)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (nome, numero, sexo, interesse, provincia, pais, senha, birth_date, filename))
        conn.commit()
        conn.close()

        flash(f"Bem-vindo, {nome}!")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        numero = request.form["numero"]
        senha = request.form["senha"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE numero=? AND senha=?", (numero, senha))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect(url_for("home"))
        else:
            flash("Número ou senha incorretos")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    current_user = get_user_by_id(session["user_id"])
    compatible_users = get_compatible_users(current_user)
    return render_template("home.html", users=compatible_users, current_user=current_user, datetime=datetime)

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = get_user_by_id(session["user_id"])
    return render_template("profile.html", user=user, datetime=datetime)

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = get_user_by_id(session["user_id"])

    if request.method == "POST":
        nome = request.form["nome"]
        numero = request.form["numero"]
        sexo = request.form["sexo"]
        interesse = request.form["interesse"]
        provincia = request.form["provincia"]
        pais = request.form["pais"]
        senha = request.form["senha"]
        birth_date = request.form["birth_date"]

        filename = user[9]
        image_file = request.files.get("image")
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(image_path)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            UPDATE users SET nome=?, numero=?, sexo=?, interesse=?, provincia=?, pais=?, senha=?, birth_date=?, image=?
            WHERE id=?
        """, (nome, numero, sexo, interesse, provincia, pais, senha, birth_date, filename, user[0]))
        conn.commit()
        conn.close()

        flash("Perfil atualizado com sucesso!")
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", user=user, datetime=datetime)

@app.route("/chat/<int:receiver_id>", methods=["GET", "POST"])
def chat(receiver_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    sender_id = session["user_id"]
    receiver = get_user_by_id(receiver_id)

    # Lista gifts
    gifts = os.listdir(GIFT_FOLDER)

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if request.method == "POST":
        content = request.form.get("content", "")
        image_file = request.files.get("image")
        gift_file = request.form.get("gift", "")

        msg_type = "text"
        msg_content = content

        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(CHAT_IMAGE_FOLDER, filename)
            image_file.save(image_path)
            msg_type = "image"
            msg_content = filename
        elif gift_file and gift_file != "":
            msg_type = "gift"
            msg_content = gift_file

        if msg_content:
            c.execute(
                "INSERT INTO messages (sender_id, receiver_id, content, timestamp, type) VALUES (?,?,?,?,?)",
                (sender_id, receiver_id, msg_content, datetime.utcnow().isoformat(), msg_type)
            )
            conn.commit()

    c.execute(
        "SELECT * FROM messages WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?) ORDER BY timestamp ASC",
        (sender_id, receiver_id, receiver_id, sender_id)
    )
    messages = c.fetchall()
    conn.close()

    return render_template("chat.html",
                           messages=messages,
                           receiver=receiver,
                           sender_id=sender_id,
                           gifts=gifts)

@app.route("/match/<int:user2_id>")
def match(user2_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user1_id = session["user_id"]
    create_match(user1_id, user2_id)
    flash("Você deu match com sucesso!")
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))

@app.route("/delete_account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Apaga mensagens do usuário
    c.execute("DELETE FROM messages WHERE sender_id=? OR receiver_id=?", (user_id, user_id))

    # Apaga matches do usuário
    c.execute("DELETE FROM matches WHERE user1_id=? OR user2_id=?", (user_id, user_id))

    # Apaga o usuário
    c.execute("DELETE FROM users WHERE id=?", (user_id,))

    conn.commit()
    conn.close()

    # Remove sessão
    session.pop("user_id", None)
    flash("Sua conta foi eliminada com sucesso!")
    return redirect(url_for("index"))

# ----------------- Inicia App -----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)