"""小樹洞旅行誌 — 靜態網站產生器（只用 Python 標準函式庫）

  python build.py          產生網站到 dist/
  python build.py --serve  產生後在 http://localhost:8000 預覽

文章放在 content/posts/*.md，格式見 README.md。
"""
import datetime as dt
import html
import json
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "dist"
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
E = html.escape
VERSION = dt.datetime.now().strftime("%Y%m%d%H%M")

# ---------------------------------------------------------------- 內容讀取

def load_posts():
    posts = []
    for f in sorted((ROOT / "content" / "posts").glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
        if not m:
            sys.exit(f"{f.name}: 缺少 front matter")
        meta = json.loads(m.group(1))
        meta["body"] = m.group(2).strip()
        meta.setdefault("slug", f.stem)
        if meta.get("draft"):
            continue
        country = next(c for c in SITE["countries"] if c["slug"] == meta["country"])
        city = next(c for c in country["cities"] if c["slug"] == meta["city"])
        meta["_country"], meta["_city"] = country, city
        meta["url"] = f"/{country['slug']}/{city['slug']}/{meta['slug']}/"
        text = re.sub(r"\{\{.*?\}\}|[#>*\-\[\]()\s]|https?://\S+", "", meta["body"])
        meta["chars"] = len(text)
        meta["minutes"] = max(1, round(len(text) / 400))
        posts.append(meta)
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def klook_link(url):
    """Klook 連結自動帶上分潤 aid（若連結本身已是分潤連結則不動）。"""
    aid = SITE.get("klook_aid", "").strip()
    if not url or not aid or "affiliate.klook.com" in url or "aid=" in url:
        return url
    return url + ("&" if "?" in url else "?") + "aid=" + urllib.parse.quote(aid)

# ---------------------------------------------------------------- Markdown（精簡版）

def inline(s):
    s = E(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)",
               lambda m: f'<a href="{m.group(2)}"' + (' target="_blank" rel="noopener"' if m.group(2).startswith("http") else "") + f">{m.group(1)}</a>", s)
    return s


def credit(img):
    lic = E(img["license"])
    if img.get("license_url"):
        lic = f'<a href="{E(img["license_url"])}" target="_blank" rel="noopener license">{lic}</a>'
    return (f'攝影：{E(img["author"])}・{lic}・'
            f'<a href="{E(img["page"])}" target="_blank" rel="noopener">Wikimedia Commons</a>')


def figure(img, eager=False, cls=""):
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    cap = f'<span class="cap">{E(img["caption"])}</span>' if img.get("caption") else ""
    return (f'<figure class="fig {cls}"><button class="zoom" aria-label="放大圖片">'
            f'<img src="{E(img["src"])}" alt="{E(img.get("alt") or img.get("caption", ""))}" '
            f'width="{img["width"]}" height="{img["height"]}" {load} decoding="async"></button>'
            f'<figcaption>{cap}<span class="credit">{credit(img)}</span></figcaption></figure>')


def anchor(t):
    return E(re.sub(r"[^\w]+", "-", t).strip("-"))


def markdown(body, post):
    out = []
    for block in re.split(r"\n\s*\n", body):
        b = block.strip()
        if not b:
            continue
        if m := re.fullmatch(r"\{\{img:(\d+)\}\}", b):
            out.append(figure(post["images"][int(m.group(1)) - 1]))
        elif b == "{{klook}}":
            out.append(klook_box(post, inline_box=True))
        elif b.startswith("### "):
            out.append(f"<h3>{inline(b[4:])}</h3>")
        elif b.startswith("## "):
            t = b[3:]
            out.append(f'<h2 id="{anchor(t)}">{inline(t)}</h2>')
        elif b.startswith("> "):
            lines = [l[2:] if l.startswith("> ") else l for l in b.splitlines()]
            out.append(f'<aside class="tip"><span class="tip-label">小樹洞提醒</span><p>{"<br>".join(inline(l) for l in lines)}</p></aside>')
        elif all(l.startswith("- ") for l in b.splitlines()):
            out.append("<ul>" + "".join(f"<li>{inline(l[2:])}</li>" for l in b.splitlines()) + "</ul>")
        else:
            out.append(f"<p>{inline(' '.join(b.splitlines()))}</p>")
    return "\n".join(out)

# ---------------------------------------------------------------- 版型元件

LOGO = ('<svg class="logo-mark" viewBox="0 0 40 40" aria-hidden="true">'
        '<path d="M20 3c-7 0-12 5-12 11 0 3 1 5 3 7v14c0 1 1 2 2 2h14c1 0 2-1 2-2V21c2-2 3-4 3-7 0-6-5-11-12-11z" fill="currentColor"/>'
        '<ellipse cx="20" cy="25" rx="4.2" ry="5.4" fill="var(--paper)"/></svg>')


