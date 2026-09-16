PURCHASE_TERMS={
"where can i buy":100,"where to buy":100,"i need this":90,
"looking for":80,"proxy":80,"buy from japan":80,
"available in japan":60,"does anyone know where":50}

SCARCITY_TERMS={
"impossible to find":100,"sold out everywhere":100,"hard to find":90,
"rare":90,"not available in my country":75,"limited":70,"discontinued":100}

def intent(t):
    t=t.lower()
    return max([v for k,v in PURCHASE_TERMS.items() if k in t],default=0)

def scarcity(t):
    t=t.lower()
    return max([v for k,v in SCARCITY_TERMS.items() if k in t],default=0)

def exclusive(t):
    t=t.lower()
    if "japan only" in t or "japan-exclusive" in t or "japan exclusive" in t:
        return 100
    if "pokemon center japan" in t:
        return 90
    if "japan first" in t:
        return 60
    return 20

def stock(s):
    return {
        "in_stock":100,"multiple_stores":100,"low_stock":70,
        "restock":50,"preorder":60,"lottery":40,"ending_soon":30,
        "sold_out":10,"discontinued":0,"unknown":0
    }.get(s,0)

def score(d,i,sc,e,g,s):
    return round(d*.25+i*.20+sc*.15+e*.15+g*.15+s*.10)

def label(x,d,i,s):
    if s<50:return "SOLD_OUT/WATCH"
    if x>=90 and d>=60 and i>=60:return "HOT"
    if x>=80 and d>=60 and i>=60:return "BUY SIGNAL"
    if x>=65:return "WATCH"
    return "IGNORE"
