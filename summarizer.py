from news_fetcher import get_news_from_gnews  # GNews APIからニュースを取得
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM # Transformersライブラリからモデルをインポート
from news_sites import news_sites  # news_sites.py から辞書 news_sites をインポート
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import json
import aiohttp # type: ignore
import asyncio
import re

# ニュース要約に使用するAIモデルの読み込み
model_name = "csebuetnlp/mT5_multilingual_XLSum"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

async def summarize_news(news_list, page):
    # GNewsからニュースを取得
    articles = get_news_from_gnews(category="general", page=page)

    tasks = []
    for article in articles:
        article_url = article.get('url', '')
        site_url = article.get('source', {}).get('url', 'No Source URL')
        # 要約を非同期で取得
        tasks.append(
            summarize_article(article, site_url)
        )

        summaries = await asyncio.gather(*tasks)
        
        # ニュースリストに追加
        news_output = []
    for article, summary in zip(articles, summaries):
        news_output.append({
            "title": article.get('title', 'No Title'),
            "summary": summary,
            "url": article.get('url', ''),
            "publishedAt": article.get('publishedAt', 'No Date'),
            "site_name": article.get('source', {}).get('name', 'No Source'),
            "site_url": site_url
        })

    return news_output

def clean_text(text):
    if not text:
        return ""
    
    # 改行と空白の正規化
    text = re.sub(r'\s+', ' ', text)
    
    # 広告やSNSボタン関連のテキストを除去
    ad_patterns = [
        r'広告',
        r'スポンサード',
        r'シェア',
        r'ツイート',
        r'いいね！',
        r'関連記事',
        r'おすすめ',
        r'PR',
        r'©',
        r'Copyright',
        r'All rights reserved',
    ]
    for pattern in ad_patterns:
        text = re.sub(pattern, '', text)
    
    # 特殊文字の除去
    text = re.sub(r'[^\w\s、。！？「」（）\u4e00-\u9fff]', '', text)
    
    return text.strip()

# ニュース記事を要約する関数
async def summarize_article(article, site_url):
    try:
        site_info = news_sites.get(site_url)
        if not site_info:
            return "未対応サイトです"

        url = article['url']
        article_content = await get_html_content(url, site_info)

        if not article_content:
            return "要約できませんでした"

        # テキストのクリーニング
        cleaned_content = clean_text(article_content)
        
        if not cleaned_content:
            return "要約できませんでした"
        elif len(cleaned_content) < 100:
            return cleaned_content

        # 要約生成
        prompt = f"以下のニュース記事を簡潔な日本語で要約してください: {cleaned_content}"
        
        # 入力テキストを適切な長さに調整
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        )
        
        # より詳細な要約生成パラメータ
        summary_ids = model.generate(
            inputs["input_ids"],
            max_length=200,
            min_length=100,
            num_beams=5,
            length_penalty=1.5,
            no_repeat_ngram_size=3,
            early_stopping=True,
            temperature=0.8,
            top_k=50,
            top_p=0.95
        )
        
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        
        # 要約結果のポストプロセス
        summary = re.sub(r'要約[:：]', '', summary)
        summary = summary.strip()
        
        if len(summary) < 20:
            return cleaned_content
        elif not summary:
            return "要約できませんでした"
        return summary
    except Exception as e:
        print(f"要約生成エラー: {str(e)}")
        return "要約できませんでした"

# ニュースの要約をまとめて取得する関数

async def get_html_content(url, site_info):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"⚠️ HTTPエラー: {response.status}")
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # メタデータからの本文取得を試みる
                meta_description = soup.find('meta', {'name': 'description'})
                if meta_description:
                    content = meta_description.get('content', '')
                    if len(content) > 100:  # 十分な長さがある場合
                        return content

                # 本文の取得
                tag_name = site_info['tag']
                content_method = site_info['content_method']
                element = site_info['element']

                if element == "class":
                    target_tags = soup.find_all(tag_name, class_=content_method)
                    if target_tags:
                        # 全てのテキストを結合
                        content = ' '.join([tag.get_text() for tag in target_tags])
                        return content

                elif element == "id":
                    target_tag = soup.find(tag_name, id=content_method)
                    if target_tag:
                        return target_tag.get_text()

                print(f"⚠️ 本文が見つかりませんでした (URL: {url})")
                return None

    except Exception as e:
        print(f"⚠️ エラー: {str(e)}")
        return None

