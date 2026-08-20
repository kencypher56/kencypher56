#!/usr/bin/env python3
"""Generate self-hosted stats SVGs from the GitHub API.

The public github-readme-stats and github-profile-trophy instances go down
(503 DEPLOYMENT_PAUSED / 402 DEPLOYMENT_DISABLED), which leaves broken images
on the profile. These cards are rendered here and committed to the repo, so
they render from raw.githubusercontent.com and never depend on a third party.

Run locally:   python scripts/gen_stats.py
In Actions:    GITHUB_TOKEN is picked up automatically for a higher rate limit.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("STATS_USER", "kencypher56")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

BG = "#0d1117"
BORDER = "#1f2b3d"
ACCENT = "#00e5a0"
CYAN = "#22d3ee"
INDIGO = "#818cf8"
PINK = "#f472b6"
AMBER = "#fbbf24"
TEXT = "#e6edf3"
MUTED = "#9fb3c8"
DIM = "#5b6b86"

CYCLE = [ACCENT, CYAN, INDIGO, PINK, AMBER, "#c084fc"]

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "HTML": "#e34c26",
    "CSS": "#563d7c", "C++": "#f34b7d", "C": "#555555", "Shell": "#89e051",
    "Java": "#b07219", "TypeScript": "#3178c6", "Makefile": "#427819",
    "Batchfile": "#C1F12E", "PowerShell": "#012456", "Dockerfile": "#384d54",
    "Kotlin": "#A97BFF", "Ruby": "#701516", "Go": "#00ADD8", "Rust": "#dea584",
    "SCSS": "#c6538c", "Vue": "#41b883", "PHP": "#4F5D95",
}


def api(path):
    url = path if path.startswith("http") else "https://api.github.com" + path
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "kencypher56-profile-stats",
    })
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def collect():
    user = api("/users/%s" % USER)
    repos, page = [], 1
    while True:
        batch = api("/users/%s/repos?per_page=100&page=%d&type=owner" % (USER, page))
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    own = [r for r in repos if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in own)
    forks = sum(r.get("forks_count", 0) for r in own)

    totals = {}
    for r in own:
        try:
            for lang, size in api("/repos/%s/%s/languages" % (USER, r["name"])).items():
                totals[lang] = totals.get(lang, 0) + size
        except urllib.error.HTTPError as e:
            print("  ! languages for %s: %s" % (r["name"], e), file=sys.stderr)

    created = datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    years = (datetime.now(timezone.utc) - created).days / 365.25

    return {
        "repos": len(own),
        "stars": stars,
        "forks": forks,
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "langs": sorted(totals.items(), key=lambda kv: -kv[1]),
        "bytes": sum(totals.values()),
        "years": years,
        "since": created.strftime("%b %Y"),
        "updated": datetime.now(timezone.utc).strftime("%d %b %Y"),
    }


HEAD = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
    'role="img" aria-label="{label}">\n<title>{label}</title>\n<defs>\n'
    '<linearGradient id="ln" x1="0" y1="0" x2="1" y2="0">'
    '<stop offset="0%" stop-color="{a}"/><stop offset="50%" stop-color="{c}"/>'
    '<stop offset="100%" stop-color="{i}"/>'
    '<animate attributeName="x1" values="0;0.5;0" dur="7s" repeatCount="indefinite"/>'
    '<animate attributeName="x2" values="1;1.5;1" dur="7s" repeatCount="indefinite"/></linearGradient>\n'
    '<clipPath id="cf"><rect x="0" y="0" width="{w}" height="{h}" rx="14"/></clipPath>\n'
    '<style>.m{{font-family:"JetBrains Mono","Fira Code",Consolas,"Courier New",monospace}}'
    '.t{{font-size:14px;fill:{t};font-weight:600;letter-spacing:.6px}}'
    '.k{{font-size:12.5px;fill:{mu}}}.v{{font-size:15px;fill:{t};font-weight:600}}'
    '.s{{font-size:10.5px;fill:{d};letter-spacing:1px}}</style>\n</defs>\n'
    '<g clip-path="url(#cf)"><rect width="{w}" height="{h}" fill="{bg}"/>\n'
)
FOOT = '<rect x="0" y="{by}" width="{w}" height="3" fill="url(#ln)"/>\n' \
       '<rect x="0" y="0" width="{w}" height="{h}" rx="14" fill="none" stroke="{br}" stroke-width="1.5"/></g></svg>\n'


def head(w, h, label):
    return HEAD.format(w=w, h=h, label=esc(label), a=ACCENT, c=CYAN, i=INDIGO,
                       t=TEXT, mu=MUTED, d=DIM, bg=BG)


def foot(w, h):
    return FOOT.format(w=w, h=h, by=h - 3, br=BORDER)


def stats_card(d):
    w, h = 480, 215
    rows = [
        ("Public repositories", d["repos"], ACCENT),
        ("Total stars earned", d["stars"], AMBER),
        ("Total forks", d["forks"], CYAN),
        ("Followers", d["followers"], INDIGO),
        ("Languages in use", len(d["langs"]), PINK),
    ]
    s = head(w, h, "GitHub statistics for %s" % USER)
    s += '<text x="22" y="32" class="m t">%s<tspan fill="%s">\'s</tspan> github</text>\n' % (esc(USER), ACCENT)
    s += '<text x="%d" y="32" class="m s" text-anchor="end">SINCE %s</text>\n' % (w - 22, esc(d["since"].upper()))
    s += '<path d="M22 44 H%d" stroke="%s" stroke-width="1"/>\n' % (w - 22, BORDER)
    y = 70
    for idx, (label, value, color) in enumerate(rows):
        s += '<g>\n'
        s += '<circle cx="30" cy="%d" r="3.5" fill="%s"><animate attributeName="opacity" values="1;.3;1" dur="%.1fs" repeatCount="indefinite"/></circle>\n' % (y - 5, color, 2.0 + idx * 0.3)
        s += '<text x="44" y="%d" class="m k">%s</text>\n' % (y, esc(label))
        s += '<text x="%d" y="%d" class="m v" text-anchor="end" fill="%s">%s</text>\n' % (w - 22, y, color, value)
        s += '</g>\n'
        y += 25
    s += '<text x="22" y="%d" class="m s">UPDATED %s</text>\n' % (h - 14, esc(d["updated"].upper()))
    s += foot(w, h)
    return s


def langs_card(d):
    w, h = 480, 215
    top = d["langs"][:6]
    total = sum(v for _, v in top) or 1
    s = head(w, h, "Most used languages by %s" % USER)
    s += '<text x="22" y="32" class="m t">most used <tspan fill="%s">languages</tspan></text>\n' % ACCENT
    s += '<text x="%d" y="32" class="m s" text-anchor="end">BY BYTES</text>\n' % (w - 22)
    s += '<path d="M22 44 H%d" stroke="%s" stroke-width="1"/>\n' % (w - 22, BORDER)
    y = 68
    bar_x, bar_w = 22, w - 44
    for idx, (lang, size) in enumerate(top):
        pct = size / total * 100
        color = LANG_COLORS.get(lang, CYCLE[idx % len(CYCLE)])
        s += '<text x="22" y="%d" class="m k" fill="%s">%s</text>\n' % (y, TEXT, esc(lang))
        s += '<text x="%d" y="%d" class="m k" text-anchor="end">%.1f%%</text>\n' % (w - 22, y, pct)
        s += '<rect x="%d" y="%d" width="%d" height="7" rx="3.5" fill="#16233a"/>\n' % (bar_x, y + 6, bar_w)
        s += ('<rect x="%d" y="%d" width="0" height="7" rx="3.5" fill="%s">'
              '<animate attributeName="width" values="0;%.1f" dur="1.1s" begin="%.2fs" fill="freeze"/></rect>\n'
              % (bar_x, y + 6, color, bar_w * pct / 100, 0.2 + idx * 0.12))
        y += 24
    s += foot(w, h)
    return s


def highlights_card(d):
    w, h = 1000, 118
    kb = d["bytes"] / 1024.0
    code = "%.1f MB" % (kb / 1024.0) if kb >= 1024 else "%d KB" % kb
    top_lang = d["langs"][0][0] if d["langs"] else "-"
    tiles = [
        ("REPOSITORIES", d["repos"], ACCENT),
        ("LANGUAGES", len(d["langs"]), CYAN),
        ("CODE WRITTEN", code, AMBER),
        ("TOP LANGUAGE", top_lang, INDIGO),
        ("YEARS ON GITHUB", "%.1f" % d["years"], PINK),
    ]
    s = head(w, h, "Profile highlights for %s" % USER)
    tile_w, gap = 180, 16
    start = (w - (tile_w * len(tiles) + gap * (len(tiles) - 1))) / 2
    for idx, (label, value, color) in enumerate(tiles):
        x = start + idx * (tile_w + gap)
        s += '<g>\n'
        s += '<rect x="%.1f" y="22" width="%d" height="70" rx="12" fill="%s" fill-opacity=".08" stroke="%s" stroke-opacity=".45"/>\n' % (x, tile_w, color, color)
        s += '<text x="%.1f" y="60" class="m" font-size="26" font-weight="700" fill="%s" text-anchor="middle">%s</text>\n' % (x + tile_w / 2, color, value)
        s += '<text x="%.1f" y="80" class="m s" text-anchor="middle">%s</text>\n' % (x + tile_w / 2, esc(label))
        s += '</g>\n'
    s += foot(w, h)
    return s


def main():
    print("fetching GitHub data for %s ..." % USER)
    d = collect()
    print("  repos=%(repos)d stars=%(stars)d forks=%(forks)d followers=%(followers)d" % d)
    print("  languages: %s" % ", ".join(l for l, _ in d["langs"][:6]))
    os.makedirs(OUT, exist_ok=True)
    for name, svg in (("stats", stats_card(d)), ("langs", langs_card(d)),
                      ("highlights", highlights_card(d))):
        path = os.path.join(OUT, "%s.svg" % name)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        print("  wrote assets/%s.svg (%d bytes)" % (name, len(svg)))


if __name__ == "__main__":
    main()
