"""Wikimedia Commons 圖片工具

用法：
  搜尋可商用圖片：  python tools/commons.py search "Taipei 101" "Jiufen"
  產生文章用圖片資料：python tools/commons.py resolve "File:xxx.jpg" "File:yyy.jpg"

只接受可商用的授權：CC0、公有領域、CC BY、CC BY-SA（排除 NC / ND）。
resolve 會輸出可直接貼進文章 front matter "images" 欄位的 JSON。
"""
import json
import time
import urllib.error
import re
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "LittleHoleTravelBlog/1.0 (static site image credits)"}
OK_PREFIX = ("CC BY", "CC-BY", "CC0", "Public domain", "PD")


def api(params):
    params = dict(params, format="json")
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)

    for attempt in range(6):
        try:
            return json.load(urllib.request.urlopen(req, timeout=30))
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 5:
                raise
            time.sleep(5 * (attempt + 1))  # Commons 限流，稍等再試


RISKY_CATS = ("NoFoP", "No FoP", "Deletion requests", "Copyright violations")


def fop_warnings(titles):
    """回傳 {title: [可疑分類]}：全景自由（FoP）或刪除請求相關分類。"""
    r = api(dict(action="query", titles="|".join(titles), prop="categories", cllimit="max"))
    out = {}
    for p in r["query"]["pages"].values():
        cats = [c["title"] for c in p.get("categories", []) if any(k.lower() in c["title"].lower() for k in RISKY_CATS)]
        if cats:
            out[p["title"]] = cats
    return out


def strip_tags(s):
    s = re.sub(r"<style.*?</style>", "", s or "", flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def commercial_ok(lic):
    return lic.startswith(OK_PREFIX) and "NC" not in lic and "ND" not in lic


def info(page):
    ii = page["imageinfo"][0]
    m = ii.get("extmetadata", {})
    lic = m.get("LicenseShortName", {}).get("value", "")
    return {
        "file": page["title"],
        "src": ii.get("thumburl", ii["url"]).split("?")[0],
        "width": ii.get("thumbwidth", ii["width"]),
        "height": ii.get("thumbheight", ii["height"]),
        "page": ii["descriptionurl"],
        "author": strip_tags(m.get("Artist", {}).get("value", ""))[:80] or "Unknown",
        "license": lic,
        "license_url": m.get("LicenseUrl", {}).get("value", ""),
        "ok": commercial_ok(lic),
    }


def search(queries):
    for q in queries:
        print("=====", q)
        r = api(dict(action="query", generator="search", gsrsearch=q + " filetype:bitmap",
                     gsrnamespace=6, gsrlimit=30, prop="imageinfo",
                     iiprop="url|size|extmetadata", iiurlwidth=1280))
        pages = sorted(r.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
        for p in pages:
            i = info(p)
            if i["ok"] and p["imageinfo"][0]["width"] >= 1600:
                desc = strip_tags(p["imageinfo"][0].get("extmetadata", {}).get("ImageDescription", {}).get("value", ""))[:120]
                print(f'{i["file"]} | {i["license"]} | {i["author"]} | {i["width"]}x{i["height"]} | {desc}')


def resolve(titles):
    out = []
    r = api(dict(action="query", titles="|".join(titles), prop="imageinfo",
                 iiprop="url|size|extmetadata", iiurlwidth=1280))
    pages = {p["title"]: p for p in r["query"]["pages"].values()}
    norm = {n["from"]: n["to"] for n in r["query"].get("normalized", [])}
    for t in titles:
        p = pages.get(norm.get(t, t))
        if not p or "imageinfo" not in p:
            print(f"!! 找不到：{t}", file=sys.stderr)
            continue
        i = info(p)
        if not i.pop("ok"):
            print(f"!! 授權不可商用，略過：{t} ({i['license']})", file=sys.stderr)
            continue
        i["alt"] = ""
        i["caption"] = ""
        out.append(i)
    for t, cats in fop_warnings([i["file"] for i in out]).items():
        print(f"!! 版權風險（全景自由/刪除請求），建議換圖：{t} → {cats}", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"search": search, "resolve": resolve}[cmd](args)
