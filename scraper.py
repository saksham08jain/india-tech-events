#!/usr/bin/env python3
"""India tech events scraper — Konfhub, Townscript, Devfolio.
Writes data/events.json + data/communities.json. Stdlib only (cron-safe).
Sources fail independently; one dead source never kills the run."""
import json, re, sys, time, html
import urllib.request, urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "en-IN,en;q=0.9"}
TECH_KW = ["tech","dev","python","javascript","java","ai ","ml","machine learning","data","cloud","devops",
           "startup","robotics","blockchain","cyber","web3","web 3","react","golang","rust","product",
           "design","hackathon","meetup","developer","engineering","linux","kubernetes","docker","api",
           "fintech","llm","genai","generative","opensource","open source","saas","flutter","node","scala",
           "qiskit","quantum","frontend","backend","fullstack","full stack","ui/ux","qa","sre","aws","azure","gcp"]
CITY_MAP = {"bangalore":"bengaluru","bengaluru":"bengaluru","mumbai":"mumbai","delhi":"delhi","new delhi":"delhi",
            "gurugram":"gurugram","gurgaon":"gurugram","noida":"noida","hyderabad":"hyderabad","pune":"pune",
            "chennai":"chennai","kolkata":"kolkata","ahmedabad":"ahmedabad","jaipur":"jaipur","indore":"indore",
            "kochi":"kochi","coimbatore":"coimbatore","goa":"goa","chandigarh":"chandigarh","online":"online",
            "remote":"online","virtual":"online"}
SPAM_PAT = re.compile(r"casino|pharma|lorazepam|xanax|viagra|essay|assignment|crypto doubl|forex|bet\b|porn|dating|replica|seo serv", re.I)
NOW = datetime.now(timezone.utc)

def esc(s): pass  # placeholder guard (build.py defines its own)

def clean(s):
    s = html.unescape(str(s or ""))
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")

def norm_city(raw):
    c = (raw or "").lower().strip()
    for k, v in CITY_MAP.items():
        if k in c: return v
    return "other-india" if c else "unknown"

def is_tech(text):
    t = (text or "").lower()
    return any(k in t for k in TECH_KW) and not SPAM_PAT.search(text or "")

def parse_date(raw):
    if not raw: return None
    raw = raw.replace("Z", "+00:00")
    try: return datetime.fromisoformat(raw).astimezone(timezone.utc).isoformat()
    except ValueError: return None

events = {}   # key: (source, url)
warnings = []

# ---------- TOWNSCRIPT ----------
# debt: townscript.com is an Angular SPA — event pages are shells w/o data, listing API needs session cookies.
# Re-enable via browser-tool session capture or their public API when available.
def scrape_townscript(limit_pages=70):
    return {}

# ---------- ALLEVENTS ----------
def scrape_allevents():
    out = {}
    cities = ["bangalore","delhi","mumbai","pune","hyderabad","chennai","kolkata","gurugram","noida","indore","jaipur","kochi"]
    for city in cities:
        for page_n in (1, 2):
            url = f"https://allevents.in/{city}/technology" + (f"?page={page_n}" if page_n > 1 else "")
            try:
                page = fetch(url)
                blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
                found = 0
                for b in blocks:
                    try:
                        d = json.loads(b)
                    except Exception:
                        continue
                    items = d if isinstance(d, list) else [d]
                    for it in items:
                        if not isinstance(it, dict) or it.get("@type") != "Event": continue
                        u = it.get("url") or ""
                        if not u or ("allevents", u) in out: continue
                        start = parse_date(it.get("startDate"))
                        if not start or datetime.fromisoformat(start) < NOW: continue
                        loc = it.get("location") or {}
                        addr = loc.get("address") if isinstance(loc, dict) else {}
                        city_raw = (addr or {}).get("addressLocality") if isinstance(addr, dict) else ""
                        if not city_raw:
                            city_raw = city  # fall back to the browse-page city slug
                        name = clean(it.get("name"))
                        if not name or SPAM_PAT.search(name): continue
                        org = it.get("organizer")
                        if isinstance(org, list) and org and isinstance(org[0], dict):
                            org = org[0].get("name","")
                        elif isinstance(org, dict):
                            org = org.get("name","")
                        if not is_tech(name + " " + clean(it.get("description",""))):
                            continue
                        out[("allevents", u)] = {
                            "source":"allevents","title":name,"url":u,"start":start,
                            "end":parse_date(it.get("endDate")),"city":norm_city(str(city_raw)),
                            "city_raw":clean(str(city_raw)),"venue":clean(loc.get("name") if isinstance(loc,dict) else ""),
                            "organizer":clean(org),
                            "description":clean(it.get("description",""))[:500],
                            "online": "online" in norm_city(str(city_raw)) or "virtual" in str(loc).lower(),
                            "scraped_at": NOW.isoformat()}
                        found += 1
                if page_n == 1 and found == 0:
                    break  # dead category page, skip pagination
                time.sleep(0.5)
            except Exception as e:
                warnings.append(f"allevents {city} p{page_n}: {e}")
                break
    return out

