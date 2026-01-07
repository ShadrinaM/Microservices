const express = require('express');
const bodyParser = require('body-parser');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');

const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'dev_secret';

const db = new sqlite3.Database('./users.db');
db.serialize(() => {
	db.run(`CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT UNIQUE,
		password TEXT,
		status TEXT DEFAULT 'active'
	)`);
});

const app = express();
app.use(bodyParser.json());

app.post('/auth/register', async (req, res) => {
	const { username, password } = req.body;
	if (!username || !password) return res.status(400).json({ error: 'missing' });
	const hash = await bcrypt.hash(password, 10);
	db.run('INSERT INTO users (username, password) VALUES (?, ?)', [username, hash], function(err) {
		if (err) return res.status(400).json({ error: 'user_exists' });
		return res.json({ id: this.lastID, username });
	});
});

app.post('/auth/login', (req, res) => {
	const { username, password } = req.body;
	if (!username || !password) return res.status(400).json({ error: 'missing' });
	db.get('SELECT * FROM users WHERE username = ?', [username], async (err, row) => {
		if (err || !row) return res.status(401).json({ error: 'invalid' });
		const ok = await bcrypt.compare(password, row.password);
		if (!ok) return res.status(401).json({ error: 'invalid' });
		const token = jwt.sign({ userId: row.id, username: row.username }, JWT_SECRET, { expiresIn: '2h' });
		return res.json({ token });
	});
});

app.get('/auth/validate', (req, res) => {
	const auth = req.headers.authorization;
	if (!auth || !auth.startsWith('Bearer ')) return res.status(401).json({ error: 'no_token' });
	const token = auth.split(' ')[1];
	jwt.verify(token, JWT_SECRET, (err, decoded) => {
		if (err) return res.status(401).json({ error: 'invalid' });
		return res.json({ user: decoded });
	});
});

app.get('/health/live', (req, res) => res.sendStatus(200));
app.get('/health/ready', (req, res) => res.sendStatus(200));

app.listen(PORT, () => console.log('auth-service listening on', PORT));