def head(title, desc, path, image=None, extra=""):
    full = f"{title}｜{SITE['name']}" if title != SITE["name"] else f"{SITE['name']}｜{SITE['tagline']}"
    url = SITE["url"] + path
    og_img = f'<meta property="og:image" content="{E(image)}">' if image else ""
    return f"""<!doctype html>
<html lang="{SITE['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(full)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{E(url)}">
<meta property="og:type" content="{'article' if extra else 'website'}">
<meta property="og:site_name" content="{E(SITE['name'])}">
<meta property="og:title" content="{E(full)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{E(url)}">
{og_img}
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#2f5d50">
<link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=Noto+Serif+TC:wght@600;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/style.css?v={VERSION}">
{extra}
</head>
<body>
<a class="skip" href="#main">跳到主要內容</a>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="logo" href="/">{LOGO}<span class="logo-text"><b>{E(SITE['name'])}</b><small>{E(SITE['name_en'])}</small></span></a>
    <button class="nav-toggle" aria-expanded="false" aria-controls="nav" aria-label="選單"><span></span><span></span></button>
    <nav id="nav" class="nav">
      {''.join(f'<a href="/{c["slug"]}/">{E(c["name"])}</a>' for c in SITE['countries'])}
      <a href="/destinations/">所有目的地</a>
      <a href="/about/">關於</a>
    </nav>
  </div>
</header>
<main id="main">
"""


def foot():
    year = dt.date.today().year
    return f"""</main>
<footer class="site-footer">
  <div class="wrap footer-grid">
    <div>
      <a class="logo logo-foot" href="/">{LOGO}<span class="logo-text"><b>{E(SITE['name'])}</b><small>{E(SITE['name_en'])}</small></span></a>
      <p class="muted">{E(SITE['tagline'])}</p>
    </div>
    <div>
      <h4>目的地</h4>
      {''.join(f'<a href="/{c["slug"]}/">{E(c["name"])} {E(c["en"])}</a>' for c in SITE['countries'])}
      <span class="muted">{"・".join(E(x.split()[0]) for x in SITE['coming_soon'])}（籌備中）</span>
    </div>
    <div>
      <h4>關於本站</h4>
      <a href="/about/">關於小樹洞</a>
      <a href="/disclosure/">聯盟行銷與圖片授權</a>
    </div>
  </div>
  <div class="wrap footer-bottom muted">© {year} {E(SITE['name'])} little-hole.com｜部分連結為聯盟行銷連結，詳見<a href="/disclosure/">揭露聲明</a></div>
</footer>
<div class="lightbox" hidden><button class="lb-close" aria-label="關閉">×</button><img alt=""></div>
<script src="/js/main.js?v={VERSION}" defer></script>
</body>
</html>"""


def card(p, big=False):
    img = p["images"][0]
    tag = "ticket" if p.get("klook") else ""
    badge = '<span class="badge">可線上訂票</span>' if tag else ""
    return f"""<article class="card{' card-big' if big else ''}">
  <a href="{p['url']}" class="card-link">
    <div class="card-img"><img src="{E(img['src'])}" alt="{E(img.get('alt',''))}" loading="lazy" width="{img['width']}" height="{img['height']}">{badge}</div>
    <div class="card-body">
      <p class="kicker">{E(p['_country']['name'])}・{E(p['_city']['name'])}</p>
      <h3>{E(p['title'])}</h3>
      <p class="excerpt">{E(p['excerpt'])}</p>
      <p class="meta">{E(p['date'])}・閱讀 {p['minutes']} 分鐘</p>
    </div>
  </a>
</article>"""


def klook_box(p, inline_box=False):
    k = p.get("klook")
    if not k:
        return ""
    href = E(klook_link(k["url"]))
    return f"""<aside class="klook{' klook-inline' if inline_box else ''}">
  <p class="klook-kicker">門票＆行程</p>
  <p class="klook-title">{E(k.get('label', p['title'] + ' 門票'))}</p>
  <p class="klook-note">{E(k.get('note', '線上預訂免排隊，出發前也能隨時查看最新票價與優惠。'))}</p>
  <a class="btn-klook" href="{href}" target="_blank" rel="sponsored nofollow noopener">到 Klook 查看票價 →</a>
  <p class="klook-disc">＊此為聯盟行銷連結，透過連結預訂小樹洞可獲得少量回饋，不會影響你的價格。</p>
</aside>"""


