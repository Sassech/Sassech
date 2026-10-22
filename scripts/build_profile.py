#!/usr/bin/env python3
"""Render the generated blocks of the profile README from profile.yml.

Usage:
    python3 scripts/build_profile.py           # rewrite README.md in place
    python3 scripts/build_profile.py --check   # exit 1 if README.md is stale

Generated blocks are delimited in README.md by:

    <!-- NAME:START -->
    ...generated content...
    <!-- NAME:END -->

Only those blocks are touched; every other line is left as you wrote it.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - dependency hint
    sys.exit("Missing dependency. Install it with: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "profile.yml"
README_PATH = ROOT / "README.md"

STACK_SECTIONS = (
    ("languages", "Languages"),
    ("frameworks", "Frameworks"),
    ("tools", "Tools, infra & data"),
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def shield(
    label: str,
    color: str,
    logo: str | None = None,
    *,
    style: str = "for-the-badge",
    logo_color: str = "white",
) -> str:
    """Build a shields.io static badge URL."""
    text = label.replace("-", "--").replace("_", "__").replace(" ", "%20")
    url = f"https://img.shields.io/badge/{text}-{color}?style={style}"
    if logo:
        url += f"&logo={logo}&logoColor={logo_color}"
    return url


def attr(value: str) -> str:
    """Escape text for use inside an HTML attribute."""
    return html.escape(str(value), quote=True)


def typing_url(typing: dict, lines: list[str]) -> str:
    """Build the readme-typing-svg URL from a plain list of lines."""
    # quote_plus encodes spaces as '+', commas as '%2C', etc. Lines are joined
    # with a literal ';' afterwards, so a semicolon inside a line cannot break
    # the separator.
    encoded = ";".join(quote_plus(line, safe="") for line in lines)
    params = {
        "font": typing.get("font", "Inconsolata"),
        "weight": typing.get("weight", 500),
        "size": typing.get("size", 50),
        "duration": typing.get("duration", 4000),
        "pause": typing.get("pause", 300),
        "color": typing.get("color", "A7A459"),
        "center": "true",
        "vCenter": "true",
        "multiline": "true",
        "repeat": "false",
        "random": "false",
        "width": typing.get("width", 1300),
        "height": typing.get("height", 140),
    }
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"https://readme-typing-svg.demolab.com?{query}&lines={encoded}"


# --------------------------------------------------------------------------- #
# block renderers
# --------------------------------------------------------------------------- #
def render_socials(cfg: dict) -> str:
    icons = []
    for social in cfg.get("header", {}).get("socials") or []:
        url = shield(
            social["label"],
            social["color"],
            social.get("logo"),
            style=social.get("style", "flat"),
            logo_color=social.get("logo_color", "white"),
        )
        name = social.get("name", social["label"])
        icons.append(
            f'<a href="{attr(social["url"])}" title="{attr(name)}">'
            f'<img src="{url}" alt="{attr(name)}" /></a>'
        )
    return "\n".join(icons)


def render_header(cfg: dict) -> str:
    header = cfg.get("header") or {}
    typing = dict(header.get("typing") or {})
    lines = typing.pop("lines", None) or []
    bio = header.get("bio") or []
    gif = header.get("gif")
    avatar = header.get("avatar")

    out = ['<div align="center">', ""]

    if avatar:
        out.append(f'<img src="{attr(avatar)}" width="25%" align="right" alt="" />')

    if lines:
        width = "70%" if avatar else "100%"
        out.append(
            f'<img src="{typing_url(typing, lines)}" width="{width}" '
            f'alt="{attr(lines[0])}" />'
        )

    out.extend(["", "<br><br>"])

    if bio:
        out.append("<pre>")
        out.extend(f"    {line}" for line in bio)
        out.extend(["</pre>", "", "<br>"])

    if gif:
        out.extend([f'<img src="{attr(gif)}" height="40" alt="" />', "", "<br>"])

    icons = render_socials(cfg)
    if icons:
        out.extend(["", icons])

    out.extend(["", "</div>"])
    return "\n".join(out)


def render_stack(cfg: dict) -> str:
    stack = cfg.get("stack") or {}
    out: list[str] = []
    for key, title in STACK_SECTIONS:
        items = stack.get(key) or []
        if not items:
            continue
        # One badge per source line: same rendered row, readable diff.
        badges = "\n".join(
            f'<img src="{shield(item["label"], item["color"], item.get("logo"), logo_color=item.get("logo_color", "white"))}" '
            f'alt="{attr(item["label"])}" />'
            for item in items
        )
        out.extend([f"### {title}", "", badges, ""])
    return "\n".join(out).rstrip()


def render_stats(cfg: dict) -> str:
    user = cfg["username"]
    stats = cfg.get("stats") or {}
    theme = stats.get("theme", "tokyonight")
    gh = "https://github-readme-stats.vercel.app/api"
    summary = "https://github-profile-summary-cards.vercel.app/api/cards"

    out: list[str] = []

    if stats.get("stats_card", True) or stats.get("top_languages", True):
        cards = []
        if stats.get("stats_card", True):
            cards.append(
                f'<img height="180em" src="{gh}?username={user}'
                f"&show_icons=true&include_all_commits=true&count_private=true"
                f"&show=prs_merged,prs_merged_percentage&hide_border=true&theme={theme}"
                f'" alt="GitHub stats" />'
            )
        if stats.get("top_languages", True):
            cards.append(
                f'<img height="180em" src="{gh}/top-langs?username={user}'
                f"&layout=compact&langs_count=8&hide_border=true&theme={theme}"
                f'" alt="Top languages" />'
            )
        out.extend(['<p align="center">', "  " + "\n  ".join(cards), "</p>", ""])

    if stats.get("streak", True):
        out.extend(
            [
                '<p align="center">',
                f'  <img width="80%" src="https://streak-stats.demolab.com?user={user}'
                f'&theme={theme}&hide_border=true" alt="Contribution streak" />',
                "</p>",
                "",
            ]
        )

    if stats.get("summary_cards", True):
        offset = stats.get("utc_offset", 0)
        out.extend(
            [
                '<p align="center">',
                f'  <img width="49%" src="{summary}/profile-details?username={user}'
                f'&theme={theme}" alt="Commits, pull requests, issues and stars" />',
                f'  <img width="49%" src="{summary}/productive-time?username={user}'
                f'&theme={theme}&utcOffset={offset}" alt="Most productive time" />',
                "</p>",
                "",
            ]
        )

    if stats.get("activity_graph", True):
        out.extend(
            [
                '<p align="center">',
                f'  <img width="95%" src="https://github-readme-activity-graph.vercel.app/graph'
                f'?username={user}&theme=tokyo-night&hide_border=true&area=true"'
                f' alt="Contribution activity graph" />',
                "</p>",
                "",
            ]
        )

    if stats.get("trophies", True):
        out.extend(
            [
                '<p align="center">',
                f'  <img src="https://github-profile-trophy.vercel.app/?username={user}'
                f'&theme={theme}&no-frame=true&no-bg=true&column=7&margin-w=8"'
                f' alt="GitHub trophies" />',
                "</p>",
                "",
            ]
        )

    if stats.get("snake", False):
        out.extend(
            [
                '<p align="center">',
                f'  <img width="95%" src="https://raw.githubusercontent.com/{user}/{user}'
                f'/output/snake.svg" alt="Contribution snake" />',
                "</p>",
                "",
            ]
        )

    return "\n".join(out).rstrip()


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open(encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    username = str(cfg.get("username", "")).strip().lstrip("@")
    if not username:
        sys.exit("profile.yml: 'username' is required")
    cfg["username"] = username
    return cfg


def replace_block(text: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- {re.escape(name)}:START -->).*?(<!-- {re.escape(name)}:END -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        sys.exit(f"README.md is missing the {name}:START / {name}:END markers")
    return pattern.sub(
        lambda match: f"{match.group(1)}\n{body}\n{match.group(2)}",
        text,
        count=1,
    )


def build() -> str:
    cfg = load_config()
    text = README_PATH.read_text(encoding="utf-8")
    text = replace_block(text, "HEADER", render_header(cfg))
    text = replace_block(text, "STACK", render_stack(cfg))
    text = replace_block(text, "STATS", render_stats(cfg))
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit with status 1 when README.md does not match profile.yml",
    )
    args = parser.parse_args(argv)

    rendered = build()
    current = README_PATH.read_text(encoding="utf-8")

    if args.check:
        if rendered != current:
            print("README.md is out of date. Run: python3 scripts/build_profile.py")
            return 1
        print("README.md is up to date.")
        return 0

    if rendered == current:
        print("Nothing to update.")
        return 0

    README_PATH.write_text(rendered, encoding="utf-8")
    print("README.md updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
