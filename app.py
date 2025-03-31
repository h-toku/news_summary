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
summarizer = pipeline("summarization", model="t5-small")

# Flaskアプリケーションの初期化。アプリ名（__name__）を引数に渡す。
app = Flask(__name__)

# セッションの秘密鍵（暗号化などに使われます）
app.secret_key = "top04259984"  # アプリケーションのセッションデータを保護するために必要

# ニュースカテゴリを定義しています。これにより、ユーザーがカテゴリごとにニュースを絞り込めます。
CATEGORIES = [
    'business', 'entertainment', 'general', 'health', 'science', 'sports', 'technology'
]

# ニュースAPIからデータを取得するためのAPIキー（ニュース情報を提供する外部サービスから取得したもの）
API_KEY = "de42c283e76946ad9c94252b4d20f42a"  # ここに自分のAPIキーを入れます

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
    NEWS_URL = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={API_KEY}&category={category}&page={page}&pageSize=5"
    if search:
        NEWS_URL += f"&q={search}"  # 検索キーワードをURLに追加
    response = requests.get(NEWS_URL)  # ニュースAPIからデータを取得
    print(response.json())  # レスポンスの内容を表示して確認
    return response.json()  # JSON形式で返す

# ニュース記事を要約する関数
def summarize_text(text):
    if not text:
        return "要約できる本文がありません。"  # 本文が空ならこのメッセージを返す
    input_length = len(text.split())  # 本文の単語数を数える
    max_len = min(50, input_length * 2)  # 要約の最大長さを決定
    summary = summarizer(text, max_length=max_len, min_length=10, do_sample=False)  # 要約を生成
    return summary[0]['summary_text']  # 要約したテキストを返す

# トップページの処理。GETリクエストに基づいてニュースを表示
@app.route("/", methods=["GET", "POST"])
def home():
    # ページ番号とカテゴリ、検索キーワードを取得
    page = request.args.get("page", 1, type=int)
    category = request.args.get('category', 'general')
    search = request.args.get('search', '')  # 検索キーワードを取得

    # ニュースをAPIから取得
    news_data = get_news(category, page, search)
    articles = news_data.get("articles", [])  # 記事データを取得

    # 記事がなければエラーメッセージを表示
    if not articles:
        return "Error: No articles found", 500

    news_list = []
    # 各記事を要約してリストに追加
    for article in articles:
        title = article.get("title", "No Title")
        description = article.get("description", "No Description")
        published_at = article.get("publishedAt", "No Date")

        # 要約を生成
        summary = summarize_text(description)
        news_list.append({
            "title": title,
            "summary": summary,
            "url": article.get("url", "#"),
            "publishedAt": published_at
        })

    # 次のページがあれば次ページの番号を設定
    next_page = page + 1 if len(articles) == 5 else None

    # 現在のページ、次ページをテンプレートに渡す
    return render_template("index.html", news_list=news_list, category=category, page=page, next_page=next_page, categories=CATEGORIES, search=search)

# アプリケーションの実行
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)  # アプリケーションをポート3000で実行（デバッグモード）
