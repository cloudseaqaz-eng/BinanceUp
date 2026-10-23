"""Public Binance archives; verified converted checkpoints and optional ZIP retention."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlsplit
import json
import time
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
import pandas as pd
from .config import Config, board_symbol, json_write, utc
from .storage import write_frame, receipt, verify_receipts, prune_archives

ARCHIVE = "https://data.binance.vision/data/"
BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
RAW_COLS = ["open", "high", "low", "close", "volume", "quote", "trades", "taker_quote"]


def get(url, retries=3):
    # urllib sends the request target as ASCII. Archive paths can contain actual
    # Chinese symbols: encode their UTF-8 bytes, preserving existing escapes and
    # the query already produced by urlencode (including S3 continuation tokens).
    parts = urlsplit(url)
    url = parts._replace(path=quote(parts.path, safe="/%")).geturl()
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers={"User-Agent": "BinanceUp-research/1.0"}), timeout=40) as r:
                return r.read()
        except HTTPError as e:
            if e.code == 404:
                return None
            if e.code not in (408, 429, 500, 502, 503, 504):
                raise
        except (TimeoutError, OSError):
            if attempt == retries - 1:
                raise
        time.sleep(1 + 2 * attempt)
    raise RuntimeError("下载重试失败: " + url)


def discover():
    """Archive prefixes include delisted pairs; never replace with today's exchangeInfo."""
    symbols, token = [], None
    while True:
        params = {"list-type": "2", "prefix": "data/spot/monthly/klines/", "delimiter": "/", "max-keys": 1000}
        if token:
            params["continuation-token"] = token
        body = get(BUCKET + "?" + urlencode(params))
        root = ET.fromstring(body)
        ns = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
        for item in root.findall("s:CommonPrefixes/s:Prefix", ns):
            symbol = item.text.rstrip("/").rsplit("/", 1)[-1]
            if board_symbol(symbol):
                symbols.append(symbol)
        token = root.findtext("s:NextContinuationToken", namespaces=ns)
        if not token:
            break
    if not symbols:
        raise RuntimeError("归档目录没有返回币种；不能据此建立空榜单")
    return sorted(set(symbols))


def zip_frame(blob, header=None):
    with zipfile.ZipFile(BytesIO(blob)) as z:
        name = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(name) as f:
            return pd.read_csv(f, header=header)


