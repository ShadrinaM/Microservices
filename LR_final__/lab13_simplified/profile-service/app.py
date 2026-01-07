from flask import Flask, request, jsonify
import sqlite3, os, requests

app = Flask(__name__)
DB = 'profiles.db'
AUTH_URL = os.environ.get('AUTH_URL', 'http://auth-service:5000')

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, full_name TEXT, bio TEXT)''')
    conn.commit()
    conn.close()

def verify_token(token):
    try:
        r = requests.post(f"{AUTH_URL}/token/verify", json={"token": token}, timeout=3)
        if r.status_code == 200:
            return r.json().get('username')
    except Exception:
        return None
    return None

@app.route('/user', methods=['GET'])
def get_user():
    token = request.args.get('token') or request.headers.get('Authorization')
    if not token:
        return "no token", 401
    user = verify_token(token)
    if not user:
        return "invalid", 401
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT full_name,bio FROM profiles WHERE username=?", (user,))
    row = c.fetchone()
    if not row:
        # create minimal profile
        c.execute("INSERT OR IGNORE INTO profiles(username,full_name,bio) VALUES(?,?,?)", (user, user, ""))
        conn.commit()
        profile = {"username": user, "full_name": user, "bio": ""}
    else:
        profile = {"username": user, "full_name": row[0], "bio": row[1]}
    conn.close()
    return jsonify(profile)

@app.route('/user', methods=['POST'])
def update_user():
    token = request.args.get('token') or request.headers.get('Authorization')
    user = verify_token(token)
    if not user:
        return "invalid", 401
    data = request.json or {}
    full = data.get('full_name','')
    bio = data.get('bio','')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO profiles(username,full_name,bio) VALUES(?,?,?)", (user, full, bio))
    conn.commit()
    conn.close()
    return "ok", 200

@app.route('/health/live')
def live():
    return "ok", 200

@app.route('/health/ready')
def ready():
    return "ready", 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001)
