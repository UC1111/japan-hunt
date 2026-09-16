from dataclasses import dataclass
import json,re,requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

H={
    "User-Agent":"Mozilla/5.0 JapanHuntMVP/0.1",
    "Accept-Language":"ja-JP,ja;q=0.9,en;q=0.8"
}

@dataclass
class PokemonProduct:
    product_id:str
    name:str
    price_jpy:float
    url:str
    image:str
    availability:str="unknown"
    is_new:bool=False
    is_restock:bool=False
    is_preorder:bool=False

def price(v):
    if v is None:return None
    m=re.search(r"([0-9][0-9,]*)",str(v))
    return float(m.group(1).replace(",","")) if m else None

def avail(t):
    t=t.lower()
    if "在庫あり" in t or "in stock" in t:return "in_stock"
    if "予約" in t or "pre-order" in t or "preorder" in t:return "preorder"
    if "再入荷" in t or "restock" in t:return "restock"
    if "sold out" in t or "売り切れ" in t or "在庫なし" in t:return "sold_out"
    return "unknown"

def jsonld(soup,base):
    out=[]
    for sc in soup.select('script[type="application/ld+json"]'):
        try:d=json.loads(sc.string or sc.get_text())
        except Exception:continue
        for o in (d if isinstance(d,list) else [d]):
            if not isinstance(o,dict) or o.get("@type")!="Product":continue
            off=o.get("offers",{})
            if isinstance(off,list):off=off[0] if off else {}
            n=str(o.get("name","")).strip()
            p=price(off.get("price"))
            u=urljoin(base,o.get("url",""))
            im=o.get("image","")
            if isinstance(im,list):im=im[0] if im else ""
            if n and p and u:
                out.append(PokemonProduct(
                    str(o.get("sku") or o.get("productID") or u),
                    n,p,u,str(im),
                    avail(str(off.get("availability","")))
                ))
    return out

def html_products(soup,base):
    selectors=[
        "[data-pid]","[data-product-id]",".product-tile",".product-item",
        ".product-card","li[class*='product']","article[class*='product']"
    ]
    out=[];seen=set()
    for sel in selectors:
        for n in soup.select(sel):
            nn=n.select_one("[class*='name'],[class*='title'],h2,h3,h4,a")
            pp=n.select_one("[class*='price'],[data-price],.price")
            a=n.select_one("a[href]")
            name=nn.get_text(" ",strip=True) if nn else ""
            pv=pp.get("data-price") if pp else None
            pv=price(pv) if pv else price(pp.get_text(" ",strip=True) if pp else None)
            u=urljoin(base,a.get("href")) if a else ""
            pid=str(n.get("data-pid") or n.get("data-product-id") or u)
            if not name or not pv or not u or pid in seen:continue
            seen.add(pid)
            im=n.select_one("img[src],img[data-src]")
            out.append(PokemonProduct(
                pid,name,pv,u,
                (im.get("src") or im.get("data-src") or "") if im else "",
                avail(n.get_text(" ",strip=True))
            ))
    return out

def fetch(url):
    r=requests.get(url,headers=H,timeout=30)
    r.raise_for_status()
    s=BeautifulSoup(r.text,"html.parser")
    p=jsonld(s,url)
    if len(p)<5:p=html_products(s,url)
    if len(p)<5:
        raise RuntimeError(f"scraper validation failed: {len(p)} products")
    return p

def fetch_all(urls):
    all={}
    for u in urls:
        for p in fetch(u):all[p.product_id]=p
    if len(all)<5:raise RuntimeError("global scraper validation failed")
    return list(all.values())
