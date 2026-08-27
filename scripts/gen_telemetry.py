#!/usr/bin/env python3
"""
Generate assets/telemetry.svg and assets/telemetry-narrow.svg from live, public
GitHub data.

Run locally with `python scripts/gen_telemetry.py`, or on a schedule via
.github/workflows/telemetry.yml. Replaces third-party stat-card services, which
are rate-limited and go down (github-readme-stats was returning
DEPLOYMENT_PAUSED when this profile was built).

Two files, one fetch: an 880px panel for desktop and a 380px panel recomposed
for a phone column, which the README selects between with a <picture> media
query. See LAYOUTS below and the header of gen_assets.py for the reasoning.

Data sources, both public — no secrets and no extra token scopes required:
  * https://github.com/users/<user>/contributions   (contribution calendar)
  * https://api.github.com/users/<user>/repos       (repos + per-repo languages)

GITHUB_TOKEN is used only if present, purely to raise the REST rate limit.

Failure policy: if any fetch or parse step fails, the script exits 0 WITHOUT
touching the existing SVGs. A stale panel is fine; a broken image in the README
is not.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from collections import Counter, OrderedDict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import svgkit as k  # noqa: E402

USER = os.environ.get("PROFILE_USER", "DushyantBhardwaj2")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

UA = "profile-telemetry-generator (+https://github.com/%s)" % USER

# Two canvases, one dataset. GitHub caps README images at the content column
# width, so a single 880px panel is really a fixed type scale: at a 311px phone
# column 9.5px labels land at 3.4 CSS px. The README selects between these with
# a <picture> media query and `width="100%"`, so the chosen panel always fills
# the column — see the header of gen_assets.py for the full breakpoint maths.
#
# Every size below is a source px that must clear ~10 CSS px after its band's
# worst-case scale:
#   wide   served above 690px viewport -> column 659..880 -> scale 0.75..1.00
#   narrow served at or below 690px    -> column 288..658 -> scale 0.76..1.73
LAYOUTS = {
    "telemetry": dict(
        w=880, pad=26, narrow=False,
        stat_cols=4, stat_size=24, stat_label=13.5,
        meta_size=13.5, bar_h=88, bar_gap=9, month_size=13.5, callout_size=13.5,
        legend_cols=4, legend_size=13.5, legend_row=21, grid_step=34,
        header_right="SELF-GENERATED · REFRESHED NIGHTLY",
    ),
    "telemetry-narrow": dict(
        w=380, pad=16, narrow=True,
        stat_cols=2, stat_size=26, stat_label=12.5,
        meta_size=12, bar_h=68, bar_gap=4, month_size=12, callout_size=12,
        legend_cols=1, legend_size=12, legend_row=21, grid_step=28,
        header_right="REFRESHED NIGHTLY",
    ),
}

# Languages excluded from the volume chart: markup, styling and config noise
# that would otherwise crowd out the languages actually being written.
LANG_SKIP = {"HTML", "CSS", "SCSS", "Dockerfile", "Shell", "PowerShell", "Batchfile",
             "Makefile", "CMake", "Procfile", "Roff", "Nix"}

# Ordered ramp: bright cyan for the dominant language, cooling through blue to
# violet for the tail, so the bar reads as one gradient rather than a pie chart.
LANG_FILL = ["#22D3EE", "#38BDF8", "#60A5FA", "#818CF8", "#A78BFA", "#C4B5FD", "#3D4654"]


def fetch(url, accept=None):
    """HTTP GET with an optional on-disk cache.

    Set TELEMETRY_CACHE_DIR to develop the layout offline without spending the
    unauthenticated GitHub rate limit (60 req/hr). CI leaves it unset so the
    scheduled run always reads live data.
    """
    cache_dir = os.environ.get("TELEMETRY_CACHE_DIR")
    cache_path = None
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        key = re.sub(r"[^A-Za-z0-9]+", "_", url)[-120:]
        cache_path = os.path.join(cache_dir, key + ".cache")
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as fh:
                return fh.read()

    headers = {"User-Agent": UA}
    if accept:
        headers["Accept"] = accept
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and "api.github.com" in url:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = resp.read().decode("utf-8", "replace")

    if cache_path:
        with open(cache_path, "w", encoding="utf-8") as fh:
            fh.write(payload)
    return payload


def fetch_json(url):
    return json.loads(fetch(url, accept="application/vnd.github+json"))


# ------------------------------------------------------------ contributions ---
def get_contributions():
    """Return (monthly totals, grand total, active days) for the last year.

    Monthly aggregation is deliberate. A day-level heatmap of any individual is
    mostly empty cells, which says more about calendar habits than about
    engineering; month totals show the actual shape of when work happened.
    """
    html = fetch("https://github.com/users/%s/contributions" % USER)

    tips = dict(re.findall(r'<tool-tip[^>]*\sfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', html))

    days = []
    for td in re.findall(r"<td\b[^>]*class=\"[^\"]*ContributionCalendar-day[^\"]*\"[^>]*>", html):
        d = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', td)
        if not d:
            continue
        ident = re.search(r'id="([^"]+)"', td)
        count = 0
        if ident and ident.group(1) in tips:
            m = re.match(r"\s*(No|[\d,]+)\s+contribution", tips[ident.group(1)])
            if m:
                count = 0 if m.group(1) == "No" else int(m.group(1).replace(",", ""))
        days.append((datetime.strptime(d.group(1), "%Y-%m-%d").date(), count))

    if len(days) < 300:
        raise RuntimeError("contribution calendar looked wrong: %d cells parsed" % len(days))

    days.sort(key=lambda t: t[0])
    total = sum(c for _, c in days)
    active = sum(1 for _, c in days if c > 0)

    months = OrderedDict()
    for d, c in days:
        months.setdefault(d.strftime("%Y-%m"), 0)
        months[d.strftime("%Y-%m")] += c

    # Keep the trailing 12 whole-or-partial months.
    keys = list(months)[-12:]
    return [(kk, months[kk]) for kk in keys], total, active


# ---------------------------------------------------------------- languages ---
def get_languages():
    """Aggregate code volume per language across all non-fork public repos.

    Also returns how many of those repos declare a homepage URL, which is the
    honest way to count shipped/deployed projects without hardcoding a number.

    This is the expensive step — one request per repo — so the whole aggregate is
    memoised as a single cache entry when TELEMETRY_CACHE_DIR is set.
    """
    cache_dir = os.environ.get("TELEMETRY_CACHE_DIR")
    agg_path = os.path.join(cache_dir, "langs-aggregate.json") if cache_dir else None

    if agg_path and os.path.exists(agg_path):
        with open(agg_path, encoding="utf-8") as fh:
            agg = json.load(fh)
        by_bytes = Counter(agg["bytes"])
        repo_total, deployed = agg["repoCount"], agg["deployed"]
    else:
        repos = [r for r in fetch_json(
            "https://api.github.com/users/%s/repos?per_page=100&type=owner" % USER)
            if not r.get("fork")]

        repo_total = len(repos)
        deployed = sum(1 for r in repos if (r.get("homepage") or "").startswith("http"))

        by_bytes = Counter()
        for r in repos:
            try:
                for lang, n in fetch_json(r["languages_url"]).items():
                    by_bytes[lang] += n
            except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
                continue
            time.sleep(0.1)

        if not by_bytes:
            raise RuntimeError("no language data resolved")

        if agg_path:
            with open(agg_path, "w", encoding="utf-8") as fh:
                json.dump({"bytes": dict(by_bytes), "repoCount": repo_total,
                           "deployed": deployed}, fh)

    coded = Counter({lang: n for lang, n in by_bytes.items() if lang not in LANG_SKIP})
    total = sum(coded.values())
    top = coded.most_common(6)
    shown = sum(n for _, n in top)
    rows = [(lang, 100.0 * n / total) for lang, n in top]
    if total - shown > 0:
        rows.append(("Other", 100.0 * (total - shown) / total))
    return rows, repo_total, len(coded), deployed


# ------------------------------------------------------------------ drawing ---
def draw_month_bars(x, y, w, months, L):
    """Twelve monthly contribution bars — shows the shape of the year."""
    body = []
    h = L["bar_h"]
    gap = L["bar_gap"]
    n = len(months)
    bw = (w - gap * (n - 1)) / float(n)
    peak = max(1, max(v for _, v in months))
    top3 = sorted({v for _, v in months}, reverse=True)[:3]

    body.append(k.line(x, y + h, x + w, y + h, stroke=k.BORDER_HI))

    for i, (key, val) in enumerate(months):
        bx = x + i * (bw + gap)
        bh = (h - 6) * val / float(peak)
        # Empty months still get a visible floor tick so the axis reads clearly.
        if bh < 2:
            body.append(k.rect(round(bx, 1), y + h - 2, round(bw, 1), 2,
                               fill=k.BORDER_HI, rx=1))
        else:
            colour = k.CYAN if val >= peak * 0.7 else (k.BLUE if val >= peak * 0.3 else "#2C5A78")
            body.append(k.rect(round(bx, 1), round(y + h - bh, 1), round(bw, 1),
                               round(bh, 1), fill=colour, rx=3, opacity=0.95))
        if val and val in top3:
            body.append(k.text(bx + bw / 2, y + h - bh - 7, str(val),
                                size=L["callout_size"], fill=k.FG, anchor="middle",
                                weight="bold"))
        label = datetime.strptime(key, "%Y-%m").strftime("%b").upper()
        body.append(k.text(bx + bw / 2, y + h + 16, label, size=L["month_size"],
                            fill=k.FG3, anchor="middle"))
    return "".join(body), y + h + 16


def draw_lang_bars(x, y, rows, w, L):
    """Single stacked bar plus a legend.

    The legend is a 4-up grid at 880px and a single right-aligned column at
    380px: two narrow columns cannot hold a name like "Jupyter Notebook" at a
    font size that survives the phone downscale, and a legible list beats a
    cramped grid.
    """
    body = []
    bar_h = 10
    cx = x
    for i, (lang, pct) in enumerate(rows):
        seg = max(2.0, w * pct / 100.0)
        if cx + seg > x + w:
            seg = x + w - cx
        body.append(k.rect(round(cx, 1), y, round(seg, 1), bar_h,
                           fill=LANG_FILL[i % len(LANG_FILL)],
                           rx=0, opacity=0.92))
        cx += seg

    # Rounded mask ends: redraw thin panel-coloured corners instead of a clip.
    body.insert(0, k.rect(x, y, w, bar_h, fill=k.PANEL_ALT, rx=bar_h / 2))

    size = L["legend_size"]
    row_h = L["legend_row"]
    ly = y + bar_h + 24

    if L["narrow"]:
        for i, (lang, pct) in enumerate(rows):
            yy = ly + i * row_h
            body.append(k.circle(x + 4, yy - 4, 3.5, fill=LANG_FILL[i % len(LANG_FILL)]))
            body.append(k.text(x + 15, yy, lang, size=size, fill=k.FG2))
            body.append(k.text(x + w, yy, "%.1f%%" % pct, size=size, fill=k.FG3,
                               anchor="end"))
        return "".join(body), ly + (len(rows) - 1) * row_h

    per_row = L["legend_cols"]
    col_w = w / per_row
    for i, (lang, pct) in enumerate(rows):
        col, row = i % per_row, i // per_row
        lx = x + col * col_w
        yy = ly + row * row_h
        body.append(k.circle(lx + 4, yy - 4, 3.5, fill=LANG_FILL[i % len(LANG_FILL)]))
        body.append(k.text(lx + 15, yy, "%s %.1f%%" % (lang, pct), size=size, fill=k.FG2))
    return "".join(body), ly + ((len(rows) - 1) // per_row) * row_h


def build(months, total, active, lang_rows, repo_count, lang_count, deployed, L):
    W = L["w"]
    pad = L["pad"]
    inner = W - pad * 2
    parts = []

    hy = pad + 26
    parts.append(k.section_label(pad + 2, hy, "// TELEMETRY", size=L["meta_size"] + 1))
    parts.append(k.text(W - pad - 2, hy, L["header_right"], size=L["meta_size"],
                        fill=k.FG3, anchor="end"))
    parts.append(k.accent_bar(pad + 2, hy + 9, 140, 2))

    # ---- stat strip -------------------------------------------------------
    # Label lines are spelled out per variant rather than auto-wrapped: the only
    # one that needs two lines is the contributions window, and dropping the
    # window to make it fit would make the number vaguer than it is.
    if L["narrow"]:
        labels = (("PUBLIC REPOS",), ("CONTRIBUTIONS", "LAST 12 MONTHS"),
                  ("LANGUAGES IN USE",), ("REPOS WITH LIVE URL",))
    else:
        labels = (("PUBLIC REPOS",), ("CONTRIBUTIONS / 12 MO",),
                  ("LANGUAGES IN USE",), ("REPOS WITH LIVE URL",))
    # The fourth stat reads each repo's homepage field; it does not probe the
    # URL, so the label must say "LIVE URL" and never imply uptime.
    values = (str(repo_count), "{:,}".format(total), str(lang_count), str(deployed))

    sy = hy + 42
    cols = L["stat_cols"]
    col_w = inner / cols
    label_lead = 14
    row_h = L["stat_size"] + 22 + label_lead * (max(len(t) for t in labels) - 1)
    for i, (value, label_lines) in enumerate(zip(values, labels)):
        col, row = i % cols, i // cols
        cx = pad + 2 + col * col_w
        cy = sy + row * row_h
        parts.append(k.text(cx, cy, value, size=L["stat_size"], fill=k.FG, weight="bold"))
        for j, ln in enumerate(label_lines):
            parts.append(k.text(cx, cy + 18 + j * label_lead, ln,
                                size=L["stat_label"], fill=k.FG3,
                                spacing="0" if L["narrow"] else "0.7"))
        if col:
            parts.append(k.line(cx - 14, cy - L["stat_size"] + 3, cx - 14,
                                cy + 24 + label_lead * (len(label_lines) - 1),
                                stroke=k.BORDER, opacity=0.8))
    n_rows = (len(values) + cols - 1) // cols
    stat_bottom = sy + (n_rows - 1) * row_h + 24 + label_lead * (max(len(t) for t in labels) - 1)

    # ---- monthly contribution shape ---------------------------------------
    # Narrow reserves a second label line for every stat row (row_h is uniform),
    # so it already carries ~14u of trailing space the wide strip does not.
    my = stat_bottom + (30 if L["narrow"] else 44)
    parts.append(k.text(pad + 2, my, "COMMIT ACTIVITY · BY MONTH", size=L["meta_size"],
                        fill=k.FG2, spacing="0.8"))
    if not L["narrow"]:
        parts.append(k.text(W - pad - 2, my, "%d active days" % active,
                            size=L["meta_size"], fill=k.FG3, anchor="end"))
    bars, bars_bottom = draw_month_bars(pad + 2, my + 16, inner - 4, months, L)
    parts.append(bars)
    if L["narrow"]:
        parts.append(k.text(pad + 2, bars_bottom + 20, "%d active days" % active,
                            size=L["meta_size"], fill=k.FG3))
        bars_bottom += 20

    # ---- language volume --------------------------------------------------
    gy = bars_bottom + 40
    parts.append(k.line(pad + 2, gy - 20, W - pad - 2, gy - 20, stroke=k.BORDER))
    parts.append(k.text(pad + 2, gy, "CODE VOLUME BY LANGUAGE" if L["narrow"]
                        else "CODE VOLUME BY LANGUAGE · PUBLIC REPOS",
                        size=L["meta_size"], fill=k.FG2, spacing="0.8"))
    lang_svg, lang_bottom = draw_lang_bars(pad + 2, gy + 14, lang_rows, inner - 4, L)
    parts.append(lang_svg)

    height = int(lang_bottom + 24)

    frame = [
        k.rect(0, 0, W, height, fill=k.BG, rx=12),
        k.grid_bg(1, 1, W - 2, height - 2, step=L["grid_step"], opacity=0.5),
        k.rect(0, 0, W, height, fill="url(#panelGlow)", rx=12),
        k.rect(0.5, 0.5, W - 1, height - 1, fill="none", stroke=k.BORDER, rx=12),
    ]
    return k.svg_doc(W, height, "".join(frame) + "".join(parts),
                     "GitHub telemetry for %s" % USER)


def main():
    try:
        months, total, active = get_contributions()
        lang_rows, repo_count, lang_count, deployed = get_languages()
    except Exception as exc:  # noqa: BLE001 - never break the README over telemetry
        print("telemetry: skipping refresh (%s: %s)" % (type(exc).__name__, exc))
        return 0

    wrote = []
    for name, layout in LAYOUTS.items():
        svg = build(months, total, active, lang_rows, repo_count, lang_count,
                    deployed, layout)
        path = os.path.normpath(os.path.join(ASSETS, name + ".svg"))

        old = None
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                old = fh.read()
        if old is not None and old.strip() == svg.strip():
            continue

        k.write(path, svg)
        wrote.append(name + ".svg")

    if not wrote:
        print("telemetry: unchanged")
        return 0
    print("telemetry: wrote %s (%d contributions, %d active days, %d deployed, top lang %s)"
          % (", ".join(wrote), total, active, deployed,
             lang_rows[0][0] if lang_rows else "?"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
