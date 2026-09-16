
import json, math
from pathlib import Path
from datetime import datetime, timezone

PATH=Path("data/demand_history.json")
PATH.parent.mkdir(exist_ok=True)

def load():
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save(x):
    PATH.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8")

def zscore(current, history):
    if len(history)<3:
        return 0.0
    mean=sum(history)/len(history)
    var=sum((x-mean)**2 for x in history)/len(history)
    sd=math.sqrt(var)
    if sd==0:
        return 0.0
    return (current-mean)/sd

def update(clusters):
    """
    clusters: {product_key: mention_count_for_this_run}
    Returns enriched records with spike score 0-100.
    """
    h=load()
    now=datetime.now(timezone.utc).isoformat()
    out={}
    for key,current in clusters.items():
        rec=h.get(key,{"counts":[]})
        hist=rec.get("counts",[])
        z=zscore(current,hist[-30:])
        previous=hist[-1] if hist else 0
        growth=(current-previous)/max(previous,1)
        spike=min(100,max(0,50+z*15+growth*25))
        out[key]={"current":current,"previous":previous,
                  "growth":round(growth,3),"zscore":round(z,2),
                  "spike_score":round(spike,1)}
        hist=(hist+[current])[-30:]
        h[key]={"counts":hist,"last_seen":now}
    save(h)
    return out
