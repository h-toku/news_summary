# news_sitesのキーをURLにする
news_sites = {
    "https://jp.reuters.com/": { "tag":"script","element":"id", "content_method": "fusion_metadata"},
    "https://www.cnn.co.jp/": { "tag":"span","element":"class", "content_method": "credit"},
    "https://www.bloomberg.co.jp/": { "tag":"script","element":"type", "content_method": "application/ld+json"},
    "https://www.nikkei.com/": { "tag":"p","element":"class", "content_method": "paragraph_p18mfke4"},
    "https://www.asahi.com/": { "tag":"","element":"", "content_method": ""},
    "https://www.yomiuri.co.jp/": { "tag":"","element":"", "content_method": ""},
    "https://www.jiji.com/jc/": { "tag":"","element":"", "content_method": ""},  
    "https://japan.cnet.com/" : { "tag":"div","element":"id", "content_method": "NWrelart:Body"},
    "https://prtimes.jp/"   : { "tag":"script","element":"id", "content_method": "__NEXT_DATA__"},
    "https://forbesjapan.com/" : { "tag":"div","element":"class", "content_method": "article-content*****"},
    "https://news.golfdigest.co.jp/" : { "tag":"div","element":"class", "content_method": "article_body"},
}
