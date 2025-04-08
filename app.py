from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mysqldb import MySQL
from auth import auth  # auth.py からBlueprintをインポート
from summarizer import summarize_news

# Flaskアプリケーションの初期化
app = Flask(__name__)
app.secret_key = "top04259984"

# ニュースカテゴリ（GNewsに対応）
CATEGORIES = [
    'general', 'world', 'nation', 'business', 'technology',
    'entertainment', 'sports', 'science', 'health'
]

# MySQLの設定
app.config['MYSQL_HOST'] = 'mysql'
app.config['MYSQL_USER'] = 'tokuhara'
app.config['MYSQL_PASSWORD'] = 'top04259984'
app.config['MYSQL_DB'] = 'news_summary'

# MySQLとの接続設定
mysql = MySQL(app)

# Flask-Loginの設定
login_manager = LoginManager()
login_manager.init_app(app)  # login_managerをFlaskアプリに関連付け
login_manager.login_view = "auth.login"  # 未ログイン時にリダイレクトされるURLを指定

# Blueprintの登録
app.register_blueprint(auth, url_prefix="/auth")

# ユーザー情報を保持するクラス（Flask-Login用）
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# ユーザー情報を取得する関数
@login_manager.user_loader
def load_user(user_id):
    # ユーザーIDに基づいてユーザーをデータベースから取得
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    if user_data:
        return User(id=user_data[0], username=user_data[1])
    return None

# ホームページ（ニュース一覧）
@app.route("/", methods=["GET", "POST"])
def home():
    # ニュースの要約を取得
    news_list = summarize_news()

    # ページに渡す情報
    return render_template("index.html", news_list=news_list)

# ログアウトのルート
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))  # 'auth.login'に修正

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True, use_reloader=False)
