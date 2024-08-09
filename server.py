import smtplib
from datetime import datetime, timedelta
import secrets
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import werkzeug
from flask import Flask, render_template, redirect, url_for, request, send_from_directory, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from werkzeug.security import generate_password_hash

load_dotenv()


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-goes-here'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)


# user_loader callback
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    password: Mapped[str] = mapped_column(unique=False, nullable=False)


class RecoveryCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(50), nullable=False, unique=True)
    expiry_time = db.Column(db.DateTime, nullable=False)

    user = db.relationship('User', back_populates='recovery_codes')


User.recovery_codes = db.relationship('RecoveryCode', back_populates='user', lazy=True)

with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form['password']
        # Hashing and salting the password entered by the user
        hash_password = generate_password_hash(password=password,
                                               method='pbkdf2:sha256:600000',
                                               salt_length=8)
        # generate_password_hash: used for generating secure password hashes.
        # password: This is the password that you want to hash.
        # method='pbkdf2:sha256:600000': This specifies the hashing method and parameters to be used.
        # In this case:
        # pbkdf2 indicates that the PBKDF2 (Password-Based Key Derivation Function 2) algorithm will be used.
        # sha256 specifies the hash function SHA-256, which is used within the PBKDF2 algorithm.
        # 600000 specifies the number of iterations of the PBKDF2 algorithm.This value determines the computational cost of generating the hash and
        # helps enhance security by increasing the time required to compute the hash. Higher values typically provide greater security but may also result in longer computation times.
        # salt_length=8: This parameter specifies the length of the salt to be used in the password hashing process.

        # Storing the hashed password in our database
        user = User(username=username, email=email, password=hash_password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        print(email, password)
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User.query.filter_by(username=email).first()

        if user:
            if werkzeug.security.check_password_hash(user.password, password):
                login_user(user)

                return redirect(url_for("secretz"))

    return render_template("login.html")


def send_recovery_email(to_email, code):
    from_email = os.getenv('EMAIL_USER')
    from_password = os.getenv('EMAIL_PASS')
    subject = 'Password Recovery Code'
    body = (f'Your recovery code is {code}.'
            f'It will expire in 15 minutes.')

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(from_email, from_password)
        server.sendmail(from_email, to_email, msg.as_string())


@app.route('/forgetpassword', methods=['GET', 'POST'])
def forgetpassword():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        print(email, user)
        if user:
            print(user)
            code = secrets.token_hex(4)

            expiry_time = datetime.utcnow() + timedelta(minutes=15)
            recovery_code = RecoveryCode(user_id=user.id, code=code, expiry_time=expiry_time)
            db.session.add(recovery_code)
            db.session.commit()

            # Send the recovery code via email
            send_recovery_email(user.email, code)
            return redirect(url_for('reset_password'))

    return render_template("forget.html")


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get("email")
        code = request.form.get("code")
        new_password = request.form.get("password")
        print(email, code, new_password)
        user = User.query.filter_by(email=email).first()
        if user:
            recovery_code = RecoveryCode.query.filter_by(user_id=user.id, code=code).first()

            if recovery_code and recovery_code.expiry_time > datetime.utcnow():
                # Update user password
                hash_password = generate_password_hash(new_password, method='pbkdf2:sha256:600000', salt_length=8)
                user.password = hash_password
                db.session.delete(recovery_code)
                db.session.commit()

                flash('Your password has been updated.')
                return redirect(url_for('login'))

            flash('Invalid or expired recovery code.')

    return render_template("reset_password.html")


@app.route('/secret', methods=['GET', 'POST'])
@login_required
def secretz():
    return render_template("secret.html", username=current_user.username)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route('/download', methods=['GET'])
@login_required
def download():
    if request.method == "GET":
        return send_from_directory('static', 'flask_cheatsheet.pdf')


if __name__ == '__main__':
    app.run(debug=True, port=5001)
