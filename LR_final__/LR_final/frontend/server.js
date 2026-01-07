const express = require('express');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 8080;

app.use(express.static(path.join(__dirname, 'public')));

app.get('/config', (req, res) => {
	return res.json({
		LOGIN_TITLE: process.env.LOGIN_TITLE || 'Вход',
		REGISTER_TITLE: process.env.REGISTER_TITLE || 'Регистрация',
		WELCOME_MESSAGE: process.env.WELCOME_MESSAGE || 'Добро пожаловать'
	});
});

app.listen(PORT, () => console.log('frontend on', PORT));