def breadcrumbs(items):
    parts = [f'<a href="{u}">{E(n)}</a>' if u else f'<span aria-current="page">{E(n)}</span>' for n, u in items]
    return '<nav class="crumbs" aria-label="麵包屑">' + '<span class="sep">/</span>'.join(parts) + "</nav>"

# ---------------------------------------------------------------- 頁面

def write(path, content):
    f = OUT / path.strip("/") / "index.html" if not path.endswith(".html") else OUT / path.strip("/")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def page_post(p, posts):
    c, ci = p["_country"], p["_city"]
    imgs = p["images"]
    info_rows = "".join(f"<div><dt>{E(k)}</dt><dd>{inline(v)}</dd></div>" for k, v in p.get("info", {}).items())
    related = [x for x in posts if x is not p and x["country"] == p["country"]][:3]
    toc = re.findall(r"^## (.+)$", p["body"], re.M)
    ld = {
        "@context": "https://schema.org", "@type": "Article", "headline": p["title"],
        "description": p["excerpt"], "image": [i["src"] for i in imgs], "datePublished": p["date"],
        "dateModified": p.get("updated", p["date"]), "inLanguage": SITE["lang"],
        "author": {"@type": "Organization", "name": SITE["name"]},
        "publisher": {"@type": "Organization", "name": SITE["name"], "url": SITE["url"]},
        "about": {"@type": "TouristAttraction", "name": p.get("place", p["title"]),
                  "address": p.get("info", {}).get("地址", "")},
        "mainEntityOfPage": SITE["url"] + p["url"],
    }
    extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
    h = head(p["title"], p["excerpt"], p["url"], imgs[0]["src"], extra)
    h += f"""<article class="post">
  <header class="post-head wrap">
    {breadcrumbs([("首頁", "/"), (c['name'], f"/{c['slug']}/"), (ci['name'], f"/{c['slug']}/{ci['slug']}/"), (p['title'], None)])}
    <p class="kicker">{E(c['name'])}・{E(ci['name'])}</p>
    <h1>{E(p['title'])}</h1>
    {f'<p class="subtitle">{E(p["subtitle"])}</p>' if p.get('subtitle') else ''}
    <p class="meta">{E(p['date'])}　・　約 {p['chars']} 字・閱讀 {p['minutes']} 分鐘</p>
  </header>
  <div class="post-hero wrap-wide">{figure(imgs[0], eager=True, cls='hero-fig')}</div>
  <div class="post-layout wrap">
    <div class="post-body prose">
      <p class="lede">{inline(p['excerpt'])}</p>
      {markdown(p['body'], p)}
      <p class="tags">{''.join(f'<span>#{E(t)}</span>' for t in p.get('tags', []))}</p>
    </div>
    <aside class="post-side">
      <div class="side-sticky">
        <section class="info-card"><h2>景點資訊</h2><dl>{info_rows}</dl>
          <p class="info-foot">資訊以官方公告為準，出發前請再次確認。</p></section>
        {klook_box(p)}
        {('<nav class="toc"><h2>本文目錄</h2><ol>' + ''.join(f'<li><a href="#{anchor(t)}">{E(t)}</a></li>' for t in toc) + '</ol></nav>') if toc else ''}
      </div>
    </aside>
  </div>
</article>"""
    if related:
        h += f'<section class="wrap related"><h2 class="section-title">繼續探索{E(c["name"])}</h2><div class="grid">{"".join(card(r) for r in related)}</div></section>'
    write(p["url"], h + foot())


