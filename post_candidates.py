
import csv
from pathlib import Path

def make(rows, limit=3):
    candidates=[]
    for r in rows:
        if r.get("score",0) < 80: continue
        if r.get("demand_spike",0) < 55 and r.get("demand_count",0) < 2: continue
        if r.get("stock",0) < 50: continue
        name=r["name"]
        jp=f'¥{int(r["japan_price_jpy"]):,}'
        us=f'${r["overseas_median_usd"]:.2f}' if r.get("overseas_median_usd") else "—"
        gap=r.get("price_gap_percent")
        gap_text=f'{gap:+.0f}%' if gap is not None else "—"
        text=(
            f"🇯🇵 Japan find: {name}\n"
            f"Japan price: {jp}\n"
            f"Overseas listing median: {us} ({gap_text})\n"
            f"Demand signal: {r.get('demand_spike',0):.0f}/100\n"
            f"Check availability from Japan ↓\n{r['url']}"
        )
        candidates.append({"score":r["score"],"text":text,"url":r["url"]})
    return sorted(candidates,key=lambda x:x["score"],reverse=True)[:limit]

if __name__=="__main__":
    f=Path("data/opportunities.csv")
    if not f.exists(): raise SystemExit("Run main.py first.")
    with f.open(encoding="utf-8-sig",newline="") as fh:
        rows=list(csv.DictReader(fh))
    for x in make(rows):
        print("\n---\n"+x["text"])
