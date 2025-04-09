from news_fetcher import get_news_from_gnews  # GNews APIからニュースを取得
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM # Transformersライブラリからモデルをインポート
from news_sites import news_sites  # news_sites.py から辞書 news_sites をインポート
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import json
import aiohttp
import asyncio

# ニュース要約に使用するAIモデルの読み込み
model_name = "csebuetnlp/mT5_multilingual_XLSum"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

async def summarize_news(news_list, page):
    # GNewsからニュースを取得
    articles = get_news_from_gnews(category="general", page=1)

    summarized_news = []

    news_list = []
    for article in articles:
        article_url = article.get('url', '')
        
        # サイト情報を取得（URLから抽出）
        site_url = extract_site_url(article_url)

        # 要約を非同期で取得
        summary = await summarize_article(article, site_url)
        
        # ニュースリストに追加
        news_list.append({
            "title": article.get('title', 'No Title'),
            "summary": summary,
            "url": article_url,
            "publishedAt": article.get('publishedAt', 'No Date'),
        })
    
    return news_list

# サイトURLを抽出する関数（URLからサイトを決定）
def extract_site_url(url):
    # ここでURLからドメイン部分などを抽出
    # 例: https://example.com/news -> "https://example.com"
    parsed_url = urlparse(url)
    site_url = parsed_url.scheme + "://" + parsed_url.netloc
    return site_url


# ニュース記事を要約する関数
async def summarize_article(article, site_url):
    site_info = news_sites.get(site_url)
    if not site_info:
        return "未対応サイトです"

    url = article['url']
    article_content = await get_html_content(url, site_info)  # html_element を渡さない

    print(f"要約対象URL: {url}")
    print(f"要約対象サイト: {site_url}")
    print(f"要約対象コンテンツ: {article_content}")

    if article_content:
        prompt = "日本語で要約: " + article_content  # ← ここ重要！
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, padding="longest", max_length=512)
        summary_ids = await model.generate(inputs["input_ids"], max_length=100, num_beams=4, early_stopping=True)
        return tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    else:
        return "要約できませんでした"

# ニュースの要約をまとめて取得する関数

async def get_html_content(url, site_info):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"⚠️ HTTPエラー: {response.status}")
                return None

            html = await response.text()  # 非同期にHTMLを取得
            soup = BeautifulSoup(html, 'html.parser')
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

