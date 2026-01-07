from flask import Flask, request, jsonify
import jwt
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
    return jsonify({"status": "ok", "service": "notification-service"}), 200


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


# NOTIFICATION ENDPOINTS
@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    """Получение уведомлений пользователя"""
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
            """SELECT id, title, message, type, is_read, created_at 
               FROM notifications 
               WHERE user_id = %s 
               ORDER BY created_at DESC""",
            (user_id,),
        )
        notifications = cursor.fetchall()

        cursor.close()
        conn.close()

        result = []
        for notif in notifications:
            result.append(
                {
                    "id": notif[0],
                    "title": notif[1],
                    "message": notif[2],
                    "type": notif[3],
                    "is_read": notif[4],
                    "created_at": notif[5].isoformat() if notif[5] else None,
                }
            )

        return jsonify({"notifications": result}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications", methods=["POST"])
def create_notification():
    """Создание уведомления"""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Нужен Bearer токен"}), 401

    token = auth_header.split(" ")[1]
    payload = verify_token(token)

    if not payload:
        return jsonify({"error": "Недействительный токен"}), 401

    user_id = payload["user_id"]
    data = request.json

    if not data or "title" not in data or "message" not in data:
        return jsonify({"error": "Нужны title и message"}), 400

    title = data["title"]
    message = data["message"]
    notif_type = data.get("type", "info")

    if notif_type not in ["info", "warning", "success", "error"]:
        return jsonify({"error": "Неверный тип уведомления"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO notifications (user_id, title, message, type, is_read) 
               VALUES (%s, %s, %s, %s, false) 
               RETURNING id, created_at""",
            (user_id, title, message, notif_type),
        )
        notif_id, created_at = cursor.fetchone()
        conn.commit()

        cursor.close()
        conn.close()

        return (
            jsonify(
                {
                    "message": "Уведомление создано",
                    "id": notif_id,
                    "title": title,
                    "message": message,
                    "type": notif_type,
                    "created_at": created_at.isoformat(),
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications/<int:notification_id>/read", methods=["PUT"])
def mark_as_read(notification_id):
    """Отметить уведомление как прочитанное"""
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
            "UPDATE notifications SET is_read = true WHERE id = %s AND user_id = %s",
            (notification_id, user_id),
        )
        conn.commit()

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Уведомление не найдено"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "Уведомление отмечено как прочитанное"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications/<int:notification_id>", methods=["DELETE"])
def delete_notification(notification_id):
    """Удалить уведомление"""
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
            "DELETE FROM notifications WHERE id = %s AND user_id = %s",
            (notification_id, user_id),
        )
        conn.commit()

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Уведомление не найдено"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "Уведомление удалено"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=os.getenv("FLASK_DEBUG") == "true")
