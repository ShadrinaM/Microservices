const express = require('express');
const bodyParser = require('body-parser');
const sqlite3 = require('sqlite3').verbose();
const axios = require('axios');

const PORT = process.env.PORT || 3001;
const AUTH_URL = process.env.AUTH_URL || 'http://auth-service:3000';

const db = new sqlite3.Database('./profiles.db');
db.serialize(() => {
	db.run(`CREATE TABLE IF NOT EXISTS profiles (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		userId INTEGER UNIQUE,
		name TEXT,
		bio TEXT
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

app.get('/profile/me', async (req, res) => {
	try {
		const user = await validateToken(req);
		db.get('SELECT * FROM profiles WHERE userId = ?', [user.userId], (err, row) => {
			if (err) return res.status(500).json({ error: 'db' });
			return res.json({ profile: row || { userId: user.userId, name: user.username } });
		});
	} catch (e) {
		return res.status(401).json({ error: 'unauth' });
	}
});

app.post('/profile/me', async (req, res) => {
	try {
		const user = await validateToken(req);
		const { name, bio } = req.body;
		db.run('INSERT OR REPLACE INTO profiles (id, userId, name, bio) VALUES ((SELECT id FROM profiles WHERE userId = ?), ?, ?, ?)',
			[user.userId, user.userId, name || '', bio || ''], function(err) {
				if (err) return res.status(500).json({ error: 'db' });
				return res.json({ ok: true });
		});
	} catch (e) {
		return res.status(401).json({ error: 'unauth' });
	}
});

app.get('/health/live', (req, res) => res.sendStatus(200));
app.get('/health/ready', (req, res) => res.sendStatus(200));

app.listen(PORT, () => console.log('profile-service', PORT));