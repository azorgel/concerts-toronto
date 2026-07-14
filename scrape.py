import re
import json
import html as html_module
import urllib.request
import urllib.error
import ssl
import sys

URL = "https://concertsto.com/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        return resp.read().decode("utf-8")

def parse(content):
    start = content.find("<tbody>")
    end = content.find("</tbody>") + len("</tbody>")
    tbody = content[start:end]

    rows = re.split(r"(?=<tr[\s>])", tbody)

    current_date = ""
    concerts = []

    for row in rows:
        row = row.strip()
        if not row or not row.startswith("<tr"):
            continue

        if 'class="date"' in row and 'class="date-' not in row:
            current_date = re.sub(r"<[^>]+>", "", row).strip()
            continue

        if 'class="c"' in row or 'class="c odd"' in row:
            event_match = re.search(r'<td class="event">(.*?)</td>', row, re.DOTALL)
            if not event_match:
                continue
            event_html = event_match.group(1)

            artist_raw = re.split(r"<br", event_html)[0]
            artist = html_module.unescape(re.sub(r"<[^>]+>", "", artist_raw)).strip()

            venue_match = re.search(r'<span class="venue">(.*?)</span>', event_html)
            venue = html_module.unescape(re.sub(r"<[^>]+>", "", venue_match.group(1))).strip() if venue_match else ""

            price_match = re.search(r'class="price"[^>]*>(.*?)</td>', row)
            price = re.sub(r"<[^>]+>", "", price_match.group(1)).strip() if price_match else ""

            tickets = []
            for url, name in re.findall(r'href="([^"]+)"[^>]*class="s-\d+"[^>]*>(.*?)</a>', row):
                tickets.append({"url": html_module.unescape(url), "name": html_module.unescape(name)})

            concerts.append({
                "date": current_date,
                "artist": artist,
                "venue": venue,
                "price": price,
                "tickets": tickets,
            })

    return concerts

