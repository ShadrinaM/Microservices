from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import db, User
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Конфигурация базы данных из переменных окружения
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/userdb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Создание таблиц
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:  # В реальном приложении используйте хеширование!
            if user.status != 'active':
                flash(f'Аккаунт {user.status}')
                return redirect(url_for('login'))
            
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('profile'))
        else:
            flash('Неверные учетные данные')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', '')
        full_name = request.form.get('full_name', '')
        
        existing_user = User.query.filter_by(username=username).first()
        
        if existing_user:
            flash('Пользователь уже существует')
        else:
            new_user = User(
                username=username, 
                password=password,
                email=email if email else None,
                full_name=full_name if full_name else None
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация успешна! Теперь войдите в систему.')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        # Обновляем только те поля, которые предоставлены
        if 'email' in request.form:
            user.email = request.form['email'] if request.form['email'] else None
        
        if 'full_name' in request.form:
            user.full_name = request.form['full_name'] if request.form['full_name'] else None
        
        if 'password' in request.form and request.form['password']:
            # В реальном приложении здесь должно быть хеширование пароля
            user.password = request.form['password']
        
        try:
            db.session.commit()
            flash('Профиль успешно обновлен!')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении: {str(e)}')
    
    return render_template('edit_profile.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)