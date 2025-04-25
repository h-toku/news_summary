import aiohttp
from bs4 import BeautifulSoup
import re

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

async def get_html_content(url, site_info):
    try:
        # 非同期HTTPリクエスト
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"⚠️ HTTPエラー: {response.status} - {url}")
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # メタタグからのコンテンツ取得（優先的に使う）
                meta_description = soup.find('meta', {'name': 'description'})
                og_description = soup.find('meta', {'property': 'og:description'})
                if meta_description:
                    content = meta_description.get('content', '')
                    if len(content) > 100:
                        return clean_text(content)  # クリーニング後に返す
                elif og_description:
                    content = og_description.get('content', '')
                    if len(content) > 100:
                        return clean_text(content)

                # 各ニュースサイトに応じた処理
                tag_name = site_info.get('tag', 'p')  # 'p'タグがデフォルト
                content_method = site_info.get('content_method', '')  # 'content_method' は class または id
                element = site_info.get('element', 'class')  # デフォルトは 'class'

                # 'class'または'id'で指定された内容を取得
                if element == "class":
                    target_tags = soup.find_all(tag_name, class_=content_method)
                    if target_tags:
                        content = ' '.join([tag.get_text() for tag in target_tags])
                        return clean_text(content)  # テキストクリーニング
                elif element == "id":
                    target_tag = soup.find(tag_name, id=content_method)
                    if target_tag:
                        return clean_text(target_tag.get_text())

                # 特定の要素が見つからない場合、別の方法を試みる（例：mainタグやarticleタグ）
                main_content = soup.find('main')
                if main_content:
                    return clean_text(main_content.get_text())

                article_content = soup.find('article')
                if article_content:
                    return clean_text(article_content.get_text())

                # 最後に、記事の主要なテキストを何とか取得できなかった場合
                print(f"⚠️ 本文が見つかりませんでした (URL: {url})")
                return None

    except Exception as e:
        print(f"⚠️ エラー: {str(e)}")
        return None
