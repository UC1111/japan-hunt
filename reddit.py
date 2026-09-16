import hashlib,re,time,requests,feedparser

UA="JapanHuntMVP/0.1 (research bot)"

def normalize_product_key(text):
    text=re.sub(r"https?://\S+"," ",text.lower())
    text=re.sub(r"[^a-z0-9\s-]"," ",text)
    text=re.sub(r"\s+"," ",text).strip()
    stop={"where","can","i","buy","this","that","is","there","any","someone",
          "help","me","looking","for","please","want","need","japan",
          "japanese","pokemon","center","exclusive","proxy"}
    return " ".join(w for w in text.split() if w not in stop)[:160]

def collect_queries(queries,limit_per_query=50):
    out=[]
    for q in queries:
        r=requests.get(
            "https://www.reddit.com/search.rss",
            params={"q":q,"sort":"new","limit":limit_per_query},
            headers={"User-Agent":UA},timeout=20
        )
        r.raise_for_status()
        feed=feedparser.parse(r.text)
        for e in feed.entries:
            title=e.get("title","")
            summary=re.sub("<[^>]+>"," ",e.get("summary",""))
            raw=f"{title} {summary}"
            key=normalize_product_key(raw)
            if not key: continue
            ident=e.get("id",e.get("link",raw))
            out.append({
                "id":hashlib.sha1(ident.encode()).hexdigest(),
                "title":title,"text":summary,"url":e.get("link",""),
                "created_utc":time.time(),"query":q,"product_key":key
            })
    return out
