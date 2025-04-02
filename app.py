import requests  # 外部からニュースを取得するためのライブラリ
from transformers import pipeline  # AIモデルを使用してニュースを要約するためのライブラリ
from flask import Flask, render_template, request, redirect, url_for, flash  # Flaskはウェブアプリケーションのフレームワーク
from flask_mysqldb import MySQL  # MySQLデータベースとFlaskを連携させるためのライブラリ
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user  # ユーザー認証機能
from werkzeug.security import generate_password_hash, check_password_hash  # パスワードの安全な処理
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length

# ここではAIによる要約処理を行うためにT5というモデルを使っています
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Flaskアプリケーションの初期化。アプリ名（__name__）を引数に渡す。
app = Flask(__name__)

# セッションの秘密鍵（暗号化などに使われます）
app.secret_key = "top04259984"  # アプリケーションのセッションデータを保護するために必要

# ニュースカテゴリ（GNewsに対応）
CATEGORIES = [
    'general', 'world', 'nation', 'business', 'technology',
    'entertainment', 'sports', 'science', 'health'
]

# GNews APIキー
GNEWS_API_KEY = "b91e84cbe135568c5bb4c33ce5ac51b6"

# MySQLデータベースに接続するための設定
app.config['MYSQL_HOST'] = 'mysql'  # MySQLサーバのホスト名（コンテナ名など）
app.config['MYSQL_USER'] = 'tokuhara'  # MySQLユーザー名
app.config['MYSQL_PASSWORD'] = 'top04259984'  # MySQLユーザーのパスワード
app.config['MYSQL_DB'] = 'news_summary'  # 使用するデータベース名

# MySQLとの接続設定
mysql = MySQL(app)

# Flask-Loginでユーザー認証のための設定
login_manager = LoginManager()
login_manager.init_app(app)  # アプリケーションにログインマネージャーを初期化
login_manager.login_view = "login"  # ログインページのビューを設定

# ユーザー情報を保持するクラス（Flask-Login用）
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=100)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6)])

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()  # フォームのインスタンスを作成
    if form.validate_on_submit():  # フォームが正しく送信された場合
        hashed_password = generate_password_hash(form.password.data, method='sha256')  # パスワードをハッシュ化
        new_user = User(username=form.username.data, password_hash=hashed_password)  # 新しいユーザーを作成
        db.session.add(new_user)  # ユーザーをデータベースに追加
        db.session.commit()  # 変更をコミット
        flash("登録が完了しました！ログインしてください。", "success")  # メッセージを表示
        return redirect(url_for('login'))  # ログインページにリダイレクト
    return render_template('register.html', form=form)  # フォームを渡す

# ログイン状態を保持するための関数。ユーザーがログインした際にユーザー情報を取得。
@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor()  # MySQL接続カーソルを取得
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))  # ユーザーIDでユーザーを検索
    user_data = cursor.fetchone()  # 一致するユーザー情報を取得
    if user_data:  # ユーザーが見つかればUserオブジェクトを返す
        return User(id=user_data[0], username=user_data[1])  # ユーザーIDとユーザー名を返す
    return None  # ユーザーが見つからなければNoneを返す

# ログインページの処理。ユーザー名とパスワードをチェックして、認証成功ならユーザーをログインさせる
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":  # POSTリクエストならログイン処理を行う
        username = request.form["username"]  # ユーザー名を取得
        password = request.form["password"]  # パスワードを取得

        # データベースからユーザー情報を取得
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()  # 一致するユーザー情報を取得

        # パスワードが一致するか確認
        if user_data and check_password_hash(user_data[2], password):  # ハッシュ化したパスワードと比較
            user = User(id=user_data[0], username=user_data[1])  # Userオブジェクトを作成
            login_user(user)  # ユーザーをログイン
            return redirect(url_for("profile"))  # プロフィールページにリダイレクト
        else:
            flash("Invalid credentials. Please try again.")  # 認証失敗のメッセージを表示

    return render_template("login.html")  # ログインフォームを表示

# プロフィールページの表示（ログインしている場合のみアクセス可能）
@app.route("/profile")
@login_required  # ログインしていないとアクセスできない
def profile():
    return f"Hello, {current_user.username}! You are logged in."  # ログイン中のユーザー名を表示

# ログアウト機能
@app.route("/logout")
@login_required  # ログインしていないとアクセスできない
def logout():
    logout_user()  # ログアウト処理
    return redirect(url_for("login"))  # ログインページにリダイレクト

# ニュースを取得する関数。指定したカテゴリーとページ番号に基づいてニュースを取得
def get_news(category, page, search=None):
    url = "https://gnews.io/api/v4/top-headlines"
    params = {
        "token": GNEWS_API_KEY,
        "lang": "ja",
        "country": "jp",
        "category": category,
        "max": 5,
        "sortby": "publishedAt", 
    }
    if search:
        params["q"] = search  # 検索ワードを追加

    response = requests.get(url, params=params)
    if response.status_code == 200:
        news_data = response.json()
        return news_data.get("articles", [])  # 記事リストを返す
    else:
        return []  # 取得失敗時は空リスト

# ニュース記事を要約する関数
def summarize_text(text):
    if not text:
        return "要約できる本文がありません。"

    # 単語数が少ない場合は要約せずそのまま返す
    if len(text.split()) < 20:
        return text

    try:
        summary = summarizer(text, max_length=50, min_length=30, do_sample=True, top_k=50, top_p=0.95)
        return summary[0]['summary_text']
    except Exception as e:
        print("Summarization Error:", e)
        return text  # エラー時は元の文章を返す

# ホームページ（ニュース一覧）
@app.route("/", methods=["GET", "POST"])
def home():
    page = request.args.get("page", 1, type=int)
    category = request.args.get('category', 'general')
    search = request.args.get('search', '')

    # GNews APIからニュースを取得
    articles = get_news(category, page, search)

    if not articles:
        flash("該当するニュースが見つかりませんでした。", "warning")
        return render_template("index.html", news_list=[], category=category, page=page, next_page=None, categories=CATEGORIES, search=search)

    news_list = []
    for article in articles:
        title = article.get("title", "No Title")
        description = article.get("description", "No Description")
        published_at = article.get("publishedAt", "No Date")
        url = article.get("url", "#")

        # 要約を生成
        summary = summarize_text(description)
        news_list.append({
            "title": title,
            "summary": summary,
            "url": url,
            "publishedAt": published_at
        })

    next_page = page + 1 if len(articles) == 5 else None

    return render_template("index.html", news_list=news_list, category=category, page=page, next_page=next_page, categories=CATEGORIES, search=search)

# アプリ実行
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)

