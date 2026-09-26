"""Local market desk. Serves the page and proxies free market, news, and NSE data."""
from __future__ import annotations

import calendar
import datetime
import email.utils
import html
import http.cookiejar
import json
import os
import re
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = 8765
PAGES = {"/", "/index.html"}
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept": "application/json,text/html,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
}

QUERIES = [
    ("India", "Nifty OR Sensex OR NSE OR BSE stock"),
    ("United States", "Wall Street OR Nasdaq OR S&P 500 stock"),
    ("Europe", "European stocks OR FTSE OR DAX market"),
    ("Asia", "Nikkei OR Hang Seng OR Shanghai stocks"),
    ("Energy", "oil OR crude OR OPEC OR energy stocks"),
    ("Technology", "AI OR semiconductor OR chip stocks"),
    ("Banking", "bank stocks OR interest rate OR RBI OR Federal Reserve"),
    ("Pharma", "pharma OR drug OR healthcare stocks"),
    ("Auto", "EV OR automobile OR auto stocks"),
    ("Metals", "gold OR steel OR copper OR mining stocks"),
    ("Crypto", "bitcoin OR crypto market"),
    ("Defense", "defense stocks OR geopolitical market"),
    ("FMCG", "consumer goods OR FMCG OR retail sales"),
    ("Realty", "real estate OR infrastructure stocks"),
]

MARKETS = [
    ("India", "Nifty 50", "^NSEI"),
    ("India", "Sensex", "^BSESN"),
    ("India", "Nifty Bank", "^NSEBANK"),
    ("India", "Nifty IT", "^CNXIT"),
    ("F&O", "India VIX", "^INDIAVIX"),
    ("F&O", "USD / INR", "INR=X"),
    ("F&O", "Crude oil", "CL=F"),
    ("F&O", "Gold", "GC=F"),
    ("F&O", "US futures", "ES=F"),
    ("Rates", "US 10Y yield", "^TNX"),
    ("Rates", "Dollar index", "DX-Y.NYB"),
    ("Sector", "Nifty Auto", "^CNXAUTO"),
    ("Sector", "Nifty Pharma", "^CNXPHARMA"),
    ("Sector", "Nifty FMCG", "^CNXFMCG"),
    ("Sector", "Nifty Metal", "^CNXMETAL"),
    ("Sector", "Nifty Realty", "^CNXREALTY"),
    ("Sector", "Nifty Energy", "^CNXENERGY"),
    ("Commodity", "Silver", "SI=F"),
    ("Commodity", "Platinum", "PL=F"),
    ("Commodity", "Palladium", "PA=F"),
    ("Commodity", "Copper", "HG=F"),
    ("Commodity", "Aluminium", "ALI=F"),
    ("Commodity", "Brent crude", "BZ=F"),
    ("Commodity", "Natural gas", "NG=F"),
    ("Crypto", "Bitcoin", "BTC-USD"),
    ("Crypto", "Ethereum", "ETH-USD"),
    ("United States", "S&P 500", "^GSPC"),
    ("United States", "Dow Jones", "^DJI"),
    ("United States", "Nasdaq", "^IXIC"),
    ("United Kingdom", "FTSE 100", "^FTSE"),
    ("Germany", "DAX", "^GDAXI"),
    ("France", "CAC 40", "^FCHI"),
    ("Europe", "Euro Stoxx 50", "^STOXX50E"),
    ("Switzerland", "SMI", "^SSMI"),
    ("Spain", "IBEX 35", "^IBEX"),
    ("Italy", "FTSE MIB", "FTSEMIB.MI"),
    ("Netherlands", "AEX", "^AEX"),
    ("Japan", "Nikkei 225", "^N225"),
    ("Hong Kong", "Hang Seng", "^HSI"),
    ("China", "Shanghai", "000001.SS"),
    ("South Korea", "KOSPI", "^KS11"),
    ("Taiwan", "TAIEX", "^TWII"),
    ("Singapore", "Straits Times", "^STI"),
    ("Australia", "ASX 200", "^AXJO"),
    ("Canada", "TSX", "^GSPTSE"),
    ("Brazil", "Bovespa", "^BVSP"),
    ("Mexico", "IPC", "^MXX"),
    ("South Africa", "JSE Top 40", "^JN0U.JO"),
    ("Indonesia", "Jakarta", "^JKSE"),
    ("Thailand", "SET", "^SET.BK"),
    ("Malaysia", "KLCI", "^KLSE"),
    ("Saudi Arabia", "Tadawul", "^TASI.SR"),
    ("New Zealand", "NZX 50", "^NZ50"),
    ("Argentina", "Merval", "^MERV"),
]

STOCKS = [
    ("ADANIENT", "Adani Enterprises"), ("ADANIPORTS", "Adani Ports"), ("APOLLOHOSP", "Apollo Hospitals"),
    ("ASIANPAINT", "Asian Paints"), ("AXISBANK", "Axis Bank"), ("BAJAJ-AUTO", "Bajaj Auto"),
    ("BAJFINANCE", "Bajaj Finance"), ("BAJAJFINSV", "Bajaj Finserv"), ("BEL", "Bharat Electronics"),
    ("BHARTIARTL", "Bharti Airtel"), ("CIPLA", "Cipla"), ("COALINDIA", "Coal India"),
    ("DRREDDY", "Dr Reddy's"), ("EICHERMOT", "Eicher Motors"), ("ETERNAL", "Eternal"),
    ("GRASIM", "Grasim"), ("HCLTECH", "HCL Tech"), ("HDFCBANK", "HDFC Bank"),
    ("HDFCLIFE", "HDFC Life"), ("HINDALCO", "Hindalco"), ("HINDUNILVR", "Hindustan Unilever"),
    ("ICICIBANK", "ICICI Bank"), ("INDIGO", "InterGlobe Aviation"), ("INFY", "Infosys"),
    ("ITC", "ITC"), ("JIOFIN", "Jio Financial"), ("JSWSTEEL", "JSW Steel"),
    ("KOTAKBANK", "Kotak Bank"), ("LT", "Larsen & Toubro"), ("M&M", "Mahindra & Mahindra"),
    ("MARUTI", "Maruti Suzuki"), ("MAXHEALTH", "Max Healthcare"), ("NESTLEIND", "Nestle India"),
    ("NTPC", "NTPC"), ("ONGC", "ONGC"), ("POWERGRID", "Power Grid"),
    ("RELIANCE", "Reliance"), ("SBILIFE", "SBI Life"), ("SBIN", "SBI"),
    ("SHRIRAMFIN", "Shriram Finance"), ("SUNPHARMA", "Sun Pharma"), ("TATACONSUM", "Tata Consumer"),
    ("TMPV", "Tata Motors PV"), ("TATASTEEL", "Tata Steel"), ("TCS", "TCS"),
    ("TECHM", "Tech Mahindra"), ("TITAN", "Titan"), ("TRENT", "Trent"),
    ("ULTRACEMCO", "UltraTech Cement"), ("WIPRO", "Wipro"),
]
STOCK_ROWS = [("Nifty 50", name, ticker + ".NS") for ticker, name in STOCKS]

CATALOG = {symbol: (group, name) for group, name, symbol in MARKETS + STOCK_ROWS}
NEWS = {"items": [], "updated": 0, "sweeps": 0, "error": ""}
QUOTES = {"updated": 0, "markets": [], "error": ""}
STOCK_QUOTES = {"updated": 0, "stocks": [], "error": ""}
LOCK = threading.Lock()