def page_home(posts):
    feat, rest = posts[0], posts[1:7]
    countries = ""
    for c in SITE["countries"]:
        n = sum(1 for p in posts if p["country"] == c["slug"])
        cover = next((p["images"][0]["src"] for p in posts if p["country"] == c["slug"]), "")
        countries += f'<a class="dest" href="/{c["slug"]}/" style="--bg:url(\'{E(cover)}\')"><span class="dest-en">{E(c["en"])}</span><b>{E(c["name"])}</b><span>{n} 篇景點</span></a>'
    for x in SITE["coming_soon"]:
        zh, en = x.split(" ", 1)
        countries += f'<div class="dest dest-soon"><span class="dest-en">{E(en)}</span><b>{E(zh)}</b><span>籌備中</span></div>'
    h = head(SITE["name"], SITE["description"], "/", feat["images"][0]["src"])
    h += f"""<section class="hero wrap">
  <div class="hero-text">
    <p class="kicker">從台灣出發・走向世界城市</p>
    <h1>鑽進城市的<br><em>小樹洞</em></h1>
    <p class="hero-sub">每篇只講一個景點，把歷史、必看亮點、交通與門票一次說清楚。<br>讀完就能出發。</p>
    <a class="btn" href="#latest">開始閱讀</a>
  </div>
  <a class="hero-feature" href="{feat['url']}">
    <img src="{E(feat['images'][0]['src'])}" alt="{E(feat['images'][0].get('alt',''))}" fetchpriority="high" width="{feat['images'][0]['width']}" height="{feat['images'][0]['height']}">
    <span class="hero-feature-label"><small>最新文章・{E(feat['_city']['name'])}</small>{E(feat['title'])}</span>
  </a>
</section>
<section class="wrap" id="latest">
  <div class="section-head"><h2 class="section-title">最新景點</h2><a href="/destinations/">看全部 →</a></div>
  <div class="grid">{''.join(card(p) for p in [feat] + rest)}</div>
</section>
<section class="wrap">
  <div class="section-head"><h2 class="section-title">探索目的地</h2></div>
  <div class="dest-grid">{countries}</div>
</section>"""
    write("/", h + foot())


def page_country(c, posts):
    mine = [p for p in posts if p["country"] == c["slug"]]
    cities = ""
    for ci in c["cities"]:
        cp = [p for p in mine if p["city"] == ci["slug"]]
        if not cp:
            continue
        cities += f"""<section class="city-block">
  <div class="section-head"><h2 class="section-title"><a href="/{c['slug']}/{ci['slug']}/">{E(ci['name'])} <small>{E(ci['en'])}</small></a></h2><span class="muted">{len(cp)} 篇</span></div>
  <div class="grid">{''.join(card(p) for p in cp)}</div>
</section>"""
    h = head(f"{c['name']}景點", c["intro"], f"/{c['slug']}/")
    h += f"""<section class="page-head wrap">{breadcrumbs([("首頁", "/"), (c['name'], None)])}
  <p class="kicker">{E(c['en'])}</p><h1>{E(c['name'])}景點</h1><p class="subtitle">{E(c['intro'])}</p>
  <div class="chips">{''.join(f'<a href="/{c["slug"]}/{ci["slug"]}/">{E(ci["name"])}</a>' for ci in c['cities'] if any(p['city']==ci['slug'] for p in mine))}</div>
</section><div class="wrap">{cities}</div>"""
    write(f"/{c['slug']}/", h + foot())
    for ci in c["cities"]:
        cp = [p for p in mine if p["city"] == ci["slug"]]
        if not cp:
            continue
        h = head(f"{ci['name']}景點推薦", ci["intro"], f"/{c['slug']}/{ci['slug']}/")
        h += f"""<section class="page-head wrap">{breadcrumbs([("首頁", "/"), (c['name'], f"/{c['slug']}/"), (ci['name'], None)])}
  <p class="kicker">{E(ci['en'])}・{E(c['name'])}</p><h1>{E(ci['name'])}景點推薦</h1><p class="subtitle">{E(ci['intro'])}</p>
</section><div class="wrap"><div class="grid">{''.join(card(p) for p in cp)}</div></div>"""
        write(f"/{c['slug']}/{ci['slug']}/", h + foot())


def page_destinations(posts):
    blocks = ""
    for c in SITE["countries"]:
        for ci in c["cities"]:
            cp = [p for p in posts if p["country"] == c["slug"] and p["city"] == ci["slug"]]
            if cp:
                blocks += f'<div class="dir-col"><h3><a href="/{c["slug"]}/{ci["slug"]}/">{E(c["name"])}・{E(ci["name"])}</a></h3><ul>' + "".join(f'<li><a href="{p["url"]}">{E(p["title"])}</a></li>' for p in cp) + "</ul></div>"
    h = head("所有目的地", "小樹洞旅行誌所有景點文章索引。", "/destinations/")
    h += f'<section class="page-head wrap">{breadcrumbs([("首頁", "/"), ("所有目的地", None)])}<h1>所有目的地</h1><p class="subtitle">依城市整理的景點索引，持續更新中。</p></section><div class="wrap dir">{blocks}</div>'
    write("/destinations/", h + foot())


