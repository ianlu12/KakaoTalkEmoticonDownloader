# KakaoTalkEmoticonDownloader

下載 KakaoTalk 表情符號詳情頁（`e.kakao.com/t/<slug>`）內所有動圖（`animatedUrl`），原始檔多為 WebP，本工具會逐檔再轉一份 GIF。

## 環境需求

- Python 3.10+（已驗證 3.14.7）
- 依賴：`requests`、`Pillow`

```bash
pip install requests Pillow
```

## 快速開始

```bash
# 使用預設 slug（little-maple-henesys-adventures）
python download_kakao_section_animations.py

# 指定 slug
python download_kakao_section_animations.py --slug <slug>

# 用完整頁面 URL（會覆蓋 --slug）
python download_kakao_section_animations.py --url https://e.kakao.com/t/<slug>

# 指定輸出根目錄（預設 kakao_section_animations）
python download_kakao_section_animations.py --slug <slug> --out ./output
```

## 參數

| 參數 | 預設 | 說明 |
| --- | --- | --- |
| `--slug` | `little-maple-henesys-adventures` | 表情包 slug，頁面 URL 中 `/t/` 後面的那段 |
| `--url` | 無 | 完整頁面 URL，優先於 `--slug`；支援 `https://e.kakao.com/t/<slug>`、`https://e.kakao.com/api/items/<slug>`、裸 slug |
| `--out` | `kakao_section_animations` | 輸出根目錄，實際寫入 `<out>/<slug>/` |
| `-h, --help` | — | 顯示說明 |

## 輸出結構

```
<out>/<slug>/
├── <hash>-g.webp   # 原始下載檔
├── <hash>-g.gif    # 由 webp 自動轉出（保留透明、幀延遲）
└── ...
```

檔名取自 URL 路徑最後一段，並依 `Content-Type` 補副檔名（webp / gif / png / jpg，未知則 `.bin`）。非 webp 不轉檔。執行結束會印出 `done: N file(s) -> <out>/<slug>`。

## 運作原理

1. 以 `Referer: <page_url>` + `User-Agent: Mozilla/5.0` 建立 `requests.Session`。
2. 打 `GET https://e.kakao.com/api/items/{slug}`，取 `contents.items[].animatedUrl`。
3. 逐一串流下載到 `<out>/<slug>/`。
4. `.webp` 用 Pillow 逐幀轉 RGBA → 255 色調色盤 + 透明索引 255、`disposal=2`、`loop=0`，存成同名 `.gif`，保留各幀 `duration`（預設 100ms）。

## 注意事項

- 若 API 回傳無 `animatedUrl`，程式直接報錯退出：`No animatedUrl entries found in contents.items`。
- URL 解析失敗會報錯：`cannot parse slug from URL: ...`。
- 範例輸出目錄 `kakao_section_animations/little-maple-henesys-adventures/` 已在 `.gitignore` 中，不會進版控。
