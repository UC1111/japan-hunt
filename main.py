import csv
from pathlib import Path
import db
from config import SEARCH_QUERIES,POKEMON_CENTER_URLS
from reddit import collect_queries
from pokemon_center import fetch_all
from scorer import intent,scarcity,exclusive,stock,score,label
from price_sources import cached_ebay_median, safe_price_gap
from demand_spike import update as update_spikes

def demand(n):
    return min(100,n*15)

def report(products,mentions):
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

        # Only price-check products with some evidence of demand.
        if cnt >= 1:
            try:
                overseas_usd, sample, source = cached_ebay_median(p["name"])
                if overseas_usd:
                    gap, overseas_jpy, gap_pct = safe_price_gap(
                        p["price_jpy"], overseas_usd
                    )
            except Exception:
                pass

        x=score(d,i,sc,ex,gap,st)
        spike=spikes.get(matched[0][0],{}).get("spike_score",0) if matched else 0
        # Spike is a ranking signal, not a substitute for demand/stock/purchase intent.
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
            "price_source": source if cnt >= 1 else "none",
            "price_sample": sample if cnt >= 1 else 0,
            "price_gap_percent": round(gap_pct,1) if cnt >= 1 and gap_pct is not None else None,
            "stock":st,
            "name":p["name"],
            "availability":p["availability"],
            "url":p["url"]
        })
    return sorted(rows,key=lambda x:x["score"],reverse=True)

def main():
    db.init_db()

    print("[1/4] Reddit")
    mentions=collect_queries(SEARCH_QUERIES)
    for m in mentions:
        db.save_mention(m)
    mc=db.get_mention_counts()
    spikes=update_spikes(mc)
    print("mentions:",len(mentions),"clusters:",len(mc))

    print("[2/4] Pokémon Center")
    try:
        ps=fetch_all(POKEMON_CENTER_URLS)
    except Exception as e:
        print("SAFETY STOP:",e)
        return
    for p in ps:
        db.upsert_product(p.__dict__)
    print("products:",len(ps))

    print("[3/4] scoring + overseas price")
    rows=report(db.get_products(),mc)

    print("[4/4] CSV")
    out=Path("data/opportunities.csv")
    out.parent.mkdir(exist_ok=True)
    with out.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys() if rows else ["score"])
        w.writeheader()
        w.writerows(rows)

    for r in rows[:10]:
        print(
            f'{r["score"]:3} {r["label"]:15} '
            f'{r["name"][:45]} | JP ¥{r["japan_price_jpy"]:,.0f} '
            f'| US ${r["overseas_median_usd"] or 0}'
        )

if __name__=="__main__":
    main()