def page_static(posts):
    about = f"""<section class="page-head wrap">{breadcrumbs([("首頁", "/"), ("關於", None)])}<h1>關於小樹洞</h1></section>
<div class="wrap prose narrow">
<p>小時候總覺得樹幹上的小洞裡藏著另一個世界。長大後才發現，每座城市也有自己的「小樹洞」——一棟建築背後的工程故事、一條老街從繁華到沉寂再重生的歷程、一件國寶怎麼漂洋過海來到這裡。</p>
<p><strong>{E(SITE['name'])}</strong>想做的事很簡單：每篇文章只介紹一個景點，用 500 到 1000 字把它的來歷、必看亮點、交通方式與參觀建議講清楚，再搭配實景照片，讓你讀完就知道值不值得去、該怎麼去。</p>
<p>我們從台灣出發，接下來會陸續走訪日本、韓國、東南亞與更多世界城市。</p>
<h2>關於圖片</h2><p>本站照片來自 Wikimedia Commons 等平台、採用允許商業使用的創用 CC 授權（CC BY、CC BY-SA）或公眾領域（CC0）圖片，每張照片下方都標註攝影者、授權條款與原始出處。</p>
<h2>關於訂票連結</h2><p>需要購票的景點，文章中會附上 Klook 的訂票連結，詳見<a href="/disclosure/">聯盟行銷揭露聲明</a>。</p>
</div>"""
    write("/about/", head("關於小樹洞", "關於小樹洞旅行誌。", "/about/") + about + foot())
    credits = ""
    for p in posts:
        credits += f'<h3><a href="{p["url"]}">{E(p["title"])}</a></h3><ul class="credit-list">' + "".join(
            f'<li>{E(i["file"].replace("File:", ""))}　—　{credit(i)}</li>' for i in p["images"]) + "</ul>"
    disc = f"""<section class="page-head wrap">{breadcrumbs([("首頁", "/"), ("聯盟行銷與圖片授權", None)])}<h1>聯盟行銷與圖片授權</h1></section>
<div class="wrap prose narrow">
<h2>聯盟行銷揭露</h2>
<p>本站部分文章含有 Klook（客路）聯盟行銷連結。當你透過這些連結預訂門票或行程，小樹洞會獲得少量佣金回饋，<strong>你支付的價格不會因此增加</strong>。這些回饋用來支持網站營運與持續撰寫內容。</p>
<p>我們只在「需要購票的景點」放上訂票連結，文章內容不受合作關係影響。票價、開放時間等資訊可能變動，請以官方與訂購頁面公告為準。</p>
<h2>圖片授權</h2>
<p>本站使用的照片皆為允許商業使用的授權：CC0／公眾領域、CC BY 或 CC BY-SA。依授權條款，我們在每張照片標示攝影者、授權方式與原始來源。若你是照片作者並對使用方式有疑慮，歡迎與我們聯繫。</p>
<h2>各篇文章圖片出處</h2>{credits}
</div>"""
    write("/disclosure/", head("聯盟行銷與圖片授權", "小樹洞旅行誌的聯盟行銷揭露與圖片授權說明。", "/disclosure/") + disc + foot())
    nf = f'<section class="page-head wrap center"><p class="kicker">404</p><h1>這個樹洞是空的</h1><p class="subtitle">找不到這個頁面，可能已經搬家了。</p><a class="btn" href="/">回到首頁</a></section>'
    write("404.html", head("找不到頁面", "找不到頁面", "/404.html") + nf + foot())


def sitemap(posts):
    urls = ["/", "/destinations/", "/about/", "/disclosure/"]
    for c in SITE["countries"]:
        urls.append(f"/{c['slug']}/")
        urls += [f"/{c['slug']}/{ci['slug']}/" for ci in c["cities"] if any(p["city"] == ci["slug"] for p in posts)]
    urls += [p["url"] for p in posts]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "".join(f"  <url><loc>{SITE['url']}{u}</loc></url>\n" for u in urls) + "</urlset>\n"
    (OUT / "sitemap.xml").write_text(xml, encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE['url']}/sitemap.xml\n", encoding="utf-8")
    (OUT / "CNAME").write_text("little-hole.com\n", encoding="utf-8")


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT)
    posts = load_posts()
    for p in posts:
        page_post(p, posts)
    page_home(posts)
    for c in SITE["countries"]:
        page_country(c, posts)
    page_destinations(posts)
    page_static(posts)
    sitemap(posts)
    for p in posts:
        flag = "" if 500 <= p["chars"] <= 1000 else "  ⚠ 字數不在 500–1000"
        n = len(p["images"])
        flag += "" if 3 <= n <= 5 else "  ⚠ 圖片不在 3–5 張"
        print(f"  {p['url']}  {p['chars']} 字・{n} 張圖{flag}")
    print(f"完成：{len(posts)} 篇文章 → {OUT}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
    if "--serve" in sys.argv:
        import functools, http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
        print("預覽：http://localhost:8000")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()
