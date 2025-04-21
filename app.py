from flask import (  # noqa: F401
    Flask, render_template, redirect, 
    url_for, request, jsonify
)
from flask_login import (  # noqa: F401
    LoginManager, UserMixin, 
    login_required, logout_user, current_user
)
from auth import auth  # auth.py からBlueprintをインポート
from summarizer import summarize_article  # noqa: F401
from news_sites import (  # noqa: F401
    news_sites  # news_sites.py から辞書をインポート
)
from news_fetcher import get_news_from_gnews  # GNews APIからニュースを取得
from urllib.parse import urlparse  # noqa: F401
import anyio
import os
from datetime import datetime
from extensions import db, migrate
from sqlalchemy import or_

# Flaskアプリケーションの初期化
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# SQLAlchemyの設定
db_user = os.getenv('DB_USER', 'tokuhara')
db_pass = os.getenv('DB_PASSWORD', '')
db_host = os.getenv('DB_HOST', 'mysql')
db_port = os.getenv('DB_PORT', '3330')
db_name = os.getenv('DB_NAME', 'news_summary')

app.config['SQLALCHEMY_DATABASE_URI'] = \
    f'mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# DBとMigrateの初期化
db.init_app(app)
migrate.init_app(app, db)


# Flask-Loginの設定
login_manager = LoginManager()
login_manager.init_app(app)  # login_managerをFlaskアプリに関連付け
login_manager.login_view = "auth.login"  # 未ログイン時にリダイレクトされるURLを指定

# Blueprintの登録
app.register_blueprint(auth, url_prefix="/auth")


# ユーザー情報を保持するクラス（Flask-Login用）
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    favorites = db.relationship('Favorite', backref='user', lazy=True)

    def __init__(self, id, username):
        self.id = id
        self.username = username


# お気に入りモデル
class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    published_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, url, title, summary, published_at):
        self.user_id = user_id
        self.url = url
        self.title = title
        self.summary = summary
        self.published_at = published_at


# ユーザー情報を取得する関数
@login_manager.user_loader
def load_user(user_id):
    # ユーザーIDに基づいてユーザーをデータベースから取得
    user = db.session.get(User, user_id)
    if user:
        return user
    return None


# ニュースカテゴリ一覧
CATEGORIES = {
    "general": "一般",
    "business": "ビジネス",
    "technology": "テクノロジー",
    "entertainment": "エンタメ",
    "health": "健康",
    "science": "科学",
    "sports": "スポーツ"
}


# ニュースモデル
class News(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    published_at = db.Column(db.DateTime, nullable=False)
    category = db.Column(db.String(50), nullable=False)

    def __init__(self, title, url, summary, published_at, category):
        self.title = title
        self.url = url
        self.summary = summary
        self.published_at = published_at
        self.category = category


# ホームページ（ニュース一覧）
@app.route("/")
async def home():
    page = int(request.args.get("page", 1))
    search = request.args.get("search", "")
    category = request.args.get("category", "general")

    def fetch_news():
        return get_news_from_gnews(
            search=search,
            category=category,
            page=page
        )
    all_news = await anyio.to_thread.run_sync(fetch_news)

    # ログインしている場合、お気に入り情報を取得
    if current_user.is_authenticated:
        favorite_urls = {f.url for f in current_user.favorites}
        for news in all_news:
            news['is_favorite'] = news['url'] in favorite_urls
    else:
        for news in all_news:
            news['is_favorite'] = False

    news_list = all_news  # ページネーション用にニュースリストを取得

    # ページネーション用ダミー（本当はAPIの総件数を取れたら理想）
    total_pages = 5  # 仮に5ページまであるとする（必要に応じて変更）
    if total_pages <= 7:
        page_range = list(range(1, total_pages + 1))
    else:
        page_range = []
        if page > 4:
            page_range.append(1)
            page_range.append("...")
        start_page = max(1, page - 2)
        end_page = min(total_pages + 1, page + 3)
        page_range.extend(range(start_page, end_page))
        if page + 2 < total_pages:
            page_range.append("...")
            page_range.append(total_pages)

    template_args = {
        "news_list": news_list,
        "page": page,
        "page_range": page_range,
        "CATEGORIES": CATEGORIES,
        "search": search
    }
    return render_template("index.html", **template_args)


# お気に入りページ
@app.route("/favorites")
@login_required
def favorites():
    favorites = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    return render_template("favorites.html", favorites=favorites)


# お気に入り追加/削除API
@app.route("/api/favorites", methods=["POST"])
@login_required
def toggle_favorite():
    data = request.get_json()
    url = data.get('url')
    title = data.get('title')
    summary = data.get('summary')
    published_at_str = data.get('published_at')
    
    # published_atが空の場合は現在時刻を使用
    if not published_at_str:
        published_at = datetime.utcnow()
    else:
        try:
            published_at = datetime.fromisoformat(published_at_str)
        except ValueError:
            published_at = datetime.utcnow()

    # 既存のお気に入りを確認
    favorite = Favorite.query.filter_by(
        user_id=current_user.id, 
        url=url
    ).first()

    if favorite:
        # お気に入りを削除
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({"status": "removed"})
    else:
        # お気に入りを追加
        new_favorite = Favorite(
            user_id=current_user.id,
            url=url,
            title=title,
            summary=summary,
            published_at=published_at
        )
        db.session.add(new_favorite)
        db.session.commit()
        return jsonify({"status": "added"})


# ログアウトのルート
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True, use_reloader=False)


def get_page_range(current_page):
    page_range = [1]
    if current_page > 4:
        page_range.append("...")
        page_range += [
            current_page - 2,
            current_page - 1,
            current_page,
            current_page + 1,
            current_page + 2
        ]
    else:
        page_range += list(range(2, 7))
    return page_range


def get_news(category=None, search=None, page=1, per_page=10):
    try:
        # カテゴリと検索条件に基づいてクエリを構築
        query = News.query
        
        if category:
            query = query.filter(News.category == category)
            
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    News.title.like(search_term),
                    News.summary.like(search_term)
                )
            )
        
        # ページネーションを適用
        pagination = query.order_by(News.published_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        news_list = []
        for news in pagination.items:
            # URLからドメイン名を抽出
            domain = urlparse(news.url).netloc
            site_name = domain.replace('www.', '')
            
            news_dict = {
                'title': news.title,
                'url': news.url,
                'summary': news.summary,
                'published_at': news.published_at.strftime('%Y-%m-%d %H:%M'),
                'site_name': site_name,
                'is_favorite': False
            }
            
            # ログイン中のユーザーのお気に入り状態を確認
            if current_user.is_authenticated:
                favorite = Favorite.query.filter_by(
                    user_id=current_user.id,
                    url=news.url
                ).first()
                if favorite:
                    news_dict['is_favorite'] = True
            
            news_list.append(news_dict)
        
        return {
            'news_list': news_list,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next,
            'page': page,
            'total_pages': pagination.pages,
            'page_range': get_page_range(page, pagination.pages)
        }
        
    except Exception as e:
        print(f"Error in get_news: {str(e)}")
        return {
            'news_list': [],
            'has_prev': False,
            'has_next': False,
            'page': page,
            'total_pages': 0,
            'page_range': []
        }
