#!/usr/bin/env python3
"""Static site generator: data/*.json -> site/ (index, city pages, event pages, communities, sitemap, robots)."""
import json, html, re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
DATA, SITE = ROOT / "data", ROOT / "site"
BRAND = "IndiaTechCalendar"   # placeholder pending domain decision
CSS = """body{background:#0b0e14;color:#e8ecf1;font-family:ui-sans-serif,system-ui,sans-serif;margin:0;line-height:1.6}
.wrap{max-width:960px;margin:0 auto;padding:0 20px}header{border-bottom:1px solid #232b3b;padding:20px 0}
.logo{font-weight:800;letter-spacing:-.02em;text-decoration:none;color:#e8ecf1;font-size:20px}.logo b{color:#5eead4}
.meta{color:#8b94a3;font-size:13px}h1{font-size:clamp(26px,4vw,38px);letter-spacing:-.02em;margin:28px 0 8px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;margin:24px 0}
.card{background:#131824;border:1px solid #232b3b;border-radius:10px;padding:16px;display:block;text-decoration:none;color:inherit}
.card:hover{border-color:#5eead4}.card h3{margin:0 0 6px;font-size:15px}.card p{margin:0;color:#8b94a3;font-size:13px}
.tag{color:#5eead4;font-size:11px;text-transform:uppercase;letter-spacing:.08em}
.city{display:inline-block;background:#131824;border:1px solid #232b3b;border-radius:99px;padding:6px 14px;margin:4px 6px 0 0;color:#8b94a3;text-decoration:none;font-size:13px}
.city:hover{border-color:#5eead4;color:#e8ecf1}footer{border-top:1px solid #232b3b;margin-top:40px;padding:24px 0;color:#8b94a3;font-size:13px}
.pill{display:inline-block;font-size:11px;border:1px solid #5eead4;color:#5eead4;border-radius:99px;padding:2px 10px;margin-left:8px}"""

def esc(s): return html.escape(str(s or ""))
def slugify(s): return re.sub(r"[^a-z0-9-]","",(s or "").lower().replace(" ","-"))[:80] or "x"
def fmt_date(iso):
    try: return datetime.fromisoformat(iso).strftime("%a, %d %b %Y · %H:%M UTC")
    except Exception: return iso

def page(title, desc, body, path):
    SITE.joinpath(path).parent.mkdir(parents=True, exist_ok=True)
    SITE.joinpath(path).write_text(f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}"><style>{CSS}</style></head><body>
<header><div class="wrap"><a class="logo" href="/"><b>{BRAND}</b> — India tech events</a></div></header>
<div class="wrap">{body}</div>
<footer><div class="wrap">Aggregated automatically from public event platforms. Owned by the event organizers; listing is informational. <a style="color:#5eead4" href="/communities.html">Communities</a></div></footer>
</body></html>""")

def event_card(e):
    tag = "ONLINE" if e.get("online") else esc(e["city"])
    return f'<a class="card" href="/event/{slugify(e["title"])}.html"><span class="tag">{tag}</span><h3>{esc(e["title"][:90])}</h3><p>{fmt_date(e["start"])}</p><p>{esc((e.get("organizer") or "")[:60])}</p></a>'

def main():
    events = json.loads((DATA / "events.json").read_text())
    communities = json.loads((DATA / "communities.json").read_text())
    SITE.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    upcoming = [e for e in events if datetime.fromisoformat(e["start"]) >= now]
    cities = {}
    for e in upcoming: cities.setdefault(e["city"], []).append(e)

    # index
    body = f'<h1>Upcoming tech events in India</h1><p class="meta">{len(upcoming)} upcoming events · {len(cities)} cities · auto-updated daily · {now.strftime("%d %b %Y")}</p>'
    for c in sorted(cities, key=lambda c: -len(cities[c])):
        if len(cities[c]) < 1: continue
        body += f'<h2 style="font-size:20px;margin:24px 0 4px">{esc(c).title()} <span class="pill">{len(cities[c])}</span></h2><div class="grid">'
        body += "".join(event_card(e) for e in cities[c][:12]) + "</div>"
    page("India Tech Events — Upcoming Hackathons, Meetups, Conferences", "Every upcoming India tech event: hackathons, meetups, conferences, workshops. Auto-updated daily.", body, "index.html")

    # city pages
    for c, evs in cities.items():
        b = f'<h1>Tech events in {esc(c).title()}</h1><p class="meta">{len(evs)} upcoming</p><div class="grid">' + "".join(event_card(e) for e in evs) + "</div>"
        page(f"Tech Events in {c.title()} — Upcoming {now.year}", f"All upcoming tech events, meetups and hackathons in {c.title()}, India. Updated daily.", b, f"city/{c}.html")

    # event pages (indexable detail pages)
    for e in upcoming:
        s = slugify(e["title"])
        ld = json.dumps({"@context":"https://schema.org","@type":"Event","name":e["title"],"startDate":e["start"],
                         "eventAttendanceMode":"https://schema.org/OnlineEventAttendanceMode" if e.get("online") else "https://schema.org/OfflineEventAttendanceMode",
                         "location":{"@type":"Place","name":e.get("venue") or e["city"]},"url":e["url"],
                         "organizer":{"@type":"Organization","name":e.get("organizer") or BRAND}})
        b = (f'<h1>{esc(e["title"])}</h1><p class="meta">{fmt_date(e["start"])} · {esc(e["city"].title())}{(" · "+esc(e["venue"])) if e.get("venue") else ""}</p>'
             f'<p>{esc(e.get("description",""))}</p><p style="margin-top:20px"><a class="city" href="{esc(e["url"])}">Register on {esc(e["source"])} →</a></p>'
             f'<script type="application/ld+json">{ld}</script>')
        page(f'{e["title"]} — {e["city"].title()} | {BRAND}', (e.get("description") or e["title"])[:150], b, f"event/{s}.html")

    # communities
    b = f'<h1>Indian tech communities & organizers</h1><p class="meta">{len(communities)} active organizers</p><div class="grid">'
    b += "".join(f'<div class="card"><h3>{esc(c["name"])}</h3><p>{c["event_count"]} upcoming · {esc(", ".join(c["cities"])[:60])}</p></div>' for c in communities[:100]) + "</div>"
    page("India Tech Communities Directory", "Active Indian tech communities and event organizers, ranked by upcoming events.", b, "communities.html")

    # sitemap + robots
    urls = ["index.html", "communities.html"] + [f"city/{c}.html" for c in cities] + [f"event/{slugify(e['title'])}.html" for e in upcoming]
    SITE.joinpath("sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
        "".join(f"<url><loc>/{{'{u}'}}</loc></url>" if False else f"<url><loc>/{u}</loc></url>" for u in urls) + "</urlset>")
    SITE.joinpath("robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")
    print(f"built: {len(upcoming)} events, {len(cities)} city pages, {len(communities)} communities -> site/")

if __name__ == "__main__":
    main()
