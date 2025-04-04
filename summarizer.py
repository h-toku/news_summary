from news_fetcher import get_news_from_gnews  # GNews APIからニュースを取得
from transformers import pipeline  # Transformersライブラリからモデルをインポート
from bs4 import BeautifulSoup  # BeautifulSoupを使ってHTMLをパース
import requests
from news_sites import news_sites  # news_sites.py から辞書 news_sites をインポート

# ニュース要約に使用するAIモデルの読み込み
summarizer = pipeline("summarization", model="google/pegasus-large")

# 記事の本文やメタ情報を抽出するための関数
def get_html_content(url, html_element):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 記事本文の抽出
        if html_element:
            content = soup.select_one(html_element)
            if content:
                return content.get_text()

        # メタタグから要約情報を取得する処理
        meta_element = site_info.get('meta_element')  # 修正：site_infoはsummarize_article内で取得
        if meta_element:
            content = soup.find('meta', {'name': 'description'})
            if content:
                return content.get('content', '')

        return ''
    except Exception as e:
        return ''  # エラーが発生した場合は空文字を返す

# ニュース記事を要約する関数
def summarize_article(article, site_url):
    # URLをキーとしてnews_sitesから該当サイトの情報を取得
    site_info = news_sites.get(site_url)  # URLを使って辞書から情報を取得
    
    if not site_info:
        return "未対応サイトです"  # サイトが未対応の場合はその旨を返す
    
    # 記事のURLを取得
    url = article['url']
    
    # html_elementを取得して、その内容を取得する
    html_element = site_info.get('html_element')
    article_content = get_html_content(url, html_element)  # 修正：html_elementを渡す
    
    if article_content:
        # 要約処理
        summary = summarizer(article_content)
        return summary[0]['summary_text'] if summary else "要約できませんでした"
    else:
        return "要約できませんでした"

# ニュースの要約をまとめて取得する関数
def summarize_news():
    # GNewsからニュースを取得
    articles = get_news_from_gnews(category="general", page=1)

    news_list = []
    for article in articles:
        # ニュースのURLを取得
        article_url = article.get('url', '')

        # URLがnews_sitesに部分一致するかを確認
        matched_site = None
        for site_url in news_sites:
            if article_url.startswith(site_url):  # 部分一致確認
                matched_site = site_url
                break
        
        if matched_site:
            # URLが一致した場合に、summarize_articleで要約
            summary = summarize_article(article, matched_site)
            news_list.append({
                "title": article.get('title', 'No Title'),
                "summary": summary,
                "url": article_url,
                "publishedAt": article.get('publishedAt', 'No Date'),
            })
        else:
            # 存在しない場合は「未対応」
            news_list.append({
                "title": article.get('title', 'No Title'),
                "summary": "未対応",
                "url": article_url,
                "publishedAt": article.get('publishedAt', 'No Date'),
            })

    return news_list
