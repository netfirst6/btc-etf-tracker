"""
BTC ETF Flow Scraper → flows.csv
"""

import csv
import datetime
import os
import requests
from bs4 import BeautifulSoup

FARSIDE_URL = "https://farside.co.uk/bitcoin-etf-flow-all-data-table/"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "flows.csv")
MAX_ROWS    = 500

def fetch_flows():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://farside.co.uk/",
    }
    resp = requests.get(FARSIDE_URL, headers=headers, timeout=30)
    resp.raise_for_status()

    soup  = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")
    if not table:
        raise ValueError("Could not find ETF flow table on Farside page")

    rows   = table.find_all("tr")
    header = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]

    try:
        date_idx  = next(i for i, h in enumerate(header) if "date"  in h.lower())
        total_idx = next(i for i, h in enumerate(header) if "total" in h.lower())
    except StopIteration:
        date_idx, total_idx = 0, len(header) - 1

    seen = {}
    for row in rows[1:]:
        cells     = row.find_all(["td", "th"])
        if len(cells) <= total_idx:
            continue

        raw_date  = cells[date_idx].get_text(strip=True)
        raw_total = (cells[total_idx].get_text(strip=True)
                     .replace(",", "")
                     .replace("\u2212", "-")
                     .replace("\u2014", "")
                     .strip())

        date_str = None
        for fmt in ("%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                date_str = datetime.datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
        if not date_str:
            continue

        try:
            net_flow = float(raw_total) if raw_total not in ("", "-") else None
        except ValueError:
            net_flow = None

        if net_flow is not None:
            seen[date_str] = net_flow

    records = [{"date": d, "NetFlow_MUSD": v} for d, v in sorted(seen.items())]
    return records[-MAX_ROWS:]


def write_csv(records):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "NetFlow_MUSD"])
        writer.writeheader()
        for r in reversed(records):
            writer.writerow(r)
    print(f"✅  Wrote {len(records)} rows to {OUTPUT_PATH}")
    print(f"    Latest: {records[-1]['date']}  |  {records[-1]['NetFlow_MUSD']}M USD")


if __name__ == "__main__":
    print("Fetching BTC ETF flows from Farside Investors...")
    records = fetch_flows()
    print(f"  {len(records)} trading days fetched")
    write_csv(records)
