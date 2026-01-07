from flask import Flask, request, jsonify
import jwt
import datetime
import hashlib
import psycopg2
import os

app = Flask(__name__)

# ПРОСТЫЕ ФУНКЦИИ
def get_db_connection():
    """Подключение к базе данных"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        # Если нет DATABASE_URL, собираем из переменных
        db_host = os.getenv('DB_HOST', 'postgres-service.user-management.svc.cluster.local')
        db_name = os.getenv('DB_NAME', 'userdb')
        db_user = os.getenv('DB_USER', 'admin')
        db_password = os.getenv('DB_PASSWORD', '')
        
        db_url = f"host={db_host} dbname={db_name} user={db_user} password={db_password}"
    
    return psycopg2.connect(db_url)

def hash_password(password):
    """Простое хэширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id, username):
    """Создание JWT токена"""
    secret = os.getenv('JWT_SECRET', 'default-secret-key')
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, secret, algorithm='HS256')

def verify_token(token):
    """Проверка JWT токена"""
    try:
        secret = os.getenv('JWT_SECRET', 'default-secret-key')
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return payload
    except:
        return None


#  HEALTH CHECKS (Liveness Probe для Kubernetes)
@app.route('/health/live', methods=['GET'])
def health_live():
    """Простая проверка - сервис жив"""
    return jsonify({"status": "ok", "service": "auth-service"}), 200
# HEALTH CHECKS (Readiness Probe для Kubernetes)
@app.route('/health/ready', methods=['GET'])
def health_ready():
    """Проверка готовности (с подключением к БД)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({"status": "ready", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "not ready", "database": str(e)}), 503


# ОСНОВНЫЕ ЭНДПОИНТЫ
@app.route('/api/register', methods=['POST'])
def register():
    """Регистрация пользователя"""
    data = request.json
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Нужны username и password"}), 400
    
    username = data['username']
    password = data['password']
    email = data.get('email')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, есть ли такой пользователь
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Пользователь уже существует"}), 400
        
        # Хэшируем пароль
        password_hash = hash_password(password)
        
        # Сохраняем в БД
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, status) VALUES (%s, %s, %s, 'active') RETURNING id",
            (username, password_hash, email)
        )
        user_id = cursor.fetchone()[0]
        conn.commit()
        
        # Создаем токен
        token = create_token(user_id, username)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Пользователь создан",
            "user_id": user_id,
            "token": token
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Вход пользователя"""
    data = request.json
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Нужны username и password"}), 400
    
    username = data['username']
    password = data['password']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Ищем пользователя
        cursor.execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s AND status = 'active'",
            (username,)
        )
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return jsonify({"error": "Пользователь не найден"}), 401
        
        user_id, db_username, password_hash = user
        
        # Проверяем пароль
        if hash_password(password) != password_hash:
            cursor.close()
            conn.close()
            return jsonify({"error": "Неверный пароль"}), 401
        
        # Создаем токен
        token = create_token(user_id, username)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Успешный вход",
            "user_id": user_id,
            "username": username,
            "token": token
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/validate', methods=['GET'])
def validate():
    """Проверка токена"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Нужен Bearer токен"}), 401
    
    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    
    if not payload:
        return jsonify({"error": "Недействительный токен"}), 401
    
    return jsonify({
        "valid": True,
        "user_id": payload['user_id'],
        "username": payload['username']
    }), 200

@app.route('/api/config', methods=['GET'])
def get_config():
    """Получение конфигурации UI"""
    return jsonify({
        "login_title": os.getenv('LOGIN_TITLE', 'Вход в систему'),
        "welcome_message": os.getenv('WELCOME_MESSAGE', 'Добро пожаловать')
    }), 200

# === ЗАПУСК ===
if __name__ == '__main__':
    # Проверяем, что есть JWT секрет
    if not os.getenv('JWT_SECRET'):
        print("Внимание: JWT_SECRET не установлен, используется значение по умолчанию")
    
    app.run(host='0.0.0.0', port=5000, debug=os.getenv('FLASK_DEBUG') == 'true')