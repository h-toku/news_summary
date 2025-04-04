# news_sitesのキーをURLにする
news_sites = {
    "https://jp.reuters.com/": {"field": "div.article-body", "html_element": "meta[name='description']"},
    "https://news.golfdigest.co.jp/": {"field": "article_body", "html_element": "article p"},
    "https://siteC.com": {"field": "content", "html_element": "article p"},
    "https://siteD.com": {"field": "content", "html_element": "div.article-body"},
    "https://siteE.com": {"field": "content", "html_element": "section.article-body"},
}
