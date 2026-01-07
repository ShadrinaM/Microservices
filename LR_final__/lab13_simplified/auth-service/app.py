from flask import Flask, request, jsonify, render_template_string, redirect, send_from_directory
import sqlite3, os, hmac, hashlib, base64, time

app = Flask(__name__, static_folder='static', template_folder='templates')
DB = 'users.db'
SECRET = os.environ.get('APP_SECRET', 'dev-secret')  # from K8s Secret
LOGIN_TITLE = os.environ.get('LOGIN_TITLE', 'Вход')
REGISTER_TITLE = os.environ.get('REGISTER_TITLE', 'Регистрация')
WELCOME_MESSAGE = os.environ.get('WELCOME_MESSAGE', 'Добро пожаловать')

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, state TEXT)''')
    conn.commit()
    conn.close()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def make_token(username, exp=3600):
    payload = f"{username}|{int(time.time())+exp}"
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode()
    return token

def verify_token(token):
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        username, exp, sig = raw.split('|')
        payload = f"{username}|{exp}"
        expected = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig): 
            return None
        if int(exp) < int(time.time()):
            return None
        return username
    except Exception:
        return None

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/login', methods=['GET'])
def login_page():
    return app.send_static_file('login.html')

@app.route('/register', methods=['GET'])
def register_page():
    return app.send_static_file('register.html')

@app.route('/ui-config', methods=['GET'])
def ui_config():
    return jsonify({
        "LOGIN_TITLE": LOGIN_TITLE,
        "REGISTER_TITLE": REGISTER_TITLE,
        "WELCOME_MESSAGE": WELCOME_MESSAGE
    })

@app.route('/register', methods=['POST'])
def register():
    u = request.form.get('username')
    p = request.form.get('password')
    if not u or not p:
        return "missing", 400
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users(username,password,state) VALUES(?,?,?)", (u, hash_pw(p), 'active'))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "exists", 400
    conn.close()
    token = make_token(u)
    return redirect(f"/profile?token={token}")

@app.route('/login', methods=['POST'])
def login():
    u = request.form.get('username')
    p = request.form.get('password')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT password,state FROM users WHERE username=?", (u,))
    row = c.fetchone()
    conn.close()
    if not row:
        return "no user", 400
    hashed, state = row
    if state != 'active':
        return "inactive", 403
    if hash_pw(p) != hashed:
        return "bad credentials", 401
    token = make_token(u)
    return redirect(f"/profile?token={token}")

@app.route('/profile')
def profile_redirect():
    token = request.args.get('token')
    if not token:
        return redirect('/')
    return redirect(f"http://profile-service:5001/user?token={token}")

@app.route('/token/verify', methods=['POST'])
def token_verify():
    data = request.json or {}
    token = data.get('token')
    user = verify_token(token)
    if not user:
        return jsonify({"ok": False}), 401
    return jsonify({"ok": True, "username": user})

@app.route('/health/live')
def live():
    return "ok", 200

@app.route('/health/ready')
def ready():
    return "ready", 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)