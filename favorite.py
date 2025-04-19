from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from flask_login import current_user, login_required
from auth import auth

db = SQLAlchemy()


class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


@auth.route('/favorite/<int:news_id>', methods=['POST'])
@login_required
def add_favorite(news_id):
    # お気に入りを追加
    favorite = Favorite(user_id=current_user.id, news_id=news_id)
    db.session.add(favorite)
    db.session.commit()
    return jsonify({'message': 'お気に入りに追加しました！'}), 201

@auth.route('/favorites', methods=['GET'])
@login_required
def get_favorites():
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    news_list = [{'id': f.news_id, 'title': f.news.title} for f in favorites]
    return render_template('favorites.html', news_list=news_list)