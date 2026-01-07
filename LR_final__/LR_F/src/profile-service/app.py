from flask import Flask, request, jsonify
import jwt
import hashlib
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)


def get_db_connection():
    """Подключение к базе данных"""
    db_host = os.getenv(
        "DB_HOST", "postgres-service.user-platform-exam.svc.cluster.local"
    )
    db_name = os.getenv("DB_NAME", "userdb")
    db_user = os.getenv("DB_USER", "admin")
    db_password = os.getenv("DB_PASSWORD", "")

    return psycopg2.connect(
        host=db_host, database=db_name, user=db_user, password=db_password
    )


def hash_password(password):
    """Простое хэширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_token(token):
    """Проверка JWT токена"""
    try:
        secret = os.getenv("JWT_SECRET", "default-secret-key")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except:
        return None


# HEALTH CHECKS
@app.route("/health/live", methods=["GET"])
def health_live():
    """Проверка жизни сервиса"""
    return jsonify({"status": "ok", "service": "profile-service"}), 200


@app.route("/health/ready", methods=["GET"])
def health_ready():
    """Проверка готовности"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({"status": "ready", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "not ready", "database": str(e)}), 503


# PROFILE ENDPOINTS
@app.route("/api/profile", methods=["GET"])
def get_profile():
    """Получение данных профиля"""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Нужен Bearer токен"}), 401

    token = auth_header.split(" ")[1]
    payload = verify_token(token)

    if not payload:
        return jsonify({"error": "Недействительный токен"}), 401

    user_id = payload["user_id"]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, email, status, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if not user:
            return jsonify({"error": "Пользователь не найден"}), 404

        return (
            jsonify(
                {
                    "user_id": user[0],
                    "username": user[1],
                    "email": user[2],
                    "status": user[3],
                    "created_at": user[4].isoformat() if user[4] else None,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profile", methods=["PUT"])
def update_profile():
    """Обновление профиля пользователя"""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Нужен Bearer токен"}), 401

    token = auth_header.split(" ")[1]
    payload = verify_token(token)

    if not payload:
        return jsonify({"error": "Недействительный токен"}), 401

    user_id = payload["user_id"]
    data = request.json

    if not data:
        return jsonify({"error": "Нет данных для обновления"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем, что пользователь существует
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Пользователь не найден"}), 404

        updates = []
        params = []

        # Обновление username
        if "username" in data:
            # Проверяем уникальность нового username
            cursor.execute(
                "SELECT id FROM users WHERE username = %s AND id != %s",
                (data["username"], user_id),
            )
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({"error": "Имя пользователя уже занято"}), 400

            updates.append("username = %s")
            params.append(data["username"])

        # Обновление email
        if "email" in data:
            updates.append("email = %s")
            params.append(data["email"])

        # Обновление пароля
        if "password" in data:
            password_hash = hash_password(data["password"])
            updates.append("password_hash = %s")
            params.append(password_hash)

        # Обновление статуса
        if "status" in data:
            if data["status"] not in ["active", "inactive", "blocked"]:
                cursor.close()
                conn.close()
                return jsonify({"error": "Неверный статус"}), 400

            updates.append("status = %s")
            params.append(data["status"])

        if not updates:
            cursor.close()
            conn.close()
            return jsonify({"error": "Нет данных для обновления"}), 400

        # Выполняем обновление
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()

        # Получаем обновленные данные
        cursor.execute(
            "SELECT id, username, email, status, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        return (
            jsonify(
                {
                    "message": "Профиль обновлен",
                    "user_id": user[0],
                    "username": user[1],
                    "email": user[2],
                    "status": user[3],
                    "created_at": user[4].isoformat() if user[4] else None,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=os.getenv("FLASK_DEBUG") == "true")
