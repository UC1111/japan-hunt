import csv
from pathlib import Path

import db
from config import SEARCH_QUERIES,NEWS_QUERIES,POKEMON_CENTER_URLS
from reddit import collect_queries
from news_sources import collect_news
from pokemon_center import fetch_all
from scorer import intent,scarcity,exclusive,stock,score,label
from price_sources import cached_ebay_median, safe_price_gap
from demand_spike import update as update_spikes

def demand(n):
    return min(100,n*15)

def report(products,mentions,spikes):
    rows=[]
    for p in products:
        pname=p["name"].lower()
        matched=[]
        for k,n in mentions.items():
            tok=[x for x in k.split() if len(x)>=4]
            overlap=sum(x in pname for x in tok)
            if overlap>=2 or (len(tok)==1 and tok[0] in pname):
                matched.append((k,n))

        cnt=sum(n for _,n in matched)
        d=demand(cnt)
        text=" ".join(k for k,_ in matched)
        i=intent(text)
        sc=scarcity(text)
        ex=exclusive(text)
        st=stock(p["availability"])

        overseas_usd=None
        overseas_jpy=None
        gap=0
        gap_pct=None
        sample=0
        source="none"

        if cnt >= 1:
            try:
                overseas_usd, sample, source = cached_ebay_median(p["name"])
                if overseas_usd:
                    gap, overseas_jpy, gap_pct = safe_price_gap(
                        p["price_jpy"], overseas_usd
                    )
            except Exception as e:
                print(f"Price lookup failed for {p['name']}: {e}")
                source="error"

        x=score(d,i,sc,ex,gap,st)
        spike=0
        if matched:
            spike=max(
                [spikes.get(k,{}).get("spike_score",0) for k,_ in matched],
                default=0
            )

        final_score=round(x*0.85 + spike*0.15)

        rows.append({
            "score":final_score,
            "base_score":x,
            "demand_spike":spike,
            "label":label(final_score,d,i,st),
            "demand_count":cnt,
            "demand":d,
            "purchase_intent":i,
            "scarcity":sc,
            "japan_exclusive":ex,
            "price_gap":gap,
            "japan_price_jpy":p["price_jpy"],
            "overseas_median_usd":overseas_usd,
            "overseas_median_jpy":overseas_jpy,
            "price_source":source,
            "price_sample":sample,
            "price_gap_percent":round(gap_pct,1) if gap_pct is not None else None,
            "stock":st,
            "name":p["name"],
            "availability":p["availability"],
            "url":p["url"]
        })

    return sorted(rows,key=lambda x:x["score"],reverse=True)

def main():
    db.init_db()

    print("[1/5] Reddit demand")
    reddit_mentions=collect_queries(SEARCH_QUERIES)
    for m in reddit_mentions:
        db.save_mention(m)
    print("Reddit mentions:",len(reddit_mentions))

    print("[2/5] Google News demand")
    news_mentions=collect_news(NEWS_QUERIES)
    for m in news_mentions:
        db.save_mention(m)
    print("News mentions:",len(news_mentions))

    mc=db.get_mention_counts()
    spikes=update_spikes(mc)
    print("clusters:",len(mc))

    print("[3/5] Pokémon Center")
    try:
        ps=fetch_all(POKEMON_CENTER_URLS)
        for p in ps:
            db.upsert_product(p.__dict__)
        print("products:",len(ps))
    except Exception as e:
        print("Pokémon Center unavailable:",e)
        print("Using previously stored products from SQLite.")

    stored_products=db.get_products()
    if len(stored_products)<5:
        print("No stored products available; cannot build opportunity report yet.")
        return
    print("stored products:",len(stored_products))

    print("[4/5] scoring + overseas price")
    rows=report(stored_products,mc,spikes)

    print("[5/5] CSV")
    out=Path("data/opportunities.csv")
    out.parent.mkdir(exist_ok=True)
    with out.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys() if rows else ["score"])
        w.writeheader()
        w.writerows(rows)

    for r in rows[:10]:
        us = r["overseas_median_usd"]
        us_text = f"${us:.2f}" if us is not None else "—"
        print(
            f'{r["score"]:3} {r["label"]:15} '
            f'{r["name"][:45]} | JP ¥{r["japan_price_jpy"]:,.0f} '
            f'| US {us_text} | source={r["price_source"]}'
        )

if __name__=="__main__":
    main()
