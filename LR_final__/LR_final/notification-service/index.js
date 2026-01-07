const express = require('express');
const bodyParser = require('body-parser');
const sqlite3 = require('sqlite3').verbose();
const axios = require('axios');

const PORT = process.env.PORT || 3002;
const AUTH_URL = process.env.AUTH_URL || 'http://auth-service:3000';

const db = new sqlite3.Database('./notifications.db');
db.serialize(() => {
	db.run(`CREATE TABLE IF NOT EXISTS notifications (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		userId INTEGER,
		message TEXT,
		read INTEGER DEFAULT 0,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
	)`);
});

const app = express();
app.use(bodyParser.json());

async function validateToken(req) {
	const auth = req.headers.authorization;
	if (!auth) throw new Error('no_token');
	const res = await axios.get(`${AUTH_URL}/auth/validate`, { headers: { authorization: auth }, timeout: 2000 });
	return res.data.user;
}

app.post('/notify', async (req, res) => {
	try {
		await validateToken(req);
		const { userId, message } = req.body;
		if (!userId || !message) return res.status(400).json({ error: 'missing' });
		db.run('INSERT INTO notifications (userId, message) VALUES (?, ?)', [userId, message], function(err) {
			if (err) return res.status(500).json({ error: 'db' });
			return res.json({ id: this.lastID });
		});
	} catch (e) {
		return res.status(401).json({ error: 'unauth' });
	}
});

app.get('/notifications', async (req, res) => {
	try {
		const user = await validateToken(req);
		db.all('SELECT * FROM notifications WHERE userId = ? ORDER BY created_at DESC', [user.userId], (err, rows) => {
			if (err) return res.status(500).json({ error: 'db' });
			return res.json({ notifications: rows });
		});
	} catch (e) {
		return res.status(401).json({ error: 'unauth' });
	}
});

app.get('/health/live', (req, res) => res.sendStatus(200));
app.get('/health/ready', (req, res) => res.sendStatus(200));

app.listen(PORT, () => console.log('notification-service', PORT));