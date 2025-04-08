import requests

# GNews APIの設定
GNEWS_API_KEY = "b91e84cbe135568c5bb4c33ce5ac51b6"  # GNews APIキー

def get_news_from_gnews(category="general", page=1, search=None):
    url = "https://gnews.io/api/v4/top-headlines"
    params = {
        "token": GNEWS_API_KEY,
        "lang": "ja",
        "country": "jp",
        "category": category,
        "sortby": "publishedAt", 
    }
    if search:
        params["q"] = search  # 検索ワードを追加

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json().get("articles", [])
    else:
        return []
