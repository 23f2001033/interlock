"""Render share cards (PNG) for build-in-public posts from the real evidence files.

Usage: uv run --with pillow python scripts/make_cards.py  ->  docs/media/*.png
"""

import json
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "media"
OUT.mkdir(parents=True, exist_ok=True)
FONTS = Path("C:/Windows/Fonts")
MONO = str(FONTS / "consola.ttf")
SANS = str(FONTS / "segoeui.ttf")
SANS_B = str(FONTS / "segoeuib.ttf")

BG, PANEL, FG, MUTED = (13, 17, 23), (22, 27, 34), (230, 237, 243), (139, 148, 158)
RED, GREEN, YELLOW, BLUE = (248, 81, 73), (63, 185, 80), (210, 153, 34), (88, 166, 255)
W = 1600


def font(path: str, size: int):
    return ImageFont.truetype(path, size)


def card(title: str, subtitle: str, body_height: int):
    img = Image.new("RGB", (W, 200 + body_height + 90), BG)
    d = ImageDraw.Draw(img)
    d.text((70, 55), title, font=font(SANS_B, 52), fill=FG)
    d.text((70, 125), subtitle, font=font(SANS, 30), fill=MUTED)
    d.rounded_rectangle((60, 190, W - 60, 190 + body_height), radius=18, fill=PANEL)
    d.text((70, 190 + body_height + 28), "Interlock · #neatHack · github.com/23f2001033/interlock",
           font=font(SANS, 26), fill=MUTED)
    return img, d


def constants():
    rows = [("SHIPPING_FLAT = 500", "# cents   (agent #1)", GREEN),
            ("FREE_SHIPPING_THRESHOLD = 5000", "# cents   (agent #1)", GREEN),
            ("SMALL_ORDER_FEE = 1.50", "# dollars (agent #2)", RED),
            ("SMALL_ORDER_THRESHOLD = 15.00", "# dollars (agent #2)", RED)]
    img, d = card("Git merged this. No conflict. No failing test.",
                  "Two Claude agents, two green branches. Now every order is \"over $15\" and the fee never applies.",
                  400)
    y = 240
    for code, note, color in rows:
        d.text((110, y), code, font=font(MONO, 44), fill=FG)
        d.text((900, y), note, font=font(MONO, 40), fill=color)
        y += 80
    img.save(OUT / "silent_bug.png")


def scoreboard():
    rows = [("v1  plain merge queue", "1.00", "0.40", "3 / 6", "$0.11"),
            ("v2.0  Interlock", "1.00", "0.67", "1 / 6", "$0.52"),
            ("v2.1  + entire-graph pre-check", "1.00", "0.67", "1 / 6", "$0.40"),
            ("v2.2  + second-opinion check", "1.00", "1.00", "0 / 6", "$0.55"),
            ("v2.3  + Haiku-first ladder", "1.00", "1.00", "0 / 6", "$0.38")]
    img, d = card("Merge queue vs Interlock, on real agent branches",
                  "8 branch pairs by independent Claude agents · 2 truly interfere · 4 improvement loops via neatlogs",
                  520)
    cols = [110, 740, 930, 1140, 1390]
    hdr = ["version", "recall", "precision", "false alarms", "cost"]
    for x, h in zip(cols, hdr):
        d.text((x, 230), h, font=font(SANS_B, 32), fill=MUTED)
    y = 300
    for i, r in enumerate(rows):
        for j, (x, v) in enumerate(zip(cols, r)):
            color = FG
            if j == 2:
                color = GREEN if v == "1.00" else (RED if v == "0.40" else YELLOW)
            if j == 3:
                color = GREEN if v.startswith("0") else RED
            d.text((x, y), v, font=font(SANS_B if i == 4 else SANS, 36), fill=color)
        y += 82
    img.save(OUT / "scoreboard.png")


def clean(text: str) -> str:
    return " ".join(re.sub(r"[*`]", "", text).split())


def sentences(text: str, upto: str | None = None, max_n: int = 4) -> str:
    parts = re.split(r"(?<=[.!?])\s+", clean(text))
    out = []
    for p in parts:
        out.append(p)
        if (upto and upto in p) or len(out) >= max_n:
            break
    return " ".join(out)


