from flask import Flask, request, jsonify
import logging, os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/notify', methods=['POST'])
def notify():
    data = request.json or {}
    user = data.get('username')
    msg = data.get('message')
    logging.info(f"Notify -> user:{user} msg:{msg}")
    return jsonify({"ok": True}), 200

@app.route('/health/live')
def live():
    return "ok", 200

@app.route('/health/ready')
def ready():
    return "ready", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
