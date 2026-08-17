# 台股隔日沖大戶分點監控

這個專案將儀表板部署在 GitHub Pages，並由 GitHub Actions 定期抓取富邦電子交易網的分點買賣超與 Yahoo Finance 延遲行情，產生靜態 JSON 檔案。GitHub Pages 只負責顯示資料，不直接向富邦或 Yahoo 發出跨域請求，因此適合以靜態網站方式發布。

## 專案結構

| 路徑 | 用途 |
|---|---|
| `index.html` | GitHub Pages 儀表板首頁 |
| `data/latest.json` | 最近六個工作日的分點買賣超資料 |
| `data/radar.json` | Actions 最近一次取得的 Yahoo 延遲行情 |
| `config/watchlist.json` | Actions 共同更新的預設自選股代號 |
| `scripts/update_data.py` | 抓取富邦與 Yahoo、產生 JSON 的 Python 腳本 |
| `.github/workflows/update-data.yml` | 每 15 分鐘執行一次的 GitHub Actions |

## 部署方式

先將本資料夾內容上傳至 GitHub repository 的預設分支。接著在 GitHub repository 的 **Settings → Pages** 中，將來源設定為 **Deploy from a branch**，選擇預設分支與 `/root` 資料夾。儲存後，GitHub Pages 會發布 `index.html`。

第一次部署後，可以在 **Actions** 頁面手動執行 `Update market data`，確認 repository 具有寫入 contents 的權限。之後 workflow 會依照 cron 設定約每 15 分鐘抓取資料，並在資料有變化時提交 `data/latest.json` 與 `data/radar.json`。

## 自選股使用方式

頁面中的自選股清單仍保存在瀏覽器 `localStorage`，因此每位使用者可以有自己的清單。若要更新 Actions 的共用行情清單，請修改 `config/watchlist.json`，例如：

```json
[
  "2330",
  "2317",
  "2454",
  "2382",
  "3037"
]
```

手動新增但尚未列入 `config/watchlist.json` 的股票，會在下一次 Actions 更新後才有靜態行情資料。頁面會清楚顯示「尚未納入最近一次 GitHub 更新」，不會把無資料誤認為零值。

## 資料限制

Yahoo Finance 的台股報價屬於延遲行情，這個專案不宣稱真正即時報價。GitHub Actions 以約 15 分鐘為更新週期，也不適合取代券商的即時行情服務。富邦分點資料則依公開頁面實際可解析內容保存；若來源頁面格式改變，Actions 會在資料檔的 `errors` 欄位留下錯誤資訊。

## 本地測試

在專案根目錄執行：

```bash
python3 -m http.server 8765
```

然後開啟 `http://127.0.0.1:8765/index.html`。直接以 `file://` 開啟時，瀏覽器會阻擋相對路徑 JSON 載入，因此不建議使用雙擊 HTML 的方式測試。
