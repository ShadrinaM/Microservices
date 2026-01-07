from flask import Flask, request, jsonify
import jwt
import psycopg2
import os

app = Flask(__name__)


def get_db_connection():
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
    try:
        secret = os.getenv("JWT_SECRET", "default-secret-key")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except:
        return None


@app.route("/health/live", methods=["GET"])
def health_live():
    return jsonify({"status": "ok", "service": "report-service"}), 200


@app.route("/health/ready", methods=["GET"])
def health_ready():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({"status": "ready", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "not ready", "database": str(e)}), 503


@app.route("/api/report", methods=["GET"])
def generate_report():
    """Возвращает список пользователей с процентом прочитанных/непрочитанных уведомлений."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Нужен Bearer токен"}), 401
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({"error": "Недействительный токен"}), 401

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Получаем для каждого пользователя общее число уведомлений и число прочитанных
        cur.execute(
            """
            SELECT u.id, u.username,
                   COUNT(n.id) AS total,
                   COALESCE(SUM(CASE WHEN n.is_read THEN 1 ELSE 0 END),0) AS read_count
            FROM users u
            LEFT JOIN notifications n ON n.user_id = u.id
            GROUP BY u.id, u.username
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        result = []
        for r in rows:
            uid, username, total, read_count = r
            total = int(total)
            read_count = int(read_count)
            if total > 0:
                read_pct = round((read_count / total) * 100, 2)
                unread_pct = round(100 - read_pct, 2)
            else:
                read_pct = 0.0
                unread_pct = 0.0
            result.append(
                {
                    "user_id": uid,
                    "username": username,
                    "total_notifications": total,
                    "read_count": read_count,
                    "read_percent": read_pct,
                    "unread_percent": unread_pct,
                }
            )

        # Сортируем по проценту прочитанных по убыванию
        result.sort(key=lambda x: x["read_percent"], reverse=True)

        return jsonify({"report": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=os.getenv("FLASK_DEBUG") == "true")