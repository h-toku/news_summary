from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_login import LoginManager, UserMixin, login_required, logout_user
from flask_mysqldb import MySQL
from auth import auth  # auth.py からBlueprintをインポート
from summarizer import summarize_article
from news_sites import news_sites  # news_sites.py から辞書 news_sites をインポート
from news_fetcher import get_news_from_gnews  # GNews APIからニュースを取得
from urllib.parse import urlparse
import anyio
from flask_migrate import Migrate
from favorite import db  # favorite.pyからdbをインポート
from flask_sqlalchemy import SQLAlchemy

# Flaskアプリケーションの初期化
app = Flask(__name__)
app.secret_key = "top04259984"

# MySQLの設定
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'tokuhara'
app.config['MYSQL_PASSWORD'] = 'top04259984'
app.config['MYSQL_DB'] = 'news_summary'

# SQLAlchemyの設定
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://tokuhara:top04259984@mysql:3330/news_summary'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config.from_object('config')  # config.py から設定を読み込む
db = SQLAlchemy(app)

# MySQLとの接続設定
mysql = MySQL(app)

# SQLAlchemyの初期化
db.init_app(app)

# Flask-Migrateの設定
migrate = Migrate(app, db)

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
@app.route("/")
async def home():
    page = int(request.args.get("page", 1))
    search = request.args.get("search", "")
    category = request.args.get("category", "general")

    all_news = await anyio.to_thread.run_sync(
        lambda: get_news_from_gnews(search=search, category=category, page=page)
    )

    # ページごとの件数
    per_page = 10
    news_list = all_news

    # ページネーション用ダミー（本当はAPIの総件数を取れたら理想）
    total_pages = 5  # 仮に5ページまであるとする（必要に応じて変更）
    if total_pages <= 7:
        page_range = list(range(1, total_pages + 1))
    else:
        page_range = []
        if page > 4:
            page_range.append(1)
            page_range.append("...")
        page_range.extend(range(max(1, page - 2), min(total_pages + 1, page + 3)))
        if page + 2 < total_pages:
            page_range.append("...")
            page_range.append(total_pages)

    return render_template(
        "index.html",
        news_list=news_list,
        page=page,
        page_range=page_range,
        CATEGORIES=CATEGORIES,
        search=search
    )

# ログアウトのルート
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))  # 'auth.login'に修正

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True, use_reloader=False)

def get_page_range(current_page):
    page_range = [1]
    if current_page > 4:
        page_range.append("...")
        page_range += [current_page - 2, current_page - 1, current_page, current_page + 1, current_page + 2]
    else:
        page_range += list(range(2, 7))
    return page_range


@app.route("/summarize", methods=["POST"])
async def summarize():
    try:
        data = await request.get_json()
        url = data.get("url")

        if not url:
            return jsonify({"summary": "URLが指定されていません"}), 400

        site_url = urlparse(url).scheme + "://" + urlparse(url).netloc
        site_info = news_sites.get(site_url)

        if not site_info:
            return jsonify({"summary": "未対応のニュースサイトです"})

        article = {"url": url}
        summary = await summarize_article(article, site_url)

        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"summary": f"要約中にエラーが発生しました: {str(e)}"}), 500