# ---------- KONFHUB ----------
# debt: /events renders client-side (no SSR data); use konfhub's public explore API when found
def scrape_konfhub(limit_pages=40):
    return {}

# ---------- DEVFOLIO (hackathons) ----------
def scrape_devfolio():
    out = {}
    try:
        page = fetch("https://devfolio.co/hackathons")
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page, re.S)
        if not m: warnings.append("devfolio: no NEXT_DATA"); return out
        data = json.loads(m.group(1))
        found = []
        def walk(o):
            if isinstance(o, dict):
                if o.get("slug") and o.get("name") and (o.get("starts_at") or o.get("start_date")):
                    found.append(o)
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(data)
        for h in found:
            u = "https://devfolio.co/hackathons/" + h["slug"]
            start = parse_date(h.get("starts_at") or h.get("start_date"))
            if not start or datetime.fromisoformat(start) < NOW: continue
            city_raw = h.get("location") or h.get("city") or ""
            out[("devfolio", u)] = {
                "source":"devfolio","title":clean(h["name"]),"url":u,"start":start,
                "end":parse_date(h.get("ends_at") or h.get("end_date")),
                "city":norm_city(str(city_raw)),"city_raw":clean(str(city_raw)),
                "venue":"","organizer":"",
                "description":clean(str(h.get("tagline") or h.get("description") or ""))[:500],
                "online": bool(h.get("is_online")), "scraped_at": NOW.isoformat()}
    except Exception as e:
        warnings.append(f"devfolio: {e}")
    return out

def main():
    for fn in (scrape_townscript, scrape_allevents, scrape_konfhub, scrape_devfolio):
        t0 = time.time()
        try:
            res = fn()
            events.update(res)
            print(f"{fn.__name__}: {len(res)} events ({time.time()-t0:.0f}s)")
        except Exception as e:
            warnings.append(f"{fn.__name__} crashed: {e}")
            print(f"{fn.__name__} CRASHED: {e}")
    # merge with previous runs (dedupe by url, keep newest scrape)
    prev_path = DATA / "events.json"
    if prev_path.exists():
        for e in json.loads(prev_path.read_text()):
            if isinstance(e, dict) and e.get("source") and e.get("url"):
                events.setdefault((e["source"], e["url"]), e)
    all_events = list(events.values())
    # drop stale (ended >7d ago)
    fresh = []
    for e in all_events:
        try:
            if datetime.fromisoformat(e["start"]) >= NOW.replace(hour=0): fresh.append(e)
        except Exception: pass
    fresh.sort(key=lambda e: e["start"])
    # communities = organizers
    communities = {}
    for e in fresh:
        org = e.get("organizer","").strip()
        if org and len(org) < 80:
            c = communities.setdefault(org, {"name":org, "cities":set(), "events":[], "links":set()})
            c["cities"].add(e["city"]); c["events"].append(e["url"]); c["links"].add(e["source"])
    comm_list = [{"name":k, "cities":sorted(v["cities"]), "event_count":len(v["events"]),
                  "sources":sorted(v["links"]), "upcoming":v["events"][:5]} for k,v in
                 sorted(communities.items(), key=lambda kv:-len(kv[1]["events"]))]
    (DATA / "events.json").write_text(json.dumps(fresh, indent=1))
    (DATA / "communities.json").write_text(json.dumps(comm_list, indent=1))
    print(f"TOTAL upcoming: {len(fresh)} | communities: {len(comm_list)}")
    for w in warnings: print("WARN:", w)

if __name__ == "__main__":
    main()
