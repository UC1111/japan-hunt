import hashlib
import time
from urllib.parse import quote_plus

import feedparser
import requests

UA = "JapanHuntMVP/0.5 (read-only research bot)"
BASE = "https://news.google.com/rss/search"

def _normalize_product_key(text):
    # Reuse the same normalization logic without importing reddit.py,
    # so a Reddit outage cannot affect the News source.
    import re
    text=re.sub(r"https?://\S+"," ",text.lower())
    text=re.sub(r"[^a-z0-9\s-]"," ",text)
    text=re.sub(r"\s+"," ",text).strip()
    stop={"where","can","i","buy","this","that","is","there","any","someone",
          "help","me","looking","for","please","want","need","japan",
          "japanese","pokemon","center","exclusive","proxy"}
    return " ".join(w for w in text.split() if w not in stop)[:160]

def collect_news(queries, limit_per_query=20):
    out=[]
    for q in queries:
        try:
            params={
                "q":q,
                "hl":"en-US",
                "gl":"US",
                "ceid":"US:en",
            }
            r=requests.get(
                BASE,
                params=params,
                headers={"User-Agent":UA},
                timeout=20,
            )
            r.raise_for_status()
            feed=feedparser.parse(r.text)

            for e in feed.entries[:limit_per_query]:
                title=e.get("title","")
                summary=e.get("summary","")
                raw=f"{title} {summary}"
                key=_normalize_product_key(raw)
                if not key:
                    continue
                ident=e.get("id",e.get("link",raw))
                out.append({
                    "id":hashlib.sha1(("news:"+ident).encode()).hexdigest(),
                    "title":title,
                    "text":summary,
                    "url":e.get("link",""),
                    "created_utc":time.time(),
                    "query":q,
                    "product_key":key,
                })
        except Exception as e:
            print(f"Google News error: {q} -> {e}")
            print("Skipping this News query.")

        time.sleep(1)

    return out
