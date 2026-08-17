from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"

FUBON_URL = "https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GitHubActions/1.0)"}
BRANCHES = {
    "凱基-台北": {"broker": "凱基", "brokerCode": "9200", "branchCode": "9268"},
    "元大-土城永寧": {"broker": "元大", "brokerCode": "9800", "branchCode": "9875"},
    "國票-敦北法人": {"broker": "國票", "brokerCode": "7790", "branchCode": "0037003700390063"},
    "凱基-松山": {"broker": "凱基", "brokerCode": "9200", "branchCode": "9217"},
    "凱基-虎尾": {"broker": "凱基", "brokerCode": "9200", "branchCode": "9275"},
    "凱基-斗六": {"broker": "凱基", "brokerCode": "9200", "branchCode": "9281"},
    "富邦-虎尾": {"broker": "富邦", "brokerCode": "9600", "branchCode": "9697"},
    "富邦-嘉義": {"broker": "富邦", "brokerCode": "9600", "branchCode": "9692"},
    "富邦-建國": {"broker": "富邦", "brokerCode": "9600", "branchCode": "9658"},
    "富邦-南屯": {"broker": "富邦", "brokerCode": "9600", "branchCode": "9666"},
    "富邦-北港": {"broker": "富邦", "brokerCode": "9600", "branchCode": "0039003600390043"},
}


def number(value: str) -> int:
    return int(re.sub(r"[^0-9-]", "", value or "") or 0)


def parse_stock(text: str) -> tuple[str, str]:
    text = " ".join(text.split())
    match = re.match(r"^(\d{4,6}[A-Z]?)(.*)$", text, re.I)
    return (match.group(1), match.group(2).strip() or match.group(1)) if match else ("", text)


def fetch_branch(name: str, date: str) -> list[dict]:
    cfg = BRANCHES[name]
    params = {"a": cfg["brokerCode"], "b": cfg["branchCode"], "c": "B", "e": date, "f": date}
    response = requests.get(FUBON_URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = "big5"
    soup = BeautifulSoup(response.text, "html.parser")
    rows: dict[str, dict] = {}
    for table in soup.find_all("table"):
        table_rows = table.find_all("tr")
        header_index = next((i for i, row in enumerate(table_rows) if "買進" in row.get_text() and "賣出" in row.get_text() and "差額" in row.get_text()), None)
        if header_index is None:
            continue
        is_sell = "賣超" in table_rows[0].get_text()
        for row in table_rows[header_index + 1 :]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue
            code, stock_name = parse_stock(cells[0].get_text(" ", strip=True))
            if not code:
                continue
            buy, sell, net = (number(c.get_text(" ", strip=True)) for c in cells[1:4])
            rows[code] = {"code": code, "name": stock_name, "buy": buy, "sell": sell, "net": -abs(net) if is_sell else abs(net)}
    return list(rows.values())


def fetch_yahoo(code: str) -> dict:
    symbol = code if "." in code else f"{code}.TW"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}"
    response = requests.get(url, params={"interval": "1d", "range": "5d"}, headers=HEADERS, timeout=20)
    response.raise_for_status()
    result = response.json()["chart"]["result"][0]
    meta = result.get("meta", {})
    quote_data = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = [v for v in quote_data.get("close", []) if v is not None]
    price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    previous = meta.get("previousClose") or meta.get("chartPreviousClose")
    change = price - previous if price is not None and previous is not None else None
    return {"code": code, "name": meta.get("longName") or meta.get("shortName") or code, "price": price, "change": change, "changePct": change / previous * 100 if change is not None and previous else None, "volume": (quote_data.get("volume") or [None])[-1], "updatedAt": datetime.now(timezone.utc).isoformat()}


def recent_weekdays(count: int = 6) -> list[str]:
    values, cursor = [], datetime.now()
    while len(values) < count:
        if cursor.weekday() < 5:
            values.append(cursor.strftime("%Y-%m-%d"))
        cursor -= timedelta(days=1)
    return list(reversed(values))


def main() -> None:
    dates = recent_weekdays()
    today = dates[-1]
    configured = json.loads((CONFIG_DIR / "watchlist.json").read_text(encoding="utf-8"))
    branch_data, errors = {}, {}
    for name in BRANCHES:
        branch_data[name] = {}
        for date in dates:
            try:
                branch_data[name][date] = fetch_branch(name, date)
            except Exception as exc:
                branch_data[name][date] = []
                errors[f"{name}|{date}"] = str(exc)
    radar = {}
    for code in configured:
        try:
            radar[code] = fetch_yahoo(code)
        except Exception as exc:
            radar[code] = {"code": code, "error": str(exc)}
    payload = {"updatedAt": datetime.now(timezone.utc).isoformat(), "date": today, "dates": dates, "branches": branch_data, "errors": errors}
    (DATA_DIR / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA_DIR / "radar.json").write_text(json.dumps({"updatedAt": payload["updatedAt"], "quotes": radar}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
