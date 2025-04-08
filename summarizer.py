from news_fetcher import get_news_from_gnews  # GNews APIからニュースを取得
from transformers import T5Tokenizer, T5ForConditionalGeneration # Transformersライブラリからモデルをインポート
from news_sites import news_sites  # news_sites.py から辞書 news_sites をインポート
import requests
from bs4 import BeautifulSoup
import json

# ニュース要約に使用するAIモデルの読み込み
model_name = "sonoisa/t5-base-japanese"
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)

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

# ニュース記事を要約する関数
def summarize_article(article, site_url):
    site_info = news_sites.get(site_url)
    if not site_info:
        return "未対応サイトです"

    url = article['url']
    article_content = get_html_content(url, site_info)  # html_element を渡さない

    if article_content:
        prompt = "summarize: " + article_content  # ← ここ重要！
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, padding="longest", max_length=512)
        summary_ids = model.generate(inputs["input_ids"], max_length=100, num_beams=4, early_stopping=True)
        return tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    else:
        return "要約できませんでした"

# ニュースの要約をまとめて取得する関数

import requests
from bs4 import BeautifulSoup
import json

def get_html_content(url, site_info):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"⚠️ HTTPエラー: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    tag_name = site_info['tag']
    content_method = site_info['content_method']
    element = site_info.get('element')  # element は任意扱い

    target_tag = None

    # タグの取得方法を element の種類に応じて決定
    if element == "id":
        target_tag = soup.find(tag_name, id=content_method)
    elif element == "class":
        target_tag = soup.find(tag_name, class_=content_method)
    elif element == "type":
        # 例: <script type="application/ld+json">
        script_tags = soup.find_all(tag_name, type=content_method)
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if data.get("@type") == "NewsArticle":
                    return data.get("description") or data.get("headline")
            except Exception:
                continue
        print("⚠️ NewsArticle 型の JSON が見つかりませんでした")
        return None
    else:
        print("⚠️ 不正な element 指定です")
        return None

    # 該当するタグが見つかった場合の処理
    if target_tag and target_tag.string:
        return target_tag.string.strip()
    
    print("⚠️ 該当タグが見つかりませんでした" + f" (URL: {url})")
    return None
