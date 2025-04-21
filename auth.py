from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length
from sqlalchemy.exc import IntegrityError
from extensions import db

# Blueprintの作成
auth = Blueprint('auth', __name__)
# ユーザー情報を保持するクラス（Flask-Login用）


class User(UserMixin):
    def __init__(self, username, password=None, id=None):
        self.id = id
        self.username = username
        self.password = password


class RegistrationForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[InputRequired(), Length(min=4, max=100)]
    )
    password = PasswordField(
        'Password',
        validators=[InputRequired(), Length(min=6)]
    )


# ユーザー情報を取得する関数（Flask-Login用）
@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("パスワードが一致していません。", "error")
            return render_template("register.html")

        try:
            # ユーザーをデータベースに追加 (SQLAlchemyを使用)
            hashed_password = generate_password_hash(password)
            db.session.execute(
                db.text(
                    "INSERT INTO users (username, password) "
                    "VALUES (:username, :password)"
                ),
                {
                    "username": username,
                    "password": hashed_password
                }
            )
            db.session.commit()
            flash("登録が完了しました！", "success")
            return redirect(url_for("auth.login"))
        except IntegrityError:
            # 重複エラーをキャッチしてフラッシュメッセージを表示
            db.session.rollback()
            flash("そのユーザーネームはすでに使われています。別のユーザー名を選んでください。", "error")

    return render_template("register.html")


# ログインのルート
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        result = db.session.execute(
            db.text(
                "SELECT id, username, password "
                "FROM users WHERE username = :username"
            ),
            {"username": username}
        )
        user_data = result.fetchone()

        if user_data and check_password_hash(user_data[2], password):
            user = User(id=user_data[0], username=user_data[1])
            login_user(user)
            return redirect(url_for("home"))
        else:
            flash("ユーザー名/パスワードが間違っています。", "error")

    return render_template("login.html")


# ログアウトのルート
@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
