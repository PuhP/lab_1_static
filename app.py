import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lab4-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db' # Используем SQLite для простоты
db = SQLAlchemy(app)

#пароль
def validate_password(password):
    errors = []
    if not (8 <= len(password) <= 128):
        errors.append("Длина должна быть от 8 до 128 символов.")
    if not re.search(r'[a-zа-я]', password):
        errors.append("Должна быть минимум одна строчная буква.")
    if not re.search(r'[A-ZА-Я]', password):
        errors.append("Должна быть минимум одна заглавная буква.")
    if not re.search(r'\d', password):
        errors.append("Должна быть минимум одна цифра.")
    if ' ' in password:
        errors.append("Пароль не должен содержать пробелы.")
    
    # Разрешенные спецсимволы по заданию
    allowed_chars = set(r"~!?!@#$%^&*_ -+()[]{}><\/| \"'.,:;")
    # Проверка на недопустимые символы (если нужно строго)
    
    return errors

# тип данные
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    users = db.relationship('User', backref='role', lazy=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(50))
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# инициализ данных
with app.app_context():
    db.create_all()
    if not Role.query.first():
        db.session.add_all([
            Role(name="Администратор", description="Полный доступ"),
            Role(name="Пользователь", description="Просмотр контента")
        ])
        db.session.commit()


# Настройка LoginManager (обязательно для работы UserMixin)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Главная страница (Список пользователей)
@app.route('/')
def index():
    users = User.query.all()
    return render_template('index.html', users=users)

@app.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    roles = Role.query.all()
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        last_name = request.form.get('last_name')
        first_name = request.form.get('first_name')
        middle_name = request.form.get('middle_name')
        role_id = request.form.get('role_id')

        # Простая валидация логина (по заданию: латиница + цифры, >= 5 символов)
        if not login or len(login) < 5 or not re.match(r'^[a-zA-Z0-9]+$', login):
            flash("Логин должен быть не менее 5 символов и содержать только латиницу и цифры.", "danger")
            return render_template('create_user.html', roles=roles)

        # Твоя валидация пароля
        password_errors = validate_password(password)
        if password_errors:
            for error in password_errors:
                flash(error, "danger")
            return render_template('create_user.html', roles=roles)

        # Проверка обязательного имени
        if not first_name:
            flash("Имя обязательно для заполнения.", "danger")
            return render_template('create_user.html', roles=roles)

        # Проверка уникальности логина
        if User.query.filter_by(login=login).first():
            flash("Такой логин уже занят.", "danger")
            return render_template('create_user.html', roles=roles)

        try:
            new_user = User(
                login=login,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                role_id=role_id if role_id else None
            )
            new_user.set_password(password) # Хешируем
            db.session.add(new_user)
            db.session.commit()
            flash("Пользователь успешно создан!", "success")
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при сохранении: {str(e)}", "danger")

    return render_template('create_user.html', roles=roles)

@app.route('/users/<int:user_id>')
def view_user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('view_user.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_val = request.form.get('login')
        password_val = request.form.get('password')
        remember = True if request.form.get('remember') else False

        # --- ОТЛАДКА: смотрим, что пришло из формы ---
        print(f"\n[DEBUG] Попытка входа с логином: '{login_val}'")

        user = User.query.filter_by(login=login_val).first()

        # --- ОТЛАДКА: нашли ли мы пользователя в БД ---
        if user:
            print(f"[DEBUG] Пользователь найден в БД: {user.login} (ID: {user.id})")
            
            # Проверяем пароль
            is_password_correct = user.check_password(password_val)
            print(f"[DEBUG] Результат проверки пароля: {is_password_correct}")

            if is_password_correct:
                login_user(user, remember=remember)
                flash("Вы успешно вошли в систему!", "success")
                
                next_page = request.args.get('next')
                print(f"[DEBUG] Переход на страницу: {next_page or 'index'}")
                return redirect(next_page or url_for('index'))
            else:
                print("[DEBUG] Ошибка: Пароль не совпал с хешем в базе.")
        else:
            print(f"[DEBUG] Ошибка: Пользователь с логином '{login_val}' не найден в БД.")

        flash("Неверный логин или пароль.", "danger")
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из системы.", "success")
    return redirect(url_for('index'))

@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()
    
    if request.method == 'POST':
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.middle_name = request.form.get('middle_name')
        role_id = request.form.get('role_id')
        user.role_id = role_id if role_id else None

        if not user.first_name:
            flash("Имя обязательно для заполнения.", "danger")
            return render_template('edit_user.html', user=user, roles=roles)

        try:
            db.session.commit()
            flash("Данные пользователя обновлены!", "success")
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при обновлении: {str(e)}", "danger")

    return render_template('edit_user.html', user=user, roles=roles)

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f"Пользователь {user.first_name} удален.", "success")
    except:
        flash("Ошибка при удалении.", "danger")
    return redirect(url_for('index'))

#пароль
@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_pass = request.form.get('old_password')
        new_pass = request.form.get('new_password')
        confirm_pass = request.form.get('confirm_password')

        # 1. Проверка старого пароля
        if not current_user.check_password(old_pass):
            flash("Текущий пароль введен неверно.", "danger")
            return render_template('change_password.html')

        # 2. Проверка совпадения новых паролей
        if new_pass != confirm_pass:
            flash("Новые пароли не совпадают.", "danger")
            return render_template('change_password.html')
            
        # 3. Валидация нового пароля по твоим правилам (8-128 симв., регистр, цифры)
        password_errors = validate_password(new_pass)
        if password_errors:
            for error in password_errors:
                flash(error, "danger")
            return render_template('change_password.html')

        # 4. Сохранение нового пароля
        try:
            current_user.set_password(new_pass)
            db.session.commit()
            flash("Пароль успешно изменен!", "success")
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при сохранении пароля: {str(e)}", "danger")

    return render_template('change_password.html')



# Запуск сервера
if __name__ == '__main__':
    app.run(debug=True)
        