def build_html(concerts):
    venues = sorted(set(c["venue"] for c in concerts if c["venue"]))
    concerts_json = json.dumps(concerts, separators=(",", ":"))
    venues_json = json.dumps(venues)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<title>Toronto Concerts // ConcertsTO</title>
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<style>
*{{box-sizing:border-box}}
body{{font-family:arial,sans-serif;font-size:12px;color:#fff;background-color:#000;margin:0}}
a:link,a:visited{{color:#fff;text-decoration:none}}
h1{{font-size:16px;margin:0}}
.container{{margin:0 auto;max-width:960px}}
.header{{box-sizing:border-box;width:100%;padding:5px;color:#fff;background-color:#031ba1;text-shadow:1px 1px #222}}
.footer{{margin-bottom:20px;font-size:12px;color:#fff;padding:5px}}
.filter-bar{{position:sticky;top:0;z-index:10;background:#000;padding:8px 5px;border-bottom:1px solid #031ba1;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.filter-bar label{{color:#aaa;font-size:12px;white-space:nowrap}}
.filter-bar select{{background:#111;color:#fff;border:1px solid #031ba1;padding:4px 6px;font-size:12px;cursor:pointer;max-width:260px}}
.filter-bar input[type=text]{{background:#111;color:#fff;border:1px solid #031ba1;padding:4px 6px;font-size:12px;width:160px;outline:none}}
.filter-bar input[type=text]::placeholder{{color:#555}}
#result-count{{color:#aaa;font-size:12px;margin-left:auto}}
#c{{width:100%;margin:10px 0;font-size:14px;border-collapse:collapse;border:0}}
#c td,#c th{{padding:5px;text-align:left;border:0}}
#c th{{color:#fff;font-weight:bold;text-transform:uppercase;vertical-align:top;white-space:nowrap}}
#c tr.odd{{background-color:#222}}
#c tr.date{{background-color:#ddd;color:#000;text-shadow:1px 1px #fff}}
#c tr.date td{{font-weight:bold}}
#c tr.date-t,#c tr.date-b{{height:10px}}
#c td.event{{width:80%}}
#c td.event .venue{{color:#999;font-size:12px}}
#c th.price{{width:10%}}
#c td.tickets{{width:10%}}
.tickets a{{padding:2px;text-align:center;font-size:10px;display:block;text-decoration:none;text-shadow:1px 1px #222;white-space:nowrap}}
.tickets p{{margin-top:0;margin-bottom:5px}}
.tickets p:last-child{{margin-bottom:0}}
.tickets a:hover{{background-color:#ddd;color:#000;text-shadow:1px 1px #fff}}
.s-4{{background-color:#9933ff}}
.s-5{{background-color:#031ba1}}
.s-14{{background-color:#00BA22}}
.s-16{{background-color:#f90}}
.s-18{{background-color:#33f3ff}}
.s-other{{background-color:#555}}
.no-results{{padding:20px;color:#888;text-align:center;font-size:14px}}
</style>
</head>
<body>
<div class="header">
  <div class="container">
    <h1>Toronto Concerts</h1>
  </div>
</div>
<div class="container">
  <div class="filter-bar">
    <label for="venue-select">Venue:</label>
    <select id="venue-select"><option value="">All Venues</option></select>
    <label for="artist-search">Search:</label>
    <input type="text" id="artist-search" placeholder="Artist or venue...">
    <span id="result-count"></span>
  </div>
  <table id="c">
    <thead><tr class="h"><th>Event</th><th class="price">Price</th><th>Tickets</th></tr></thead>
    <tbody id="concert-tbody"></tbody>
  </table>
  <div id="no-results" class="no-results" style="display:none">No concerts found.</div>
</div>
<div class="container footer">
  Data sourced from <a href="https://concertsto.com/" target="_blank">ConcertsTO</a>
</div>
<script>
const CONCERTS={concerts_json};
const VENUES={venues_json};
const venueSelect=document.getElementById('venue-select');
const artistSearch=document.getElementById('artist-search');
const tbody=document.getElementById('concert-tbody');
const resultCount=document.getElementById('result-count');
const noResults=document.getElementById('no-results');
VENUES.forEach(v=>{{const o=document.createElement('option');o.value=v;o.textContent=v;venueSelect.appendChild(o);}});
function esc(s){{return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}
function tcls(n){{n=n.toLowerCase();if(n.includes('ticketmaster')||n.includes('ticketweb'))return 's-4';if(n.includes('ticketnetwork'))return 's-14';if(n.includes('waitf'))return 's-16';if(n.includes('songkick'))return 's-5';if(n.includes('eventbrite'))return 's-18';return 's-other';}}
function render(){{
  const vf=venueSelect.value,sf=artistSearch.value.toLowerCase().trim();
  const filtered=CONCERTS.filter(c=>{{
    if(vf&&c.venue!==vf)return false;
    if(sf&&!(c.artist+' '+c.venue).toLowerCase().includes(sf))return false;
    return true;
  }});
  if(!filtered.length){{tbody.innerHTML='';noResults.style.display='block';resultCount.textContent='0 concerts';return;}}
  noResults.style.display='none';
  resultCount.textContent=filtered.length+' concert'+(filtered.length!==1?'s':'');
  let h='',lastDate='',odd={{}};
  filtered.forEach(c=>{{
    if(c.date!==lastDate){{h+=`<tr class="date-t"><td colspan="3"></td></tr><tr class="date"><td colspan="3">${{esc(c.date)}}</td></tr><tr class="date-b"><td colspan="3"></td></tr>`;lastDate=c.date;odd[c.date]=0;}}
    const isOdd=odd[c.date]++%2===1;
    const tk=(c.tickets||[]).map(t=>`<p><a href="${{esc(t.url)}}" rel="nofollow" class="${{tcls(t.name)}}" target="_blank">${{esc(t.name)}}</a></p>`).join('');
    h+=`<tr class="${{isOdd?'c odd':'c'}}"><td class="event">${{esc(c.artist)}}<br/><span class="venue">${{esc(c.venue)}}</span></td><td>${{esc(c.price)}}</td><td class="tickets">${{tk}}</td></tr>`;
  }});
  tbody.innerHTML=h;
}}
venueSelect.addEventListener('change',render);
artistSearch.addEventListener('input',render);
render();
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("Fetching concerts...")
    try:
        content = fetch()
    except Exception as e:
        print(f"Failed to fetch: {e}", file=sys.stderr)
        sys.exit(1)

    concerts = parse(content)
    print(f"Parsed {len(concerts)} concerts")

    html = build_html(concerts)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote index.html")