def agent_said_no():
    st = json.loads((ROOT / "evidence/runs/20261011-031122/state.json").read_text(encoding="utf-8"))
    reply = st["rounds"][1]["reply"]
    quote = sentences(reply, upto="contradict", max_n=6)
    lines = textwrap.wrap(quote, 66)[:10]
    img, d = card("The AI agent said no, and it was right",
                  "Interlock asked agent #1 to make an acceptance test pass. The test contradicted the agent's own task.",
                  80 + 54 * len(lines))
    y = 230
    for ln in lines:
        d.text((110, y), ln, font=font(MONO, 34), fill=FG)
        y += 54
    img.save(OUT / "agent_said_no.png")


def drift_timeline():
    st = json.loads((ROOT / "evidence/runs/land-20261011-031600/state.json").read_text(encoding="utf-8"))
    color = {"landed": GREEN, "drift": YELLOW, "retry": YELLOW, "coordinate": BLUE, "finish": GREEN, "prove": FG, "plan": FG}
    lines = []
    for e in st["events"]:
        info = {k: v for k, v in e.items() if k not in ("at", "event")}
        if e["event"] == "drift":
            dep = info['why'][info['affected'][0]]['new_code_depends_on'][0]
            text = f"teammate pushed: only {', '.join(info['affected'])} affected (uses {dep})"
        elif e["event"] == "plan":
            text = " -> ".join(info["order"])
        elif e["event"] == "prove":
            hold = "both intents hold" if set(info["verdicts"]) == {"holds"} else "interference"
            text = f"{info['branch']}: {hold}" + (f" + {len(info['conflicts'])} file conflict" if info["conflicts"] else "")
        elif e["event"] == "coordinate":
            text = f"{info['branch']}: own session resumed -> {info['status']} (round {info['rounds']})"
        elif e["event"] == "retry":
            text = "compare-and-swap failed: target moved"
        elif e["event"] == "landed":
            text = f"{info['branch']} landed ({info['detail']})"
        elif e["event"] == "finish":
            text = f"goal {info['status'].upper()} · final suite {info['final_suite']['passed']}/{info['final_suite']['passed'] + len(info['final_suite']['failed'])}"
        else:
            text = json.dumps(info)[:80]
        lines.append((e["at"], e["event"], text, color.get(e["event"], FG)))
    img, d = card("Landing 3 agent branches while a teammate pushes",
                  "interlock land agent/issue-4 agent/issue-5 agent/issue-1 · no human in the loop · 2.5 minutes",
                  60 + 64 * len(lines))
    y = 225
    for at, ev, text, c in lines:
        d.text((100, y), at, font=font(MONO, 30), fill=MUTED)
        d.text((280, y), ev, font=font(MONO, 30), fill=c)
        d.text((490, y), text[:70], font=font(SANS, 30), fill=FG)
        y += 64
    img.save(OUT / "drift_timeline.png")


def agents_talk():
    st = json.loads((ROOT / "evidence/runs/20261011-013837/state.json").read_text(encoding="utf-8"))
    r = st["rounds"][0]
    msg = textwrap.wrap(sentences(r["message"].split("What `")[0], max_n=3), 70)[:5]
    reply = textwrap.wrap(sentences(r["reply"], max_n=3), 70)[:6]
    img, d = card("We made the agents talk to each other",
                  "Interlock -> agent #2's own Claude Code session (found via Entire) · resolved in 1 round, re-verified",
                  140 + 46 * (len(msg) + len(reply)))
    y = 225
    d.text((100, y), "Interlock:", font=font(SANS_B, 32), fill=BLUE); y += 52
    for ln in msg:
        d.text((120, y), ln[:80], font=font(MONO, 27), fill=FG); y += 44
    y += 20
    d.text((100, y), "Agent #2:", font=font(SANS_B, 32), fill=GREEN); y += 52
    for ln in reply:
        d.text((120, y), ln, font=font(MONO, 27), fill=FG); y += 44
    img.save(OUT / "agents_talk.png")


if __name__ == "__main__":
    for f in (constants, scoreboard, agent_said_no, drift_timeline, agents_talk):
        f()
    print("\n".join(str(p) for p in sorted(OUT.glob("*.png"))))