INTERVALS = {"1m": "1m", "2m": "2m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "60m", "D": "1d", "W": "1wk", "M": "1mo"}
INTRADAY = {"1m", "2m", "5m", "15m", "30m", "1H"}
SPANS = {
    "1D": ("1d", 1), "5D": ("5d", 5), "1M": ("1mo", 31), "3M": ("3mo", 92), "6M": ("6mo", 183), "YTD": ("ytd", 366),
    "1Y": ("1y", 366), "2Y": ("2y", 730), "3Y": (1096, 1096), "5Y": ("5y", 1827), "10Y": ("10y", 3653), "ALL": (0, 99999),
}
REACH = {"1m": 7, "2m": 59, "5m": 59, "15m": 59, "30m": 59, "1H": 730}
DEFAULT_SPAN = {"1m": "1D", "2m": "1D", "5m": "5D", "15m": "5D", "30m": "1M", "1H": "3M", "D": "1Y", "W": "5Y", "M": "ALL"}
RETURN_DAYS = [("1M", 30), ("3M", 91), ("6M", 182), ("1Y", 365), ("2Y", 730), ("3Y", 1095), ("5Y", 1826), ("10Y", 3652)]


def fetch_query(region: str, query: str) -> list[dict]:
    url = (
        "https://news.google.com/rss/search?q="
        + quote(query + " when:1d")
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Arthlane/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        root = ET.fromstring(response.read())
    items = []
    for node in root.findall("./channel/item")[:8]:
        title = (node.findtext("title") or "").strip()
        headline, source = title.rsplit(" - ", 1) if " - " in title else (title, "Wire")
        if not headline:
            continue
        items.append(
            {
                "headline": headline,
                "source": source,
                "region": region,
                "link": (node.findtext("link") or "").strip(),
                "published": (node.findtext("pubDate") or "").strip(),
            }
        )
    return items


def sweep_news() -> None:
    found, errors = [], []
    for region, query in QUERIES:
        try:
            found.extend(fetch_query(region, query))
        except Exception as exc:
            errors.append(f"{region}: {exc}")
    seen, unique = set(), []
    for item in found:
        key = item["headline"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    with LOCK:
        NEWS["items"] = unique[:140]
        NEWS["updated"] = int(time.time())
        NEWS["sweeps"] += 1
        NEWS["error"] = "; ".join(errors[:3])


def yahoo(symbol: str, interval: str, span: str | int) -> dict:
    """span is a Yahoo range name, or a number of days back from now (0 means the full history)."""
    if isinstance(span, str):
        window = f"range={span}"
    else:
        now = int(time.time())
        window = f"period1={now - span * 86400 if span else 0}&period2={now}"
    url = YAHOO + quote(symbol, safe="") + f"?interval={interval}&{window}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=20) as response:
        return json.loads(response.read().decode())["chart"]["result"][0]


def session_base(meta: dict, opens: list) -> float | None:
    prev = meta.get("previousClose") or meta.get("chartPreviousClose")
    first = next((value for value in opens if value), None)
    if prev and first and abs(prev - first) / first > 0.012:
        return float(first)
    return float(prev or first or 0) or None


def day_change(meta: dict, price: float, base: float | None) -> tuple[float, float]:
    change = meta.get("fulldayChange")
    percent = meta.get("fulldayChangePercent")
    if change is None or percent is None:
        change = price - (base or price)
        percent = change / base * 100 if base else 0.0
    return change, percent


def summarize(group: str, name: str, symbol: str, result: dict) -> dict | None:
    meta = result["meta"]
    opens = [value for value in result["indicators"]["quote"][0]["open"] if value is not None]
    price = meta.get("regularMarketPrice")
    base = session_base(meta, opens)
    if price is None or not base or not opens:
        return None
    change, percent = day_change(meta, price, base)
    previous = price - change
    period = (meta.get("currentTradingPeriod") or {}).get("regular") or {}
    now = time.time()
    state = "OPEN" if period.get("start", 0) <= now <= period.get("end", 0) else "CLOSED"
    return {
        "country": group,
        "name": name,
        "symbol": symbol,
        "price": round(price, 2),
        "change": round(change, 2),
        "percent": round(percent, 2),
        "open": round(opens[0], 2),
        "high": round(meta.get("regularMarketDayHigh") or max(opens), 2),
        "low": round(meta.get("regularMarketDayLow") or min(opens), 2),
        "previous": round(previous, 2),
        "gap": round(opens[0] - previous, 2),
        "volume": int(meta.get("regularMarketVolume") or 0),
        "state": state,
    }


def fetch_row(row: tuple[str, str, str]) -> dict | None:
    group, name, symbol = row
    try:
        return summarize(group, name, symbol, yahoo(symbol, "5m", "1d"))
    except Exception:
        return None


def refresh(rows: list, target: dict, key: str) -> None:
    with ThreadPoolExecutor(max_workers=8) as pool:
        found = [item for item in pool.map(fetch_row, rows) if item]
    with LOCK:
        if found:
            target[key] = found
            target["updated"] = int(time.time())
        missing = len(rows) - len(found)
        target["error"] = f"{missing} symbols delayed" if missing else ""


def fit_window(interval: str, span: str) -> tuple[str, str]:
    interval = interval if interval in INTERVALS else "1m"
    span = span if span in SPANS else DEFAULT_SPAN[interval]
    reach = REACH.get(interval)
    if reach and SPANS[span][1] > reach:
        span = max((key for key, (_, days) in SPANS.items() if days <= reach), key=lambda key: SPANS[key][1])
    return interval, span


def bars_of(result: dict) -> list[dict]:
    block = result["indicators"]["quote"][0]
    candles = []
    for ts, open_, high, low, close, volume in zip(
        result.get("timestamp") or [], block["open"], block["high"], block["low"], block["close"], block["volume"]
    ):
        if None in (open_, high, low, close):
            continue
        candles.append(
            {"t": int(ts), "o": round(open_, 4), "h": round(high, 4), "l": round(low, 4), "c": round(close, 4), "v": int(volume or 0)}
        )
    return candles


def rolled(candles: list[dict], unit: str) -> list[dict]:
    """Merge bars into IST calendar days (D), ISO weeks (W) or months (M)."""
    out: list = []
    for c in candles:
        day = datetime.datetime.fromtimestamp(c["t"] + 19800, datetime.timezone.utc).date()
        key = day if unit == "D" else tuple(day.isocalendar()[:2]) if unit == "W" else (day.year, day.month)
        if out and out[-1][0] == key:
            bar = out[-1][1]
            bar["h"], bar["l"], bar["c"], bar["v"] = max(bar["h"], c["h"]), min(bar["l"], c["l"]), c["c"], bar["v"] + c["v"]
        else:
            out.append((key, dict(c)))
    return [bar for _, bar in out]


def hourly_rollup(symbol: str, unit: str) -> list[dict]:
    """Some NSE sector indices have no daily history on Yahoo, only two years of hourly bars."""
    return rolled(bars_of(yahoo(symbol, "60m", "2y")), unit)


def span_start(span_key: str) -> int:
    if span_key == "ALL":
        return 0
    if span_key == "YTD":
        year = time.gmtime(time.time() + 19800).tm_year
        return calendar.timegm((year, 1, 1, 0, 0, 0)) - 19800
    return int(time.time()) - SPANS[span_key][1] * 86400


def load_chart(symbol: str, interval_key: str, span_key: str) -> dict | None:
    if symbol not in CATALOG:
        return None
    interval_key, span_key = fit_window(interval_key, span_key)
    yahoo_span = SPANS[span_key][0]
    if interval_key == "D" and span_key == "ALL":
        yahoo_span = 0
    result = yahoo(symbol, INTERVALS[interval_key], yahoo_span)
    meta = result["meta"]
    candles = bars_of(result)
    note = ""
    if interval_key not in INTRADAY and len(candles) < 3:
        start = span_start(span_key)
        candles = [c for c in hourly_rollup(symbol, interval_key) if c["t"] >= start]
        meta = {**meta, "chartPreviousClose": None}
        note = "Yahoo has no daily history for this index, so these bars are built from hourly data (last 2 years)."
    if not candles:
        return {"error": "no bars for this range", "candles": [], "interval": interval_key, "span": span_key}
    price = meta.get("regularMarketPrice") or candles[-1]["c"]
    if interval_key in INTRADAY:
        base = session_base(meta, [c["o"] for c in candles]) or candles[0]["o"]
    else:
        base = meta.get("previousClose") or (candles[-2]["c"] if interval_key == "D" and len(candles) > 1 else candles[-1]["o"])
    change, percent = day_change(meta, price, base)
    if span_key == "1D":
        start = price - change
    elif span_key == "ALL" or not meta.get("chartPreviousClose"):
        start = candles[0]["o"]
    else:
        start = meta["chartPreviousClose"]
    group, name = CATALOG[symbol]
    return {
        "country": group,
        "name": name,
        "symbol": symbol,
        "interval": interval_key,
        "span": span_key,
        "price": round(price, 4),
        "change": round(change, 4),
        "percent": round(percent, 2),
        "previous": round(price - change, 4),
        "rangeChange": round(price - start, 4),
        "rangePercent": round((price / start - 1) * 100, 2) if start else None,
        "note": note,
        "candles": candles,
    }


def load_returns(symbol: str) -> dict:
    """Closing prices at the start of each lookback, so the page can compute returns against the live price."""
    closes = [(c["t"], c["c"]) for c in bars_of(yahoo(symbol, "1d", 0))]
    if len(closes) < 30:
        closes = [(c["t"], c["c"]) for c in hourly_rollup(symbol, "D")]
    if len(closes) < 2:
        raise RuntimeError("no daily history")
    last = closes[-1][0]
    bases: dict = {"5D": closes[-6][1] if len(closes) > 5 else None}
    for key, days in RETURN_DAYS:
        cutoff = last - days * 86400
        older = [close for ts, close in closes if ts <= cutoff]
        bases[key] = older[-1] if older else None
    year = time.gmtime(last + 19800).tm_year
    new_year = calendar.timegm((year, 1, 1, 0, 0, 0)) - 19800
    before = [close for ts, close in closes if ts < new_year]
    bases["YTD"] = before[-1] if before else None
    bases["ALL"] = closes[0][1]
    return {"symbol": symbol, "bases": bases, "since": closes[0][0], "fetched": int(time.time())}


NSE_STATE = {"opener": None, "made": 0.0}
NSE_LOCK = threading.Lock()
STORE: dict = {}


def nse_opener():
    with NSE_LOCK:
        if NSE_STATE["opener"] is None or time.time() - NSE_STATE["made"] > 240:
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            opener.open(urllib.request.Request("https://www.nseindia.com/option-chain", headers=NSE_HEADERS), timeout=15).read(256)
            NSE_STATE["opener"], NSE_STATE["made"] = opener, time.time()
        return NSE_STATE["opener"]


def nse_get(path: str):
    opener = nse_opener()
    try:
        request = urllib.request.Request("https://www.nseindia.com" + path, headers=NSE_HEADERS)
        with opener.open(request, timeout=20) as response:
            return json.loads(response.read().decode())
    except Exception:
        with NSE_LOCK:
            NSE_STATE["opener"] = None
        raise


def cached(key: str, ttl: int, loader):
    hit = STORE.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    try:
        value = loader()
    except Exception:
        if hit:
            return hit[1]
        raise
    STORE[key] = (time.time(), value)
    return value


def option_side(raw: dict | None) -> dict | None:
    if not raw:
        return None
    return {
        "oi": raw.get("openInterest") or 0,
        "chg": raw.get("changeinOpenInterest") or 0,
        "ltp": raw.get("lastPrice") or 0,
        "change": raw.get("change") or 0,
        "iv": raw.get("impliedVolatility") or 0,
        "vol": raw.get("totalTradedVolume") or 0,
        "bid": raw.get("buyPrice1") or 0,
        "bidQty": raw.get("buyQuantity1") or 0,
        "ask": raw.get("sellPrice1") or 0,
        "askQty": raw.get("sellQuantity1") or 0,
    }


def load_chain(expiry: str | None) -> dict:
    info = cached("nse:info", 600, lambda: nse_get("/api/option-chain-contract-info?symbol=NIFTY"))
    expiries = info.get("expiryDates") or []
    if not expiries:
        raise RuntimeError("NSE returned no expiry dates")
    if expiry not in expiries:
        expiry = expiries[0]
    raw = cached(
        "nse:chain:" + expiry,
        45,
        lambda: nse_get("/api/option-chain-v3?type=Indices&symbol=NIFTY&expiry=" + quote(expiry)),
    )
    records = raw.get("records") or {}
    rows = sorted(
        (
            {"strike": item["strikePrice"], "ce": option_side(item.get("CE")), "pe": option_side(item.get("PE"))}
            for item in records.get("data") or []
            if item.get("strikePrice") is not None
        ),
        key=lambda row: row["strike"],
    )
    ce_total = sum(row["ce"]["oi"] for row in rows if row["ce"])
    pe_total = sum(row["pe"]["oi"] for row in rows if row["pe"])

    def pain(level: float) -> float:
        return sum(
            (row["ce"]["oi"] if row["ce"] else 0) * max(0, level - row["strike"])
            + (row["pe"]["oi"] if row["pe"] else 0) * max(0, row["strike"] - level)
            for row in rows
        )

    strikes = [row["strike"] for row in rows]
    return {
        "expiry": expiry,
        "expiries": expiries,
        "spot": records.get("underlyingValue"),
        "timestamp": records.get("timestamp"),
        "rows": rows,
        "ceOi": ce_total,
        "peOi": pe_total,
        "pcr": round(pe_total / ce_total, 3) if ce_total else None,
        "maxPain": min(strikes, key=pain) if strikes else None,
    }


GOODRETURNS = "https://www.goodreturns.in"
BROWSER_HEADERS = {"User-Agent": NSE_HEADERS["User-Agent"], "Accept-Language": "en-IN,en;q=0.9"}
ABROAD = {
    "abu-dhabi", "ajman", "australia", "bahrain", "bangladesh", "calculator", "canada", "china", "dammam", "doha",
    "dubai", "england", "france", "fujairah", "germany", "japan", "kuwait", "malaysia", "muscat", "nepal",
    "new-zealand", "oman", "pakistan", "qatar", "ras-al-khaimah", "russia", "saudi-arabia", "sharjah", "singapore",
    "sri-lanka", "united-arab-emirates", "united-states",
}


def page_tables(path: str) -> tuple[str, list[list[list[str]]]]:
    request = urllib.request.Request(GOODRETURNS + path, headers=BROWSER_HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        page = response.read().decode("utf-8", "ignore")
    tables = []
    for block in re.findall(r"<table.*?</table>", page, re.S):
        rows = []
        for row in re.findall(r"<tr.*?</tr>", block, re.S):
            cells = [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", cell)).split()) for cell in re.findall(r"<t[hd].*?</t[hd]>", row, re.S)]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return page, tables


def rupees(text: str) -> tuple[float | None, float | None]:
    match = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:\(\s*([+-]?[\d,]+(?:\.\d+)?)\s*\))?", text or "")
    if not match:
        return None, None
    change = float(match.group(2).replace(",", "")) if match.group(2) else None
    return float(match.group(1).replace(",", "")), change


def table_named(tables: list, first: str) -> list:
    return next((table for table in tables if table[0] and table[0][0].lower() == first.lower()), [])


def gold_grams(tables: list) -> dict:
    head, *rows = table_named(tables, "Gram") or [[]]
    one = next((row for row in rows if row and row[0] == "1"), None)
    out = {}
    for i, purity in enumerate(head[1:], start=1):
        if one and i < len(one):
            price, change = rupees(one[i])
            out[purity] = {"price": price, "change": change}
    return out


def silver_rates(tables: list) -> dict:
    grams = table_named(tables, "Gram")
    one = next((row for row in grams[1:] if row and row[0] == "1"), None)
    history = table_named(tables, "Date")
    kg, kg_change = rupees(history[1][-1]) if len(history) > 1 else (None, None)
    gram = rupees(one[1])[0] if one and len(one) > 1 else None
    yesterday = rupees(one[2])[0] if one and len(one) > 2 else None
    return {
        "gram": gram,
        "gramChange": gram - yesterday if gram is not None and yesterday is not None else None,
        "kg": kg,
        "kgChange": kg_change,
    }


def gold_history(tables: list) -> list:
    rows = []
    for row in table_named(tables, "Date")[1:]:
        g24, c24 = rupees(row[1]) if len(row) > 1 else (None, None)
        g22, c22 = rupees(row[2]) if len(row) > 2 else (None, None)
        rows.append({"date": row[0], "g24": g24, "c24": c24, "g22": g22, "c22": c22})
    return rows


def silver_history(tables: list) -> list:
    rows = []
    for row in table_named(tables, "Date")[1:]:
        kg, change = rupees(row[-1])
        rows.append({"date": row[0], "kg": kg, "change": change})
    return rows


def weight_sheet(tables: list) -> dict:
    """The 'Gram' table as rows of weight -> [price, change] per column (24K/22K/18K, or one 'Rate' column)."""
    head, *rows = table_named(tables, "Gram") or [[]]
    daily = "Today" in head
    labels = ["Rate"] if daily else head[1:]
    out = []
    for row in rows:
        grams = rupees(row[0])[0] if row else None
        if not grams:
            continue
        if daily:
            today = rupees(row[head.index("Today")])[0] if len(row) > head.index("Today") else None
            before = rupees(row[head.index("Yesterday")])[0] if "Yesterday" in head and len(row) > head.index("Yesterday") else None
            cells = [[today, today - before if today is not None and before is not None else None]]
        else:
            cells = [list(rupees(cell)) for cell in row[1:len(labels) + 1]]
        out.append({"grams": grams, "cells": cells})
    return {"labels": labels, "rows": out}


def load_bullion() -> dict:
    gold_page, gold = page_tables("/gold-rates/")
    _, silver = page_tables("/silver-rates/")
    try:
        platinum = weight_sheet(page_tables("/platinum-price.html")[1])
    except Exception:
        platinum = {"labels": [], "rows": []}
    silver_by_city = {row[0]: row for row in table_named(silver, "City")[1:]}
    cities = []
    for row in table_named(gold, "City")[1:]:
        s_row = silver_by_city.get(row[0], [])
        cities.append(
            {
                "city": row[0],
                "slug": row[0].lower().replace(" ", "-"),
                "g24": rupees(row[1])[0] if len(row) > 1 else None,
                "g22": rupees(row[2])[0] if len(row) > 2 else None,
                "g18": rupees(row[3])[0] if len(row) > 3 else None,
                "skg": rupees(s_row[-1])[0] if s_row else None,
            }
        )
    slugs = sorted(set(re.findall(r"/gold-rates/([a-z-]+)\.html", gold_page)) - ABROAD)
    if not cities or not gold_grams(gold):
        raise RuntimeError("GoodReturns page layout changed")
    return {
        "gold": gold_grams(gold),
        "silver": silver_rates(silver),
        "cities": cities,
        "goldHistory": gold_history(gold),
        "silverHistory": silver_history(silver),
        "cityList": [{"slug": slug, "name": slug.replace("-", " ").title()} for slug in slugs],
        "sheets": {"gold": weight_sheet(gold), "silver": weight_sheet(silver), "platinum": platinum},
        "fetched": int(time.time()),
    }


def load_city(slug: str) -> dict:
    _, gold = page_tables(f"/gold-rates/{slug}.html")
    grams = gold_grams(gold)
    if not grams:
        raise RuntimeError("no gold rates for this city")
    try:
        _, silver = page_tables(f"/silver-rates/{slug}.html")
        silver_today, silver_sheet = silver_rates(silver), weight_sheet(silver)
    except Exception:
        silver_today, silver_sheet = {}, {"labels": [], "rows": []}
    return {
        "city": slug.replace("-", " ").title(),
        "slug": slug,
        "g24": (grams.get("24K") or {}).get("price"),
        "g22": (grams.get("22K") or {}).get("price"),
        "g18": (grams.get("18K") or {}).get("price"),
        "skg": silver_today.get("kg"),
        "gold": grams,
        "silver": silver_today,
        "sheets": {"gold": weight_sheet(gold), "silver": silver_sheet},
        "fetched": int(time.time()),
    }


IBJA_COLUMNS = ["999", "995", "916", "750", "585", "silver", "platinum"]


def load_ibja() -> dict:
    """India Bullion and Jewellers Association benchmark: gold per 10 g, silver per kg, platinum per 10 g."""
    request = urllib.request.Request("https://ibjarates.com/", headers=BROWSER_HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        page = response.read().decode("utf-8", "ignore")
    rows = []
    for session, chunk in zip(("AM", "PM"), page.split('class="table-striped"')[1:3]):
        for row in re.findall(r"<tr.*?</tr>", chunk.split("</table>")[0], re.S):
            cells = [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split()) for c in re.findall(r"<t[hd].*?</t[hd]>", row, re.S)]
            if len(cells) >= 8 and re.fullmatch(r"\d\d/\d\d/\d{4}", cells[0]):
                day, month, year = cells[0].split("/")
                values = [float(v.replace(",", "")) if re.fullmatch(r"[\d,.]+", v) else None for v in cells[1:8]]
                rows.append({"date": f"{year}-{month}-{day}", "session": session, "rates": dict(zip(IBJA_COLUMNS, values))})
    if not rows:
        raise RuntimeError("IBJA page layout changed")
    rows.sort(key=lambda r: (r["date"], r["session"]), reverse=True)
    return {"rows": rows, "latest": rows[0], "todayPublished": "TodayRatesTableDataNo" not in page, "fetched": int(time.time())}


SIGNAL_UNIVERSE = (
    [(symbol, "Index") for symbol in ("^NSEI", "^NSEBANK", "^CNXIT", "^BSESN")]
    + [(symbol, "Index") for group, _, symbol in MARKETS if group == "Sector"]
    + [(symbol, "Stock") for _, _, symbol in STOCK_ROWS]
    + [(symbol, "Commodity") for symbol in ("GC=F", "SI=F", "PL=F", "HG=F", "CL=F", "BZ=F", "NG=F")]
    + [("INR=X", "Currency")]
    + [(symbol, "Crypto") for symbol in ("BTC-USD", "ETH-USD")]
    + [(symbol, "World") for symbol in ("^GSPC", "^IXIC", "^DJI", "^N225", "^HSI", "^FTSE", "^GDAXI")]
)
INDICATORS = {"updated": 0, "items": {}, "error": ""}
POSITIVE = re.compile(
    r"\b(?:surg\w*|soar\w*|jump\w*|rall(?:y|ies|ied|ying)|gain(?:s|ed|ing)?|ris(?:e|es|ing)|rose|climb\w*|record high|all-time high|"
    r"fresh high|beat(?:s|ing)?|upgrad\w*|outperform\w*|bullish|boost\w*|approv\w*|wins?|won|bags?|expan\w*|dividend|buyback|"
    r"rebound\w*|recover\w*|upbeat|robust|strong(?:er|ly)?|optimis\w*|inflows?|higher|advance[sd]?)\b",
    re.I,
)
NEGATIVE = re.compile(
    r"\b(?:fall(?:s|ing)?|fell|drop(?:s|ped|ping)?|slump\w*|plung\w*|tumbl\w*|crash\w*|slid(?:e|es|ing)?|declin\w*|loss(?:es)?|"
    r"los(?:e|es|ing)|weak(?:er|ness|ens?)?|miss(?:es|ed)?|downgrad\w*|underperform\w*|bearish|probe\w*|fraud|penalt\w*|fined|"
    r"bans?|banned|lawsuit|default\w*|resign\w*|outflows?|sell-?offs?|selling|fears?|concerns?|worr\w*|warn\w*|tariffs?|war|"
    r"recession|slowdown|lower|cuts?|slips?|slipped|sheds?|dips?|dipped|sinks?|sank|volatil\w*|crisis|panic|"
    r"eas(?:e|es|ed|ing)|retreat\w*|hack\w*|halts?|halted|pauses?)\b",
    re.I,
)
PHRASES = [
    (re.compile(r"snap\w* (?:an? |its |their )?(?:[\w-]+ )?losing streak", re.I), 1),
    (re.compile(r"snap\w* (?:an? |its |their )?(?:[\w-]+ )?winning streak", re.I), -1),
    (re.compile(r"(?:fears?|worries|concerns?|tensions?) (?:eas\w*|reced\w*|fad\w*|cool\w*)", re.I), 1),
    (re.compile(r"profit[- ](?:booking|taking)", re.I), -1),
    (re.compile(r"\bup \d[\d,.]*\s*(?:%|points?|pts)", re.I), 1),
    (re.compile(r"\bdown \d[\d,.]*\s*(?:%|points?|pts)", re.I), -1),
    (re.compile(r"rate cuts?", re.I), 1),
    (re.compile(r"rate hikes?", re.I), -1),
    (re.compile(r"short[- ]covering", re.I), 1),
]
CLAUSE = re.compile(r"[,;:|–—]| - |\b(?:as|while|but|after|amid|despite|though|although|whereas)\b", re.I)
TOPICS = {
    "^NSEI": r"\bnifty\b(?! bank)|\bsensex\b|dalal street|indian (?:stocks|shares|equities|markets?)",
    "^BSESN": r"\bsensex\b|dalal street",
    "^NSEBANK": r"bank nifty|nifty bank|\bbank(?:ing)? stocks\b|\bRBI\b|\blenders?\b|psu banks?",
    "^CNXIT": r"(?-i:\bIT\b) (?:stocks|shares|sector|index|majors?|services)|software (?:services|exports)",
    "^CNXAUTO": r"\bauto (?:stocks|sales|sector|makers?)\b|automakers?|car sales|two-wheeler",
    "^CNXPHARMA": r"pharma|drugmakers?|\bUSFDA\b",
    "^CNXFMCG": r"\bFMCG\b|consumer goods|rural demand",
    "^CNXMETAL": r"metal stocks|\bsteel\b|\bmining\b|aluminium",
    "^CNXREALTY": r"realty|real estate|housing sales",
    "^CNXENERGY": r"energy stocks|power (?:stocks|sector|demand)|oil (?:and|&) gas",
    "GC=F": r"\bgold\b(?! (?:stocks?|miners?|mining|shares))",
    "SI=F": r"\bsilver\b",
    "PL=F": r"\bplatinum\b",
    "HG=F": r"\bcopper\b",
    "CL=F": r"\bcrude\b|\boil prices?\b|\bOPEC\b|\bWTI\b",
    "BZ=F": r"\bbrent\b|\bcrude\b|\bOPEC\b",
    "NG=F": r"natural gas|\bLNG\b",
    "INR=X": r"\brupee\b",
    "BTC-USD": r"bitcoin|\bcrypto\w*|\bBTC\b",
    "ETH-USD": r"\bether(?:eum)?\b|\bcrypto\w*",
    "^GSPC": r"wall street|s&p 500|\bUS stocks\b",
    "^IXIC": r"nasdaq|tech stocks|wall street",
    "^DJI": r"\bdow\b|wall street",
    "^N225": r"nikkei|japan(?:ese)? (?:stocks|shares)",
    "^HSI": r"hang seng|hong kong (?:stocks|shares)|chinese (?:stocks|shares)",
    "^FTSE": r"\bFTSE\b|(?:UK|London|British) (?:stocks|shares)",
    "^GDAXI": r"\bDAX\b|german (?:stocks|shares)|european (?:stocks|shares)",
}
STOCK_TOPICS = {
    "RELIANCE": r"Reliance(?! Power| Infra\w*| Capital| Communications| Home)|\bRIL\b",
    "SBIN": r"\bSBI\b(?! Life| Card| Mutual| MF)|State Bank",
    "LT": r"\bL&T\b|Larsen",
    "M&M": r"(?<!Tech )(?<!Kotak )Mahindra(?: & Mahindra)?(?! Finance| Lifespace| Logistics| Bank)|\bM&M\b",
    "ETERNAL": r"Zomato|Eternal(?: Ltd)?\b(?= shares| stock| Q\d|,| share)|Blinkit",
    "TMPV": r"Tata Motors",
    "BEL": r"\bBEL\b|Bharat Electronics",
    "HINDUNILVR": r"\bHUL\b|Hindustan Unilever",
    "INDIGO": r"IndiGo|InterGlobe",
    "DRREDDY": r"Dr\.? Reddy",
    "KOTAKBANK": r"Kotak(?! Securities| Mutual| MF)",
    "ICICIBANK": r"ICICI Bank",
    "BHARTIARTL": r"Airtel|Bharti",
    "EICHERMOT": r"Eicher|Royal Enfield",
    "TECHM": r"Tech Mahindra|TechM",
    "HCLTECH": r"HCL ?Tech\w*",
    "INFY": r"Infosys|\bINFY\b",
    "APOLLOHOSP": r"Apollo Hospitals?",
    "NESTLEIND": r"Nestle",
    "ULTRACEMCO": r"UltraTech",
    "COALINDIA": r"Coal India",
    "POWERGRID": r"Power Grid",
}


def ema_series(values: list, n: int) -> list:
    out = [None] * len(values)
    if len(values) < n:
        return out
    prev = sum(values[:n]) / n
    out[n - 1] = prev
    k = 2 / (n + 1)
    for i in range(n, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi_series(closes: list, n: int = 14) -> list:
    out = [None] * len(closes)
    if len(closes) <= n:
        return out
    moves = [b - a for a, b in zip(closes, closes[1:])]
    gain = sum(max(m, 0) for m in moves[:n]) / n
    loss = sum(max(-m, 0) for m in moves[:n]) / n
    out[n] = 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
    for i, m in enumerate(moves[n:], start=n + 1):
        gain = (gain * (n - 1) + max(m, 0)) / n
        loss = (loss * (n - 1) + max(-m, 0)) / n
        out[i] = 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
    return out


def atr_series(highs: list, lows: list, closes: list, n: int = 14) -> list:
    out = [None] * len(closes)
    ranges = [highs[0] - lows[0]] + [
        max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])) for i in range(1, len(closes))
    ]
    if len(ranges) < n:
        return out
    value = sum(ranges[:n]) / n
    out[n - 1] = value
    for i in range(n, len(ranges)):
        value = (value * (n - 1) + ranges[i]) / n
        out[i] = value
    return out


def macd_hist_series(closes: list) -> list:
    fast, slow = ema_series(closes, 12), ema_series(closes, 26)
    macd = [a - b if a is not None and b is not None else None for a, b in zip(fast, slow)]
    out = [None] * len(closes)
    start = next((i for i, v in enumerate(macd) if v is not None), None)
    if start is None:
        return out
    for k, sig in enumerate(ema_series(macd[start:], 9)):
        if sig is not None:
            out[start + k] = macd[start + k] - sig
    return out


def indicator_series(candles: list[dict]) -> dict:
    closes, highs, lows = [c["c"] for c in candles], [c["h"] for c in candles], [c["l"] for c in candles]
    return {
        "o": [c["o"] for c in candles], "h": highs, "l": lows, "c": closes, "v": [c["v"] for c in candles],
        "ema20": ema_series(closes, 20), "ema50": ema_series(closes, 50), "ema200": ema_series(closes, 200),
        "rsi": rsi_series(closes), "hist": macd_hist_series(closes), "atr": atr_series(highs, lows, closes),
    }


def indicators_at(s: dict, i: int) -> dict:
    """Indicator values as they stood at the close of bar i, using only bars up to i."""
    highs, lows, volumes = s["h"], s["l"], s["v"]
    recent = [v for v in volumes[max(0, i - 20):i] if v]
    return {
        "close": s["c"][i], "ema20": s["ema20"][i], "ema50": s["ema50"][i], "ema200": s["ema200"][i],
        "rsi": s["rsi"][i], "hist": [h for h in s["hist"][max(0, i - 3):i + 1] if h is not None], "atr": s["atr"][i],
        "hi20": max(highs[max(0, i - 20):i] or highs[i:i + 1]), "lo20": min(lows[max(0, i - 20):i] or lows[i:i + 1]),
        "hi52": max(highs[max(0, i - 251):i + 1]), "lo52": min(lows[max(0, i - 251):i + 1]),
        "avgVol": sum(recent) / len(recent) if recent else 0, "lastVol": volumes[i],
    }


def indicators_for(symbol: str) -> dict | None:
    candles = bars_of(yahoo(symbol, "1d", "2y"))
    if len(candles) < 60:
        candles = hourly_rollup(symbol, "D")
    if len(candles) < 60:
        return None
    s, last = indicator_series(candles), len(candles) - 1
    closes = s["c"]
    return {
        **indicators_at(s, last),
        "ret1m": closes[-1] / closes[-22] - 1 if len(closes) > 22 else None,
        "ret3m": closes[-1] / closes[-64] - 1 if len(closes) > 64 else None,
        "spark": closes[-60:],
    }


def refresh_indicators() -> None:
    def one(item):
        try:
            return item[0], indicators_for(item[0])
        except Exception:
            return item[0], None

    with ThreadPoolExecutor(max_workers=6) as pool:
        found = {symbol: data for symbol, data in pool.map(one, SIGNAL_UNIVERSE) if data}
    with LOCK:
        INDICATORS["items"].update(found)
        if found:
            INDICATORS["updated"] = int(time.time())
        missing = len(SIGNAL_UNIVERSE) - len(found)
        INDICATORS["error"] = f"{missing} instruments without daily history" if missing else ""
    STORE.pop("signals", None)


def topic_patterns() -> dict:
    patterns = {symbol: re.compile(rx, re.I) for symbol, rx in TOPICS.items()}
    for ticker, name in STOCKS:
        rx = STOCK_TOPICS.get(ticker) or re.escape(name) + (rf"|\b{ticker}\b" if ticker.isalpha() and len(ticker) >= 3 else "")
        patterns[ticker + ".NS"] = re.compile(rx)
    return patterns


PATTERNS = topic_patterns()


def headline_tone(text: str) -> int:
    score = 0
    for rx, value in PHRASES:
        score += value * len(rx.findall(text))
        text = rx.sub(" ", text)
    score += len(POSITIVE.findall(text)) - len(NEGATIVE.findall(text))
    return (score > 0) - (score < 0)


def topic_tone(headline: str, pattern: re.Pattern) -> int:
    """Score only the clauses that mention the instrument, so 'stocks gain as oil eases' reads bearish for oil."""
    clauses = [c for c in CLAUSE.split(headline) if c and pattern.search(c)] or [headline]
    total = sum(headline_tone(c) for c in clauses)
    return (total > 0) - (total < 0)


def scored_news(items: list) -> list:
    now = time.time()
    out = []
    for item in items:
        try:
            age = (now - email.utils.parsedate_to_datetime(item["published"]).timestamp()) / 3600
        except Exception:
            age = 12
        out.append({**item, "weight": 1.0 if age < 6 else 0.6 if age < 24 else 0.3})
    return out


def news_for(symbol: str, news: list) -> tuple[float, list]:
    pattern = PATTERNS.get(symbol)
    if not pattern:
        return 0.0, []
    hits = [{**item, "tone": topic_tone(item["headline"], pattern)} for item in news if pattern.search(item["headline"])]
    raw = sum(item["tone"] * item["weight"] for item in hits)
    if symbol == "INR=X":
        raw = -raw
    return max(-3.0, min(3.0, raw)), hits[:6]


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def fo_read() -> dict | None:
    try:
        chain = load_chain(None)
    except Exception:
        return None
    rows, spot = chain["rows"], chain["spot"]
    if not rows or not spot:
        return None
    ai = min(range(len(rows)), key=lambda i: abs(rows[i]["strike"] - spot))
    near, book = rows[max(0, ai - 10): ai + 11], rows[max(0, ai - 5): ai + 6]
    side_sum = lambda group, side, key: sum((r[side] or {}).get(key, 0) for r in group)
    ce_chg, pe_chg = side_sum(near, "ce", "chg"), side_sum(near, "pe", "chg")
    ce_bid, ce_ask = side_sum(book, "ce", "bidQty"), side_sum(book, "ce", "askQty")
    pe_bid, pe_ask = side_sum(book, "pe", "bidQty"), side_sum(book, "pe", "askQty")
    depth = ce_bid + ce_ask + pe_bid + pe_ask
    imbalance = ((ce_bid - ce_ask) - (pe_bid - pe_ask)) / depth if depth else 0.0
    day, mon, year = chain["expiry"].split("-")
    expiry_ts = calendar.timegm((int(year), MONTH_INDEX[mon], int(day), 10, 0, 0))
    days_left = max(0.0, (expiry_ts - time.time()) / 86400)
    atm = rows[ai]
    ivs = [side["iv"] for side in (atm["ce"], atm["pe"]) if side and side.get("iv")]
    parts = []
    pcr, pain = chain["pcr"], chain["maxPain"]
    if pcr:
        if pcr >= 1.5:
            parts.append((f"PCR {pcr:.2f}: very heavy put writing, so an overbought pullback is possible", 2))
        elif pcr >= 1.1:
            parts.append((f"PCR {pcr:.2f}: put writers are defending support", 5))
        elif pcr <= 0.6:
            parts.append((f"PCR {pcr:.2f}: very heavy call writing, so an oversold bounce is possible", -2))
        elif pcr <= 0.9:
            parts.append((f"PCR {pcr:.2f}: call writers are capping the upside", -5))
        else:
            parts.append((f"PCR {pcr:.2f}: balanced positioning", 0))
    moved = abs(ce_chg) + abs(pe_chg)
    if moved:
        share = (pe_chg - ce_chg) / moved
        if abs(share) >= 0.15:
            parts.append((f"Today's OI build-up near ATM favours {'put' if share > 0 else 'call'} writers (calls {int(ce_chg):+,}, puts {int(pe_chg):+,})", round(clamp(share * 6, -4, 4))))
    if pain and days_left <= 3:
        gap = (pain - spot) / spot * 100
        if abs(gap) >= 0.4:
            parts.append((f"Max pain {pain:,.0f} sits {abs(gap):.1f}% {'above' if gap > 0 else 'below'} spot with {days_left:.1f} days to expiry", round(clamp(gap * 2, -3, 3))))
    if depth and abs(imbalance) >= 0.08:
        parts.append((f"Option order book near ATM leans to {'buyers of calls and sellers of puts' if imbalance > 0 else 'buyers of puts and sellers of calls'} (bid/ask quantity imbalance {imbalance:+.0%})", round(clamp(imbalance * 20, -4, 4))))
    return {
        "spot": spot, "pcr": pcr, "maxPain": pain, "expiry": chain["expiry"], "daysLeft": round(days_left, 1),
        "ceChg": ce_chg, "peChg": pe_chg, "imbalance": round(imbalance, 3), "bidQty": ce_bid + pe_bid, "askQty": ce_ask + pe_ask,
        "atmIv": round(sum(ivs) / len(ivs), 2) if ivs else None,
        "parts": [{"text": t, "points": p} for t, p in parts], "points": clamp(sum(p for _, p in parts), -15, 15),
    }


def macro_context(quotes: dict, nifty_news: float) -> dict:
    pct = lambda symbol: (quotes.get(symbol) or {}).get("percent") or 0.0
    es, crude, usdinr, dxy, vix, tnx = pct("ES=F"), pct("CL=F"), pct("INR=X"), pct("DX-Y.NYB"), pct("^INDIAVIX"), pct("^TNX")
    asia = (pct("^N225") + pct("^HSI")) / 2
    fii_rows = (STORE.get("nse:fii") or (0, []))[1] or []
    fii = next((r for r in fii_rows if re.search(r"FII|FPI", str(r.get("category")))), None)
    fii_net = float(fii["netValue"]) if fii and fii.get("netValue") not in (None, "") else 0.0
    groups: dict[str, list] = {key: [] for key in ("India", "Metals", "Energy", "Industrial", "Crypto", "Currency", "US", "Global")}

    def add(group: str, text: str, points: float) -> None:
        if round(points):
            groups[group].append({"text": text, "points": round(points)})

    if abs(es) >= 0.15:
        add("India", f"US futures {es:+.2f}% set the global risk mood", clamp(es * 4, -4, 4))
        add("US", f"US futures {es:+.2f}%", clamp(es * 4, -4, 4))
        add("Industrial", f"Global risk mood: US futures {es:+.2f}%", clamp(es * 2, -2, 2))
        add("Metals", f"{'Risk-off' if es < 0 else 'Risk-on'} mood (US futures {es:+.2f}%) {'helps' if es < 0 else 'weighs on'} safe havens", clamp(-es * 2, -3, 3))
        add("Crypto", f"Risk appetite: US futures {es:+.2f}%", clamp(es * 3, -4, 4))
    if abs(asia) >= 0.3:
        add("India", f"Asian markets {asia:+.2f}% on average (Nikkei, Hang Seng)", clamp(asia * 1.5, -2, 2))
        add("Global", f"Asia {asia:+.2f}%", clamp(asia * 2, -3, 3))
    if abs(crude) >= 0.5:
        add("India", f"Crude {crude:+.2f}% ({'costlier' if crude > 0 else 'cheaper'} imports for India)", clamp(-crude * 1.2, -2, 2))
        add("Currency", f"Crude {crude:+.2f}% changes India's import bill", clamp(crude, -2, 2))
    if abs(usdinr) >= 0.1:
        add("India", f"Rupee {'weaker' if usdinr > 0 else 'stronger'} (USD/INR {usdinr:+.2f}%)", clamp(-usdinr * 8, -2, 2))
    if abs(dxy) >= 0.2:
        add("India", f"Dollar index {dxy:+.2f}% ({'pulls' if dxy > 0 else 'eases'} foreign money {'out of' if dxy > 0 else 'into'} emerging markets)", clamp(-dxy * 4, -2, 2))
        add("Metals", f"Dollar index {dxy:+.2f}% (metals usually move opposite the dollar)", clamp(-dxy * 5, -4, 4))
        add("Energy", f"Dollar index {dxy:+.2f}%", clamp(-dxy * 2, -2, 2))
        add("Crypto", f"Dollar index {dxy:+.2f}%", clamp(-dxy * 3, -3, 3))
        add("Currency", f"Dollar index {dxy:+.2f}% (a stronger dollar lifts USD/INR)", clamp(dxy * 4, -3, 3))
    if abs(tnx) >= 1:
        add("Metals", f"US 10-year yield {tnx:+.1f}% ({'higher yields hurt' if tnx > 0 else 'lower yields help'} non-yielding metals)", clamp(-tnx * 0.8, -3, 3))
    if abs(vix) >= 3:
        add("India", f"India VIX {vix:+.1f}% (fear {'rising' if vix > 0 else 'easing'})", clamp(-vix / 3, -3, 3))
    if abs(fii_net) >= 500:
        add("India", f"FIIs {'bought' if fii_net > 0 else 'sold'} ₹{abs(fii_net):,.0f} crore in cash last session", clamp(fii_net / 1500, -3, 3))
        add("Currency", f"FII {'inflows support' if fii_net > 0 else 'outflows pressure'} the rupee", clamp(-fii_net / 1500, -3, 3))
    if abs(nifty_news) >= 0.5:
        add("India", f"Indian market headlines lean {'positive' if nifty_news > 0 else 'negative'}", clamp(nifty_news, -2, 2))
    return {key: {"parts": parts, "points": clamp(sum(p["points"] for p in parts), -10, 10)} for key, parts in groups.items()}


MONTH_INDEX = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}
INDIA_KINDS = {"Index", "Stock"}
FO_WEIGHT = {"^NSEI": 1.0, "^BSESN": 0.8, "^NSEBANK": 0.5}
HOW_TO = {
    "^NSEI": "Nifty futures or options (see the options idea above)",
    "^NSEBANK": "Bank Nifty futures or options",
    "^BSESN": "Sensex options on BSE",
    "GC=F": "MCX gold futures, gold ETFs or Sovereign Gold Bonds",
    "SI=F": "MCX silver futures or silver ETFs",
    "INR=X": "NSE USD/INR currency futures or options",
}


def macro_group(symbol: str, kind: str) -> str:
    if kind in INDIA_KINDS:
        return "India"
    if symbol in ("GC=F", "SI=F", "PL=F"):
        return "Metals"
    if symbol in ("CL=F", "BZ=F", "NG=F"):
        return "Energy"
    if symbol == "HG=F":
        return "Industrial"
    if kind == "Crypto":
        return "Crypto"
    if kind == "Currency":
        return "Currency"
    return "US" if symbol in ("^GSPC", "^IXIC", "^DJI") else "Global"


def how_to(symbol: str, kind: str, side: str) -> str:
    if symbol in HOW_TO:
        return HOW_TO[symbol]
    if kind == "Stock":
        return "Cash (swing) or stock futures" if side == "BUY" else "Exit longs; short only through stock futures or puts (no overnight short selling in cash)"
    if kind == "Index":
        return "No direct F&O contract; trade the sector's leading stocks"
    if kind == "Commodity":
        return "MCX futures"
    if kind == "Crypto":
        return "Spot on an Indian exchange (30% tax on gains plus 1% TDS on sales)"
    return "International mutual funds or ETFs that track this index"


def signal_label(score: int) -> str:
    return "STRONG BUY" if score >= 55 else "BUY" if score >= 20 else "STRONG SELL" if score <= -55 else "SELL" if score <= -20 else "NEUTRAL"


def technical_parts(symbol: str, kind: str, price: float, percent: float, volume: float, ind: dict, nifty_percent: float | None) -> tuple[list, int]:
    """Trend, momentum, breakout, volume and relative-strength points. The backtest replays exactly this."""
    parts: list[dict] = []

    def add(factor: str, text: str, points: float) -> None:
        parts.append({"factor": factor, "text": text, "points": round(points)})

    e20, e50, e200 = ind["ema20"], ind["ema50"], ind["ema200"]
    above = [n for n, e in (("20", e20), ("50", e50), ("200", e200)) if e and price > e]
    below = [n for n, e in (("20", e20), ("50", e50), ("200", e200)) if e and price <= e]
    trend = (8 if e20 and price > e20 else -8 if e20 else 0) + (6 if e200 and price > e200 else -6 if e200 else 0)
    if above:
        add("trend", f"Price is above its {', '.join(above)}-day average{'s' if len(above) > 1 else ''}", (8 if "20" in above else 0) + (6 if "200" in above else 0))
    if below:
        add("trend", f"Price is below its {', '.join(below)}-day average{'s' if len(below) > 1 else ''}", -(8 if "20" in below else 0) - (6 if "200" in below else 0))
    if e20 and e50:
        trend += 8 if e20 > e50 else -8
        add("trend", "20-day average is above the 50-day (short-term uptrend)" if e20 > e50 else "20-day average is below the 50-day (short-term downtrend)", 8 if e20 > e50 else -8)
    if e50 and e200:
        trend += 8 if e50 > e200 else -8
        add("trend", "50-day average is above the 200-day (long-term uptrend)" if e50 > e200 else "50-day average is below the 200-day (long-term downtrend)", 8 if e50 > e200 else -8)

    rsi = ind["rsi"]
    if rsi is not None:
        if rsi > 70:
            add("momentum", f"RSI {rsi:.0f}: overbought, so a pullback is likely", 2)
        elif rsi >= 55:
            add("momentum", f"RSI {rsi:.0f}: buyers have momentum", 8)
        elif rsi > 45:
            add("momentum", f"RSI {rsi:.0f}: no clear momentum", 0)
        elif rsi >= 30:
            add("momentum", f"RSI {rsi:.0f}: sellers have momentum", -8)
        else:
            add("momentum", f"RSI {rsi:.0f}: oversold, so a bounce is possible", -2)
    hist = ind["hist"]
    if hist:
        crossed = any((a > 0) != (b > 0) for a, b in zip(hist, hist[1:]))
        if crossed:
            add("momentum", f"MACD crossed {'above' if hist[-1] > 0 else 'below'} its signal line in the last 3 sessions", 12 if hist[-1] > 0 else -12)
        else:
            add("momentum", f"MACD is {'above' if hist[-1] > 0 else 'below'} its signal line", 6 if hist[-1] > 0 else -6)

    if price > ind["hi20"]:
        add("breakout", f"Broke above the 20-day high of {ind['hi20']:,.2f}", 10)
    elif price < ind["lo20"]:
        add("breakout", f"Broke below the 20-day low of {ind['lo20']:,.2f}", -10)
    if price >= ind["hi52"] * 0.98:
        add("breakout", f"Within 2% of the 52-week high ({ind['hi52']:,.2f})", 0)
    elif price <= ind["lo52"] * 1.02:
        add("breakout", f"Within 2% of the 52-week low ({ind['lo52']:,.2f})", 0)

    if ind["avgVol"] and volume and abs(percent) >= 0.3:
        ratio = volume / ind["avgVol"]
        if ratio >= 1.5:
            add("volume", f"Volume is {ratio:.1f}× the 20-day average on a {percent:+.2f}% day", 5 if percent > 0 else -5)

    if kind in INDIA_KINDS and symbol != "^NSEI" and nifty_percent is not None:
        diff = percent - nifty_percent
        if abs(diff) >= 0.3:
            add("relative", f"{'Outperforming' if diff > 0 else 'Underperforming'} Nifty by {abs(diff):.2f}% today", clamp(diff * 3, -6, 6))
    elif abs(percent) >= 0.3:
        add("relative", f"{'Up' if percent > 0 else 'Down'} {abs(percent):.2f}% today", clamp(percent * 2, -4, 4))
    return parts, trend


def score_one(symbol: str, kind: str, ind: dict, live: dict | None, ctx: dict) -> dict:
    price = live["price"] if live else ind["close"]
    percent = live["percent"] if live else 0.0
    nifty = ctx["quotes"].get("^NSEI")
    parts, trend = technical_parts(
        symbol, kind, price, percent, (live or {}).get("volume") or ind["lastVol"], ind, nifty["percent"] if nifty else None
    )

    def add(factor: str, text: str, points: float) -> None:
        parts.append({"factor": factor, "text": text, "points": round(points)})

    tone, hits = news_for(symbol, ctx["news"])
    if hits:
        mood = "positive" if tone > 0.2 else "negative" if tone < -0.2 else "mixed"
        add("news", f"{len(hits)} recent headline{'s' if len(hits) > 1 else ''} mention this, tone {mood}", tone * 5)

    macro = ctx["macro"][macro_group(symbol, kind)]
    if macro["points"]:
        add("macro", "; ".join(p["text"] for p in macro["parts"][:3]), macro["points"])

    fo = ctx["fo"]
    weight = FO_WEIGHT.get(symbol, 0.33 if kind in INDIA_KINDS else 0)
    if fo and weight and fo["points"]:
        lead = "Nifty options positioning" if weight < 0.5 else "Options positioning"
        add("fo", f"{lead}: " + "; ".join(p["text"] for p in fo["parts"] if p["points"])[:220], fo["points"] * weight)

    factors = {}
    for p in parts:
        factors[p["factor"]] = factors.get(p["factor"], 0) + p["points"]
    score = round(clamp(sum(factors.values()), -100, 100))
    signal = signal_label(score)
    side = "BUY" if score >= 20 else "SELL" if score <= -20 else ""
    atr = ind["atr"] or 0
    stop = price - 1.5 * atr if side == "BUY" else price + 1.5 * atr if side == "SELL" else None
    target = price + 3 * atr if side == "BUY" else price - 3 * atr if side == "SELL" else None
    voting = [v for v in factors.values() if v]
    group, name = CATALOG.get(symbol, (kind, symbol))
    return {
        "symbol": symbol, "name": name, "kind": kind, "group": group, "price": price, "percent": percent,
        "score": score, "signal": signal, "side": side,
        "agree": sum(1 for v in voting if score and (v > 0) == (score > 0)), "factorsCount": len(voting),
        "entry": price if side else None, "stop": stop, "target": target, "atr": atr,
        "rsi": ind["rsi"], "trend": "Uptrend" if trend >= 16 else "Downtrend" if trend <= -16 else "Sideways",
        "factors": factors, "reasons": sorted(parts, key=lambda p: -abs(p["points"])),
        "levels": {k: ind[k] for k in ("ema20", "ema50", "ema200", "hi20", "lo20", "hi52", "lo52")},
        "ret1m": ind["ret1m"], "ret3m": ind["ret3m"], "spark": ind["spark"],
        "news": [{"headline": h["headline"], "link": h["link"], "source": h["source"], "tone": h["tone"]} for h in hits],
        "how": how_to(symbol, kind, side or "BUY"),
    }


def build_signals() -> dict:
    with LOCK:
        inds = dict(INDICATORS["items"])
        quotes = {m["symbol"]: m for m in QUOTES["markets"] + STOCK_QUOTES["stocks"]}
        news = scored_news(NEWS["items"])
        built_at, warn = INDICATORS["updated"], INDICATORS["error"]
    fo = fo_read()
    nifty_news, _ = news_for("^NSEI", news)
    ctx = {"quotes": quotes, "news": news, "fo": fo, "macro": macro_context(quotes, nifty_news)}
    items = [score_one(symbol, kind, inds[symbol], quotes.get(symbol), ctx) for symbol, kind in SIGNAL_UNIVERSE if symbol in inds]
    items.sort(key=lambda item: -abs(item["score"]))
    return {
        "updated": int(time.time()), "indicatorsAt": built_at, "warning": warn, "fo": fo,
        "macro": ctx["macro"], "items": items, "headlines": len(news),
    }


BT_YEARS = 5
BT_HOLD = 15
BT_COST = 0.001
BT_WARMUP = 250
BT_LABELS = ("STRONG BUY", "BUY", "SELL", "STRONG SELL")
BACKTEST = {"result": None, "running": False, "done": 0, "total": len(SIGNAL_UNIVERSE), "at": 0, "error": ""}


def ist_day(ts: int) -> datetime.date:
    return datetime.datetime.fromtimestamp(ts + 19800, datetime.timezone.utc).date()


def daily_history(symbol: str) -> list[dict]:
    candles = bars_of(yahoo(symbol, "1d", BT_YEARS * 365 + 420))
    return candles if len(candles) >= 300 else hourly_rollup(symbol, "D")


def simulate_trade(s: dict, i: int, direction: int) -> tuple[int, float, str] | None:
    """Enter at the close of bar i with a 1.5 ATR stop and a 3 ATR target; exit after BT_HOLD bars otherwise.
    A bar that touches both levels counts as a stop, and gaps through a level fill at the open."""
    entry, risk = s["c"][i], 1.5 * s["atr"][i]
    stop, target = entry - direction * risk, entry + direction * 2 * risk
    for j in range(i + 1, min(i + 1 + BT_HOLD, len(s["c"]))):
        o, h, l = s["o"][j], s["h"][j], s["l"][j]
        if (o <= stop) if direction > 0 else (o >= stop):
            return j, o, "stop"
        if (o >= target) if direction > 0 else (o <= target):
            return j, o, "target"
        if (l <= stop) if direction > 0 else (h >= stop):
            return j, stop, "stop"
        if (h >= target) if direction > 0 else (l <= target):
            return j, target, "target"
        if j == i + BT_HOLD:
            return j, s["c"][j], "time"
    return None


def backtest_one(symbol: str, kind: str, nifty_moves: dict) -> dict | None:
    candles = daily_history(symbol)
    n = len(candles)
    if n < BT_WARMUP + 40:
        return None
    s = indicator_series(candles)
    since = int(time.time()) - BT_YEARS * 365 * 86400
    start = max(BT_WARMUP, next((i for i, c in enumerate(candles) if c["t"] >= since), n))
    trades, fwd = [], {"all": [], "BUY": [], "SELL": []}
    busy_until = -1
    for i in range(start, n):
        if not s["atr"][i] or not s["c"][i - 1]:
            continue
        percent = (s["c"][i] / s["c"][i - 1] - 1) * 100
        nifty = nifty_moves.get(ist_day(candles[i]["t"])) if kind in INDIA_KINDS and symbol != "^NSEI" else None
        parts, _ = technical_parts(symbol, kind, s["c"][i], percent, s["v"][i], indicators_at(s, i), nifty)
        score = round(clamp(sum(p["points"] for p in parts), -100, 100))
        direction = 1 if score >= 20 else -1 if score <= -20 else 0
        if i + 10 < n:
            move = s["c"][i + 10] / s["c"][i] - 1
            fwd["all"].append(move)
            if direction:
                fwd["BUY" if direction > 0 else "SELL"].append(move)
        if not direction or i < busy_until:
            continue
        done = simulate_trade(s, i, direction)
        if not done:
            continue
        j, exit_price, why = done
        entry, risk = s["c"][i], 1.5 * s["atr"][i]
        trades.append({
            "t": candles[i]["t"], "exitT": candles[j]["t"], "label": signal_label(score), "side": "BUY" if direction > 0 else "SELL",
            "score": score, "entry": round(entry, 2), "exit": round(exit_price, 2), "why": why, "days": j - i,
            "r": round(direction * (exit_price - entry) / risk - BT_COST * entry / risk, 3),
            "pct": round((direction * (exit_price / entry - 1) - BT_COST) * 100, 2),
        })
        busy_until = j
    return {"symbol": symbol, "kind": kind, "bars": n, "from": candles[start]["t"] if start < n else None,
            "short": n - start < 500, "trades": trades, "fwd": fwd}


def trade_stats(trades: list) -> dict:
    if not trades:
        return {"trades": 0}
    rs = [t["r"] for t in trades]
    wins = [r for r in rs if r > 0]
    lost = -sum(r for r in rs if r <= 0)
    peak = run = drawdown = 0.0
    for t in sorted(trades, key=lambda t: t["exitT"]):
        run += t["r"]
        peak = max(peak, run)
        drawdown = max(drawdown, peak - run)
    return {
        "trades": len(rs), "winRate": round(len(wins) / len(rs), 4), "avgR": round(sum(rs) / len(rs), 3),
        "totalR": round(sum(rs), 1), "profitFactor": round(sum(wins) / lost, 2) if lost else None,
        "maxDrawdownR": round(drawdown, 1), "avgDays": round(sum(t["days"] for t in trades) / len(trades), 1),
        "avgPct": round(sum(t["pct"] for t in trades) / len(trades), 2),
        "exits": {k: round(sum(1 for t in trades if t["why"] == k) / len(trades), 3) for k in ("target", "stop", "time")},
    }


def forward_edge(runs: list) -> dict:
    """How much better the 10-day move was after a signal than on an average day of the same instrument."""
    out = {}
    for side in ("BUY", "SELL"):
        count = excess = 0.0
        for r in runs:
            base, picked = r["fwd"]["all"], r["fwd"][side]
            if base and picked:
                mean = sum(base) / len(base)
                excess += sum(m - mean for m in picked) * (1 if side == "BUY" else -1)
                count += len(picked)
        out[side] = {"signals": int(count), "edgePct": round(excess / count * 100, 2) if count else None}
    return out


def equity_curve(trades: list, points: int = 300) -> list:
    run, curve = 0.0, []
    for t in sorted(trades, key=lambda t: t["exitT"]):
        run += t["r"]
        curve.append([t["exitT"], round(run, 2)])
    sampled = curve[::max(1, len(curve) // points)]
    if curve and sampled[-1] is not curve[-1]:
        sampled.append(curve[-1])
    return sampled


def summarize_backtest(runs: list) -> dict:
    trades = [dict(t, symbol=r["symbol"], kind=r["kind"]) for r in runs for t in r["trades"]]
    years = sorted({ist_day(t["exitT"]).year for t in trades})
    return {
        "generated": int(time.time()), "years": BT_YEARS, "hold": BT_HOLD, "cost": BT_COST,
        "tested": len(runs), "universe": len(SIGNAL_UNIVERSE),
        "from": min((r["from"] for r in runs if r["from"]), default=None),
        "overall": trade_stats(trades),
        "byLabel": {label: trade_stats([t for t in trades if t["label"] == label]) for label in BT_LABELS},
        "bySide": {side: trade_stats([t for t in trades if t["side"] == side]) for side in ("BUY", "SELL")},
        "byKind": {kind: trade_stats([t for t in trades if t["kind"] == kind]) for kind in sorted({r["kind"] for r in runs})},
        "byYear": {str(y): trade_stats([t for t in trades if ist_day(t["exitT"]).year == y]) for y in years},
        "edge": forward_edge(runs),
        "curves": {side: equity_curve([t for t in trades if t["side"] == side]) for side in ("BUY", "SELL")},
        "instruments": {
            r["symbol"]: {
                "name": CATALOG.get(r["symbol"], (r["kind"], r["symbol"]))[1], "kind": r["kind"], "from": r["from"], "short": r["short"],
                "stats": trade_stats(r["trades"]),
                "buy": trade_stats([t for t in r["trades"] if t["side"] == "BUY"]),
                "sell": trade_stats([t for t in r["trades"] if t["side"] == "SELL"]),
                "edge": forward_edge([r]),
                "recent": r["trades"][-15:],
            }
            for r in runs
        },
    }


def run_backtest() -> None:
    try:
        nifty = daily_history("^NSEI")
        moves = {ist_day(b["t"]): (b["c"] / a["c"] - 1) * 100 for a, b in zip(nifty, nifty[1:])}

        def one(item):
            try:
                return backtest_one(item[0], item[1], moves)
            except Exception:
                return None
            finally:
                with LOCK:
                    BACKTEST["done"] += 1

        with ThreadPoolExecutor(max_workers=4) as pool:
            runs = [r for r in pool.map(one, SIGNAL_UNIVERSE) if r]
        if not runs:
            raise RuntimeError("no price history could be downloaded")
        result = summarize_backtest(runs)
        with LOCK:
            BACKTEST.update(result=result, at=int(time.time()), error="")
    except Exception as exc:
        with LOCK:
            BACKTEST["error"] = f"Backtest failed: {exc}"
    finally:
        with LOCK:
            BACKTEST["running"] = False


def start_backtest() -> None:
    with LOCK:
        if BACKTEST["running"]:
            return
        BACKTEST.update(running=True, done=0)
    threading.Thread(target=run_backtest, daemon=True).start()


def every(seconds: int, job) -> None:
    def run():
        while True:
            try:
                job()
            except Exception as exc:
                print("background job failed:", exc)
            time.sleep(seconds)

    threading.Thread(target=run, daemon=True).start()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, value) -> None:
        payload = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        route = parsed.path
        if route == "/api/news":
            with LOCK:
                return self.send_json(NEWS)
        if route == "/api/markets":
            with LOCK:
                return self.send_json(QUOTES)
        if route == "/api/stocks":
            with LOCK:
                return self.send_json(STOCK_QUOTES)
        if route == "/api/chart":
            symbol = (query.get("symbol") or ["^NSEI"])[0]
            if symbol not in CATALOG:
                return self.send_json({"error": "unknown symbol", "candles": []})
            interval, span = fit_window((query.get("interval") or query.get("range") or ["1m"])[0], (query.get("span") or [""])[0])
            # Just under the page's reload period, so viewers of the same chart share one Yahoo request.
            ttl = 4 if interval in ("1m", "2m") else 15 if interval in INTRADAY else 60
            try:
                chart = cached(f"chart:{symbol}:{interval}:{span}", ttl, lambda: load_chart(symbol, interval, span))
            except Exception as exc:
                chart = {"error": str(exc), "candles": []}
            return self.send_json(chart)
        if route == "/api/returns":
            symbol = (query.get("symbol") or ["^NSEI"])[0]
            if symbol not in CATALOG:
                return self.send_json({"error": "unknown symbol"})
            try:
                return self.send_json(cached("returns:" + symbol, 1800, lambda: load_returns(symbol)))
            except Exception as exc:
                return self.send_json({"error": f"History unavailable: {exc}"})
        if route == "/api/signals":
            if not INDICATORS["items"]:
                return self.send_json({"warming": True, "items": []})
            try:
                return self.send_json(cached("signals", 30, build_signals))
            except Exception as exc:
                return self.send_json({"error": f"Signals unavailable: {exc}", "items": []})
        if route == "/api/backtest":
            with LOCK:
                state = {k: BACKTEST[k] for k in ("running", "done", "total", "at", "error", "result")}
            if not state["running"] and (not state["result"] or time.time() - state["at"] > 12 * 3600):
                start_backtest()
                state["running"], state["done"] = True, 0
            return self.send_json(state)
        if route == "/api/ibja":
            try:
                return self.send_json(cached("ibja", 1800, load_ibja))
            except Exception as exc:
                return self.send_json({"error": f"IBJA rates unavailable: {exc}"})
        if route == "/api/chain":
            try:
                return self.send_json(load_chain((query.get("expiry") or [None])[0]))
            except Exception as exc:
                return self.send_json({"error": f"NSE option chain unavailable: {exc}"})
        if route == "/api/fii":
            try:
                return self.send_json({"rows": cached("nse:fii", 600, lambda: nse_get("/api/fiidiiTradeReact"))})
            except Exception as exc:
                return self.send_json({"rows": [], "error": f"NSE FII data unavailable: {exc}"})
        if route == "/api/bullion":
            try:
                return self.send_json(cached("bullion", 600, load_bullion))
            except Exception as exc:
                return self.send_json({"error": f"City gold rates unavailable: {exc}"})
        if route == "/api/bullion/city":
            slug = (query.get("slug") or [""])[0]
            if not re.fullmatch(r"[a-z]+(?:-[a-z]+)*", slug) or slug in ABROAD:
                return self.send_json({"error": "unknown city"})
            try:
                return self.send_json(cached("city:" + slug, 1800, lambda: load_city(slug)))
            except Exception as exc:
                return self.send_json({"error": f"Rates for this city are unavailable: {exc}"})
        if route not in PAGES:
            return self.send_error(404)
        return super().do_GET()

    def do_HEAD(self):
        if urlparse(self.path).path not in PAGES:
            return self.send_error(404)
        return super().do_HEAD()

    def log_message(self, fmt, *args):
        if args and "/api/" in str(args[0]):
            return
        super().log_message(fmt, *args)


if __name__ == "__main__":
    every(30, sweep_news)
    every(20, lambda: refresh(MARKETS, QUOTES, "markets"))
    every(45, lambda: refresh(STOCK_ROWS, STOCK_QUOTES, "stocks"))
    every(900, refresh_indicators)
    warmup = threading.Timer(90, start_backtest)
    warmup.daemon = True
    warmup.start()
    print(f"Arthlane  http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
