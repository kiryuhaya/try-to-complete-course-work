from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

app = Flask(__name__)
app.config['SECRET_KEY'] = 'замени_на_надежный_секретный_ключ'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модели базы данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    checks = db.relationship('CheckHistory', backref='user', lazy=True)

class CheckHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input_text = db.Column(db.Text, nullable=False)
    result = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Заглушка для нейросети
def dummy_model_check(text):
    return f"Результат проверки: текст выглядит как машинно сгенерированный (затычка)."

# Главная страница с формой проверки текста
@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        text = request.form.get('text_to_check')
        if text:
            result = dummy_model_check(text)
            # Если пользователь вошёл в систему, сохраняем проверку в истории
            if 'user_id' in session:
                new_check = CheckHistory(input_text=text, result=result, user_id=session['user_id'])
                db.session.add(new_check)
                db.session.commit()
        else:
            flash("Введите текст для проверки", "warning")
    return render_template('index.html', result=result)

# Регистрация пользователя
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        if username and password:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash("Пользователь с таким именем уже существует", "danger")
                return redirect(url_for('register'))
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("Регистрация успешна, теперь войдите в аккаунт", "success")
            return redirect(url_for('login'))
        else:
            flash("Заполните все поля", "warning")
    return render_template('register.html')

# Вход пользователя
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash("Успешный вход", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Неверный логин или пароль", "danger")
    return render_template('login.html')

# Выход из аккаунта
@app.route('/logout')
def logout():
    session.clear()
    flash("Вы вышли из аккаунта", "info")
    return redirect(url_for('index'))

# Личный кабинет пользователя с историей проверок
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Сначала войдите в аккаунт", "warning")
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user is None:
        flash("Пользователь не найден. Пожалуйста, войдите снова.", "warning")
        session.clear()
        return redirect(url_for('login'))
    history = CheckHistory.query.filter_by(user_id=user.id).order_by(CheckHistory.timestamp.desc()).all()
    return render_template('dashboard.html', user=user, history=history)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
