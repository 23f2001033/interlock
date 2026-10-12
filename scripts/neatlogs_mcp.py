"""Query Interlock's own traces back out of neatlogs through the neatlogs MCP server.

This is how we (and our coding agents) find the code behind a failure: search traces, then pull one
trace's span tree with code locations. Output is saved under evidence/neatlogs/ (no keys included).

Usage: uv run python scripts/neatlogs_mcp.py [tool] [json-args]
       uv run python scripts/neatlogs_mcp.py            # default evidence pull
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
URL = "https://ingest.neatlogs.com/mcp"
KEY = os.environ.get("NEATLOGS_API_KEY") or os.environ["NEATLOG_API_KEY"]


class MCP:
    def __init__(self):
        self.session = None
        self.next_id = 0
        self.call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "interlock", "version": "0.1"}})
        self.notify("notifications/initialized")

    def _post(self, payload: dict) -> tuple[dict | None, dict]:
        headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["mcp-session-id"] = self.session
        req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=120) as r:
            self.session = r.headers.get("mcp-session-id") or self.session
            body = r.read().decode("utf-8", errors="replace")
        for line in body.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip()), dict(r.headers)
        return (json.loads(body) if body.strip().startswith("{") else None), dict(r.headers)

    def call(self, method: str, params: dict | None = None) -> dict:
        self.next_id += 1
        msg, _ = self._post({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params or {}})
        return msg or {}

    def notify(self, method: str) -> None:
        try:
            self._post({"jsonrpc": "2.0", "method": method})
        except Exception:
            pass

    def tool(self, name: str, args: dict | None = None):
        res = self.call("tools/call", {"name": name, "arguments": args or {}}).get("result", {})
        texts = [c.get("text", "") for c in res.get("content", []) if c.get("type") == "text"]
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except json.JSONDecodeError:
            return joined


if __name__ == "__main__":
    mcp = MCP()
    if len(sys.argv) > 1:
        print(json.dumps(mcp.tool(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}), indent=2)[:20000])
        sys.exit(0)
    out = Path(__file__).resolve().parents[1] / "evidence" / "neatlogs"
    out.mkdir(parents=True, exist_ok=True)
    tools = mcp.call("tools/list").get("result", {}).get("tools", [])
    pulls = {"tools": [t["name"] for t in tools], "whoami": mcp.tool("whoami")}
    for q in ["interlock.land", "agent_message", "arbitrate.reexpress", "interlock.eval", "cleared_by_graph"]:
        pulls[f"search:{q}"] = mcp.tool("search_traces", {"query": q})
    (out / "mcp_pull.json").write_text(json.dumps(pulls, indent=2), encoding="utf-8")
    print(json.dumps(pulls, indent=2)[:6000])