def parse_klines(blob):
    raw = zip_frame(blob)
    numeric = pd.to_numeric(raw.iloc[:, 0], errors="coerce")
    raw = raw.loc[numeric.notna()]
    ts = numeric[numeric.notna()].astype("int64")
    # Spot from Jan 2025 uses microseconds. Futures/older spot use milliseconds.
    ms = ts.where(ts < 10**14, ts // 1000)
    out = pd.DataFrame({col: pd.to_numeric(raw.iloc[:, idx], errors="coerce").to_numpy()
                        for col, idx in zip(RAW_COLS, [1, 2, 3, 4, 5, 7, 8, 10])},
                       index=pd.DatetimeIndex(pd.to_datetime(ms.to_numpy(), unit="ms", utc=True) + pd.Timedelta(minutes=1), name="time"))
    valid = (out[["open", "high", "low", "close"]] > 0).all(axis=1)
    valid &= (out[["volume", "quote", "trades", "taker_quote"]] >= 0).all(axis=1)
    valid &= out.taker_quote <= out.quote * 1.000001
    return out.loc[valid].sort_index().loc[lambda x: ~x.index.duplicated(keep="last")]


def cached_zip(cfg, relative, log):
    path = cfg.path / "archive" / relative
    if path.exists():
        blob = path.read_bytes()
        status = "cached"
    else:
        blob = get(ARCHIVE + relative)
        if blob is None:
            log.append({"path": relative, "status": "404"})
            return None
        # Verify ZIP integrity before accepting the cached object.
        with zipfile.ZipFile(BytesIO(blob)) as z:
            if z.testzip() is not None:
                raise ValueError("归档 ZIP 校验失败: " + relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        tmp.write_bytes(blob)
        tmp.replace(path)
        status = "downloaded"
    log.append({"path": relative, "status": status, "bytes": len(blob), "sha256": sha256(blob).hexdigest()})
    return blob


def fetch_spot(cfg, symbol, log):
    frames = []
    start, end = cfg.warm_start, utc(cfg.end)
    months = pd.period_range(start.tz_localize(None), (end-pd.Timedelta(microseconds=1)).tz_localize(None), freq="M")
    for month in months:
        relative = f"spot/monthly/klines/{symbol}/1m/{symbol}-1m-{month}.zip"
        blob = cached_zip(cfg, relative, log)
        if blob:
            frames.append(parse_klines(blob))
            continue
        # Missing monthly archives (e.g. current month) fall back to daily archives.
        first = max(start.floor("D"), month.start_time.tz_localize("UTC"))
        last = min(end, (month+1).start_time.tz_localize("UTC"))
        for day in pd.date_range(first, last, freq="D", inclusive="left"):
            relative = f"spot/daily/klines/{symbol}/1m/{symbol}-1m-{day:%Y-%m-%d}.zip"
            blob = cached_zip(cfg, relative, log)
            if blob:
                frames.append(parse_klines(blob))
    if not frames:
        return pd.DataFrame(columns=RAW_COLS)
    result = pd.concat(frames).sort_index()
    result = result.loc[~result.index.duplicated(keep="last")]
    return result.loc[(result.index > start) & (result.index <= end)]


def fetch_oi(cfg, symbol, log):
    frames = []
    for day in pd.date_range(cfg.warm_start.floor("D"), utc(cfg.end).ceil("D"), freq="D", inclusive="left"):
        rel = f"futures/um/daily/metrics/{symbol}/{symbol}-metrics-{day:%Y-%m-%d}.zip"
        blob = cached_zip(cfg, rel, log)
        if blob:
            df = zip_frame(blob, header=0)
            t = pd.to_datetime(df["create_time"], utc=True) + pd.Timedelta(minutes=cfg.oi_lag_minutes)
            frames.append(pd.DataFrame({"time": t, "oi": pd.to_numeric(df["sum_open_interest"], errors="coerce"),
                                        "oi_usdt": pd.to_numeric(df["sum_open_interest_value"], errors="coerce")}))
    if not frames:
        return pd.DataFrame(columns=["oi", "oi_usdt"], index=pd.DatetimeIndex([], tz="UTC", name="time"))
    return pd.concat(frames).set_index("time").sort_index().loc[lambda x: ~x.index.duplicated(keep="last")]


def fetch_funding(cfg, symbol, log):
    frames = []
    months = pd.period_range(cfg.warm_start.tz_localize(None), utc(cfg.end).tz_localize(None), freq="M")
    for month in months:
        rel = f"futures/um/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip"
        blob = cached_zip(cfg, rel, log)
        if blob:
            df = zip_frame(blob, header=0)
            df.columns = [str(c).lower().replace("_", "") for c in df.columns]
            rate = pd.to_numeric(df["lastfundingrate"], errors="coerce") * 8 / pd.to_numeric(df["fundingintervalhours"], errors="coerce")
            frames.append(pd.DataFrame({"time": pd.to_datetime(df["calctime"], unit="ms", utc=True), "funding8h": rate}))
    if not frames:
        return pd.DataFrame(columns=["funding8h"], index=pd.DatetimeIndex([], tz="UTC", name="time"))
    return pd.concat(frames).set_index("time").sort_index().loc[lambda x: ~x.index.duplicated(keep="last")]


def download_request(cfg, funding=True):
    return {"warm_start": cfg.warm_start.isoformat(), "end": utc(cfg.end).isoformat(),
            "oi_mode": cfg.oi_mode, "oi_lag_minutes": cfg.oi_lag_minutes, "funding": funding}


def download(cfg, workers=3, funding=True, refresh=False):
    cfg.save()
    (cfg.path / "raw").mkdir(parents=True, exist_ok=True)
    (cfg.path / "manifests").mkdir(exist_ok=True)
    symbols = sorted(set(cfg.symbols) | {"BTCUSDT"})
    def one(symbol):
        manifest_path = cfg.path / "manifests" / f"{symbol}.json"
        request = download_request(cfg, funding)
        previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        if manifest_path.exists() and not refresh:
            if (not previous.get("error") and previous.get("request") == request
                    and verify_receipts(cfg, previous.get("raw_receipts", []))):
                if not cfg.keep_archives:
                    prune_archives(cfg, previous)
                print(symbol, "已验证转换文件，复用本地数据", flush=True)
                return previous
        log = []
        try:
            spot = fetch_spot(cfg, symbol, log)
            if (not previous.get("error") and previous.get("request") == request
                    and len(spot) < previous.get("spot_rows", 0)):
                raise RuntimeError("重新请求的归档行数少于已验证版本，保留现有行情；请检查归档是否暂时缺失")
            if len(spot):
                write_frame(spot, cfg.path / "raw" / f"{symbol}.parquet")
            oi = fetch_oi(cfg, symbol, log) if len(spot) and cfg.oi_mode != "off" else pd.DataFrame()
            if (not previous.get("error") and previous.get("request") == request
                    and len(oi) < previous.get("oi_rows", 0)):
                raise RuntimeError("OI归档少于已验证版本，保留现有OI；请检查上游覆盖")
            if len(oi):
                write_frame(oi, cfg.path / "raw" / f"{symbol}.oi.parquet")
            f = fetch_funding(cfg, symbol, log) if len(oi) and funding else pd.DataFrame()
            if (not previous.get("error") and previous.get("request") == request
                    and len(f) < previous.get("funding_rows", 0)):
                raise RuntimeError("资金费率归档少于已验证版本，保留现有资金费率；请检查上游覆盖")
            if len(f):
                write_frame(f, cfg.path / "raw" / f"{symbol}.funding.parquet")
            records = []
            for suffix, data in (("", spot), (".oi", oi), (".funding", f)):
                if len(data):
                    records.append(receipt(cfg.path/"raw"/(symbol+suffix+".parquet")))
            result = {"symbol": symbol, "spot_rows": len(spot), "oi_rows": len(oi), "funding_rows": len(f),
                      "first": str(spot.index.min()) if len(spot) else None, "last": str(spot.index.max()) if len(spot) else None,
                      "files": log, "error": None, "request": request, "raw_receipts": records}
            # Publish a verified recovery checkpoint BEFORE removing ZIPs.
            json_write(manifest_path, result)
            if records and not cfg.keep_archives:
                prune_archives(cfg, result)
        except Exception as e:
            result = {"symbol": symbol, "error": str(e), "files": log}
            if previous.get("raw_receipts"):
                # Keep the last verified checkpoint, including its minimum row
                # counts. A failed refresh must not erase that safety baseline.
                json_write(manifest_path, {**previous, "last_attempt_error": str(e)})
                return result
        json_write(manifest_path, result)
        return result
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(one, s) for s in symbols]):
            r = future.result()
            results.append(r)
            print(f"{r['symbol']}: " + (r['error'] or f"spot={r['spot_rows']}, OI={r['oi_rows']}"), flush=True)
    json_write(cfg.path / "download_summary.json", results)
    if any(r["error"] for r in results):
        raise RuntimeError("部分下载失败。缓存已保存；处理上述错误后重复 download，不应把下载失败当作没有交易。")
    return results


def read_raw(cfg, symbol):
    path = cfg.path / "raw" / f"{symbol}.parquet"
    if not path.exists():
        return pd.DataFrame(columns=RAW_COLS, index=pd.DatetimeIndex([], tz="UTC", name="time"))
    df = pd.read_parquet(path, page_checksum_verification=True)
    grid = pd.date_range(cfg.warm_start + pd.Timedelta(minutes=1), utc(cfg.end), freq="min", name="time")
    return df.reindex(grid)  # Unknown minutes remain NaN; never fabricate a zero-volume bar.
