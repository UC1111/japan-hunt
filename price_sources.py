
import json, re, time, hashlib
from pathlib import Path
from statistics import median
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

UA = "Mozilla/5.0 JapanHuntMVP/0.3"
CACHE = Path("data/price_cache.json")
CACHE.parent.mkdir(exist_ok=True)

def _load():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save(x):
    CACHE.write_text(json.dumps(x, ensure_ascii=False, indent=2), encoding="utf-8")

def usd_to_jpy(usd, rate=150.0):
    return round(float(usd) * float(rate))

def extract_prices(text):
    out=[]
    for m in re.finditer(r'(?:US\$|\$)\s*([0-9][0-9,]*(?:\.[0-9]+)?)', text):
        try:
            x=float(m.group(1).replace(",",""))
            if 0 < x < 10000: out.append(x)
        except ValueError:
            pass
    return out

def ebay_search_prices(query):
    url="https://www.ebay.com/sch/i.html?_nkw="+quote_plus(query)
    r=requests.get(url,headers={"User-Agent":UA},timeout=20)
    r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    prices=[]
    for node in soup.select(".s-item__price"):
        prices += extract_prices(node.get_text(" ",strip=True))
    # Remove obvious junk/rare extreme outliers for a listing-price estimate.
    prices=[x for x in prices if 3 <= x <= 2000]
    return prices

def cached_ebay_median(query, ttl_hours=24):
    key=hashlib.sha256(query.strip().lower().encode()).hexdigest()
    cache=_load()
    now=time.time()
    old=cache.get(key)
    if old and now-old.get("ts",0) < ttl_hours*3600:
        return old.get("usd"), old.get("sample",0), "cache"

    try:
        prices=ebay_search_prices(query)
        if len(prices) < 3:
            return None, len(prices), "insufficient"

        # Winsorize the tails before taking the median.
        prices.sort()
        lo=prices[max(0,int(len(prices)*0.10)-1)]
        hi=prices[min(len(prices)-1,int(len(prices)*0.90))]
        trimmed=[min(max(x,lo),hi) for x in prices]
        value=round(median(trimmed),2)

        cache[key]={"ts":now,"usd":value,"sample":len(prices),"query":query}
        _save(cache)
        return value,len(prices),"live"
    except Exception as e:
        if old and old.get("usd") is not None:
            return old["usd"], old.get("sample",0), "stale"
        return None,0,"error"

def price_gap_score(japan_jpy, overseas_jpy):
    if not japan_jpy or not overseas_jpy or japan_jpy <= 0:
        return 0
    gap=(overseas_jpy-japan_jpy)/japan_jpy*100
    if gap <= 0: return 0
    if gap < 10: return 20
    if gap < 25: return 40
    if gap < 50: return 60
    if gap < 100: return 80
    return 100

def safe_price_gap(japan_jpy, usd, fx=150.0):
    """Returns (gap_score, overseas_jpy, gap_percent)."""
    if not usd or not japan_jpy:
        return 0,None,None
    overseas=usd_to_jpy(usd,fx)
    pct=(overseas-japan_jpy)/japan_jpy*100
    # Guard against parser failures / absurd price mismatches.
    if pct < -99 or pct > 5000:
        return 0,overseas,pct
    return price_gap_score(japan_jpy,overseas),overseas,pct
