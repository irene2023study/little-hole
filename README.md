# 小樹洞旅行誌 little-hole.com

純靜態網站，只需要 Python 3（不用安裝任何套件）。

## 指令

```bash
python build.py            # 產生網站到 dist/
python build.py --serve    # 產生並在 http://localhost:8000 預覽
```

上線只要把 `dist/` 整個資料夾部署到靜態主機（Cloudflare Pages、GitHub Pages、Netlify 皆可），`dist/CNAME` 已設定 little-hole.com。

## 設定（site.json）

- `klook_aid`：填入 Klook 聯盟的 aid，所有 Klook 連結會自動加上 `?aid=...`。若文章裡填的是 `affiliate.klook.com` 產生的完整分潤連結，則原樣使用。
- `countries[].cities[]`：國家／城市分類，新增城市先在這裡加。
- `coming_soon`：首頁「即將推出」的目的地。
- `google_site_verification`（選填）：Google Search Console 的 HTML 標記驗證碼，填入後每頁會輸出 `<meta name="google-site-verification">`。

## SEO（建置時自動產生）

- 每頁：canonical、robots、Open Graph／Twitter 卡片（含圖片尺寸與 alt）、Atom 訂閱連結
- 文章：`Article` + `BreadcrumbList` 結構化資料、`article:*` 發佈／更新時間與標籤；front matter 可加 `"updated": "YYYY-MM-DD"` 標示更新日
- 國家／城市頁：`BreadcrumbList` + `ItemList`，描述自動帶入收錄景點
- `sitemap.xml`（含 lastmod）、`robots.txt`、`feed.xml`（Atom），404 頁 noindex

## 新增文章

在 `content/posts/` 新增 `<slug>.md`，網址會是 `/<country>/<city>/<slug>/`。

```
---
{
  "title": "標題｜副標",
  "place": "景點正式名稱",
  "subtitle": "一句話副標",
  "country": "taiwan",
  "city": "taipei",
  "date": "2026-11-10",
  "excerpt": "摘要（首頁卡片與 SEO 描述）",
  "tags": ["台北景點"],
  "info": { "地址": "...", "開放時間": "...", "門票": "...", "交通": "...", "建議停留": "..." },
  "klook": { "url": "https://www.klook.com/zh-TW/activity/...", "label": "...門票", "note": "...",
             "prices": [{"type": "全票", "price": "NT$200", "note": "18歲以上"}],
             "price_source": "官方公告票價", "price_date": "2026年11月" },
  "images": [ ...由 tools/commons.py resolve 產生... ]
}
---
## 小標

內文段落。**粗體**、[連結](https://...)

{{img:2}}        ← 插入第 2 張圖（第 1 張固定當封面）
{{klook}}        ← 插入 Klook 訂票卡片（側欄也會自動顯示）
- 清單
> 小樹洞提醒框
```

不需門票的景點把 `"klook"` 設為 `null`。建置時會檢查字數（500–1000）與圖片數（3–5）。

## 找圖（Wikimedia Commons，只取可商用授權）

```bash
python tools/commons.py search "Sun Moon Lake"
python tools/commons.py resolve "File:xxx.jpg" "File:yyy.jpg"
```

`resolve` 會自動排除 NC／ND 授權，輸出含作者、授權、出處的 JSON，貼進文章 `images` 後補上 `caption`／`alt`。圖片出處會顯示在每張圖下方與 /disclosure/ 頁面。
