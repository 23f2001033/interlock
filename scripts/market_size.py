"""Bottom-up market sizing for the business plan, from Crustdata's job-postings index.

Question: how many companies are hiring engineers who work with AI coding agents? Those teams are the
ones that will run several agents on one codebase, which is Interlock's buyer.
Count-only queries (limit 0) return no rows, so they cost (almost) no credits.

Usage: uv run python scripts/market_size.py  ->  business-plan/market_crustdata.json
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
URL = "https://api.crustdata.com/job/search"
HEADERS = {
    "authorization": f"Bearer {os.environ['CRUSTDATA_API_KEY']}",
    "content-type": "application/json",
    "x-api-version": "2025-11-01",
}
SINCE = "2026-01-01"
PHRASES = ["claude code", "coding agents", "ai coding assistant", "github copilot", "cursor ai", "codex cli"]


def search(body: dict) -> dict:
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()[:500]}


def phrase_filter(phrases: list[str]) -> dict:
    return {"op": "and", "conditions": [
        {"field": "metadata.date_added", "type": "=>", "value": SINCE},
        {"op": "or", "conditions": [{"field": "content.description", "type": "[.]", "value": p} for p in phrases]},
    ]}


def count(phrases: list[str]) -> dict:
    res = search({"filters": phrase_filter(phrases), "limit": 0, "aggregations": [{"type": "count"}]})
    return {"total_count": res.get("total_count"), "aggregations": res.get("aggregations"), "error": res.get("error"),
            "detail": res.get("detail")}


def distinct_companies(phrases: list[str], size: int = 1000) -> dict:
    res = search({"filters": phrase_filter(phrases), "limit": 0,
                  "aggregations": [{"type": "group_by", "field": "company.basic_info.company_id", "size": size}]})
    aggs = res.get("aggregations") or []
    buckets = aggs[0].get("buckets") if aggs and isinstance(aggs[0], dict) else None
    return {"distinct_companies_at_least": len(buckets) if buckets is not None else None,
            "capped_at": size, "error": res.get("error"), "detail": res.get("detail"),
            "raw_shape": list(aggs[0].keys()) if aggs and isinstance(aggs[0], dict) else None}


if __name__ == "__main__":
    out = {"source": "Crustdata /job/search (x-api-version 2025-11-01)", "since": SINCE,
           "per_phrase": {p: count([p]) for p in PHRASES}}
    out["any_phrase"] = count(PHRASES)
    out["any_phrase_companies"] = distinct_companies(PHRASES)
    path = Path(__file__).resolve().parents[1] / "business-plan" / "market_crustdata.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2)[:3000])
