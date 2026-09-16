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

def _fetch_html(url):
    # Direct first. Pokémon Center currently uses a WAF/Salesforce layer that
    # can return 403 to GitHub Actions. If that happens, use Jina Reader as a
    # read-only rendering fallback.
    try:
        r=requests.get(url,headers=H,timeout=30)
        r.raise_for_status()
        return r.text, url, "direct"
    except requests.HTTPError as e:
        if e.response is None or e.response.status_code != 403:
            raise
        print(f"Direct Pokémon Center fetch got 403: {url}")
    except requests.RequestException as e:
        print(f"Direct Pokémon Center fetch failed: {e}")

    proxy="https://r.jina.ai/http://"+url.split("://",1)[1]
    r=requests.get(
        proxy,
        headers={"User-Agent":"JapanHuntMVP/0.5"},
        timeout=60
    )
    r.raise_for_status()
    return r.text, url, "jina"

def markdown_products(text,base):
    # Jina Reader returns markdown/text. Product listing pages commonly contain
    # product names followed by yen prices. Extract linked product rows first.
    out=[]
    seen=set()

    # Markdown links whose visible text is the product name.
    for m in re.finditer(r"\[([^\]]{3,200})\]\((https?://[^)]+)\)", text):
        name=re.sub(r"\s+"," ",m.group(1)).strip()
        u=m.group(2)
        # Inspect a small window after the link for a yen price.
        window=text[m.end():m.end()+500]
        pm=re.search(r"([0-9][0-9,]*)\s*円",window)
        if not pm:
            # Sometimes price precedes the link.
            window2=text[max(0,m.start()-250):m.start()]
            pm=re.search(r"([0-9][0-9,]*)\s*円",window2)
        if not pm:
            continue
        p=float(pm.group(1).replace(",",""))
        if not name or p<=0 or u in seen:
            continue
        if "ポケモン" not in name and "Pokémon" not in name and "Pokemon" not in name:
            continue
        seen.add(u)
        # Determine stock from a local window around the product.
        around=text[max(0,m.start()-150):m.end()+300]
        a=avail(around)
        out.append(PokemonProduct(
            u,name,p,urljoin(base,u),"",a
        ))

    # Fallback: parse plain text lines with a product-like name and a yen price.
    if len(out)<5:
        lines=[re.sub(r"\s+"," ",x).strip() for x in text.splitlines()]
        for i,line in enumerate(lines):
            pm=re.search(r"([0-9][0-9,]*)\s*円",line)
            if not pm:
                continue
            p=float(pm.group(1).replace(",",""))
            name=re.sub(r"[*_`#>\[\](){}]","",line[:pm.start()]).strip(" -|:")
            if len(name)<4 or len(name)>180:
                continue
            if name in seen:
                continue
            around=" ".join(lines[max(0,i-2):min(len(lines),i+3)])
            if "ポケモン" not in name and "Pokémon" not in name and "Pokemon" not in name:
                continue
            pid="seed-"+str(abs(hash(name)))
            seen.add(name)
            out.append(PokemonProduct(pid,name,p,base,"",avail(around)))

    return out

def fetch(url):
    html,base,source=_fetch_html(url)
    if source=="direct":
        s=BeautifulSoup(html,"html.parser")
        p=jsonld(s,url)
        if len(p)<5:
            p=html_products(s,url)
    else:
        # Jina's reader output is already human-readable markdown/text.
        p=markdown_products(html,url)

    if len(p)<5:
        raise RuntimeError(
            f"scraper validation failed: {len(p)} products (source={source})"
        )
    print(f"Pokémon Center source={source}, products={len(p)}")
    return p

def fetch_all(urls):
    all={}
    errors=[]
    for u in urls:
        try:
            for p in fetch(u):
                all[p.product_id]=p
        except Exception as e:
            errors.append(f"{u}: {e}")
            print("Pokémon source failed:",e)

    if len(all)<5:
        raise RuntimeError(
            "global scraper validation failed; no usable Pokémon products. "
            + " | ".join(errors)
        )
    return list(all.values())
