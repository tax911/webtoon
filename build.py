#!/usr/bin/env python3
"""Scan /workspace/webtoon/<series>/ and regenerate the static webtoon viewer."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from html import escape
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = Path(os.environ.get("WEBTOON_SOURCE", "/workspace/webtoon"))
TEMPLATE_DIR = SITE_ROOT / "_templates"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
EP_DIR_RE = re.compile(r"^ep(\d+)(?:_(concepts|concept|preview))?$", re.I)

ICON_MARK = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<circle cx="12" cy="12" r="7"/><path d="M12 1v22M1 12h22"/></svg>'
)
ICON_ARROW = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M5 12h14M13 6l6 6-6 6"/></svg>'
)
ICON_DOWN = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M12 4v16m-6-6 6 6 6-6"/></svg>'
)
ICON_LIST = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M7 6h14M7 12h14M7 18h14M3 6h.01M3 12h.01M3 18h.01"/></svg>'
)
ICON_SLIDERS = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M4 7h16M4 17h16"/>'
    '<circle cx="9" cy="7" r="2.5" fill="currentColor"/>'
    '<circle cx="15" cy="17" r="2.5" fill="currentColor"/></svg>'
)
ICON_PREV = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m14 6-6 6 6 6"/></svg>'
)
ICON_NEXT = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
)
ICON_BOOKMARK = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12v18l-6-4-6 4Z"/></svg>'
)
ICON_TOP = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 14 6-6 6 6"/></svg>'
)
ICON_FOCUS = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5"/>'
    '<circle cx="12" cy="12" r="2"/></svg>'
)
ICON_CLOSE = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>'
)

FONT_LINKS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=Noto+Serif+KR:wght@500&display=swap" rel="stylesheet">"""


def natural_key(name: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]


def image_size(path: Path):
    try:
        from PIL import Image

        with Image.open(path) as img:
            return img.size
    except Exception:
        return None


def copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def load_meta(series_dir: Path) -> dict:
    meta_path = series_dir / "series.json"
    if not meta_path.is_file():
        return {}
    return json.loads(meta_path.read_text(encoding="utf-8"))


def scan_episode_dirs(series_dir: Path) -> dict[int, dict]:
    found: dict[int, dict] = {}
    for child in series_dir.iterdir():
        if not child.is_dir():
            continue
        match = EP_DIR_RE.match(child.name)
        if not match:
            continue
        number = int(match.group(1))
        kind = "concept" if match.group(2) else "episode"
        images = sorted(
            [p for p in child.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
            key=lambda p: natural_key(p.name),
        )
        if not images:
            continue
        existing = found.get(number)
        if existing and existing["kind"] == "episode" and kind == "concept":
            continue
        found[number] = {"number": number, "kind": kind, "source_dir": child, "images": images}
    return found


def pad_episode(number: int) -> str:
    return f"{number:03d}"


def build_placeholder_cover(dest: Path, title: str, subtitle: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    title_esc = escape(title)
    subtitle_esc = escape(subtitle)
    dest.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 768 1152" role="img" aria-label="{title_esc}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#2c2624"/>
      <stop offset="55%" stop-color="#1b191c"/>
      <stop offset="100%" stop-color="#121114"/>
    </linearGradient>
  </defs>
  <rect width="768" height="1152" fill="url(#g)"/>
  <rect x="64" y="64" width="640" height="1024" fill="none" stroke="#d8b77c" stroke-opacity=".35" stroke-width="1.5"/>
  <text x="384" y="540" text-anchor="middle" fill="#d8b77c" font-family="Noto Serif KR, Batang, serif" font-size="64">{title_esc}</text>
  <text x="384" y="600" text-anchor="middle" fill="#c4b49a" font-family="Noto Serif KR, Batang, serif" font-size="22" letter-spacing="6">{subtitle_esc}</text>
</svg>
""",
        encoding="utf-8",
    )


def prepare_series(series_dir: Path) -> dict | None:
    meta = load_meta(series_dir)
    slug = meta.get("id") or series_dir.name
    title = meta.get("title") or slug
    scanned = scan_episode_dirs(series_dir)
    episode_meta = {str(k): v for k, v in (meta.get("episodes") or {}).items()}

    asset_root = SITE_ROOT / "assets" / slug
    out_dir = SITE_ROOT / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    cover_rel = None
    cover_src = None
    if meta.get("cover"):
        candidate = series_dir / meta["cover"]
        if candidate.is_file():
            cover_src = candidate
    episodes = []
    for number in sorted(scanned):
        raw = scanned[number]
        info = episode_meta.get(str(number), {})
        kind = raw["kind"]
        dest_dir = asset_root / "episodes" / pad_episode(number)
        dest_dir.mkdir(parents=True, exist_ok=True)
        copied = []
        captions = info.get("captions") or {}
        for index, src in enumerate(raw["images"]):
            dest = dest_dir / src.name
            copy_file(src, dest)
            size = image_size(src)
            rel = f"../assets/{slug}/episodes/{pad_episode(number)}/{src.name}"
            copied.append(
                {
                    "file": src.name,
                    "src": rel,
                    "abs": f"assets/{slug}/episodes/{pad_episode(number)}/{src.name}",
                    "width": size[0] if size else None,
                    "height": size[1] if size else None,
                    "caption": captions.get(src.name, ""),
                }
            )
        title_ep = info.get("title") or f"{number}화"
        if kind == "concept":
            display_title = f"{number}화 시안 · {title_ep}"
            short_label = f"{number}화 시안"
            summary = info.get("summary") or "완성된 회차 원고가 아닌 주요 장면 시안입니다."
        else:
            display_title = f"{number}화 · {title_ep}"
            short_label = f"{number}화"
            summary = info.get("summary") or ""
        thumb_src = None
        if info.get("thumb"):
            thumb_candidate = series_dir / info["thumb"]
            if thumb_candidate.is_file():
                thumb_name = Path(info["thumb"]).name
                thumb_dest = asset_root / "covers" / thumb_name
                copy_file(thumb_candidate, thumb_dest)
                thumb_src = f"../assets/{slug}/covers/{thumb_name}"
        if thumb_src is None:
            thumb_src = copied[0]["src"]
        episodes.append(
            {
                "number": number,
                "title": title_ep,
                "summary": summary,
                "kind": kind,
                "displayTitle": display_title,
                "shortLabel": short_label,
                "url": f"episode-{pad_episode(number)}.html",
                "thumb": thumb_src,
                "thumbAbs": thumb_src.replace("../", "", 1) if thumb_src.startswith("../") else f"{slug}/{thumb_src}",
                "images": copied,
            }
        )
        if cover_src is None:
            cover_src = raw["images"][0]

    if cover_src is not None:
        cover_name = cover_src.name
        cover_dest = asset_root / "covers" / cover_name
        copy_file(cover_src, cover_dest)
        cover_rel = f"assets/{slug}/covers/{cover_name}"
    else:
        cover_dest = asset_root / "covers" / "placeholder.svg"
        build_placeholder_cover(cover_dest, title, meta.get("title_hanja") or meta.get("title_en") or "")
        cover_rel = f"assets/{slug}/covers/placeholder.svg"

    genre = meta.get("genre") or []
    if isinstance(genre, str):
        genre = [genre]

    return {
        "id": slug,
        "title": title,
        "title_en": meta.get("title_en") or "",
        "title_hanja": meta.get("title_hanja") or "",
        "tagline": meta.get("tagline") or "",
        "synopsis": meta.get("synopsis") or "",
        "genre": genre,
        "format": meta.get("format") or "세로 스크롤",
        "planned_episodes": meta.get("planned_episodes"),
        "footer": meta.get("footer") or "",
        "order": meta.get("order", 100),
        "cover": cover_rel,
        "episodes": episodes,
        "source_dir": str(series_dir),
    }


def head(title: str, description: str, css_href: str, extra: str = "") -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#171719">
<meta name="description" content="{escape(description)}">
<title>{escape(title)}</title>
{FONT_LINKS}
<link rel="stylesheet" href="{css_href}">
<link rel="icon" type="image/svg+xml" href="{'../' if css_href.startswith('../') else ''}favicon.svg">
{extra}
</head>
"""


def site_header(home_href: str, brand: str, links: list[tuple[str, str]]) -> str:
    nav = "".join(f'<a href="{escape(href)}">{escape(label)}</a>' for href, label in links)
    return (
        f'<header class="site-header">'
        f'<a class="brand" href="{escape(home_href)}" aria-label="{escape(brand)} 홈">{ICON_MARK}<span>{escape(brand)}</span></a>'
        f'<nav class="site-links" aria-label="주요 메뉴">{nav}</nav>'
        f"</header>"
    )


def js_payload(series: dict) -> str:
    payload = {
        "seriesId": series["id"],
        "seriesTitle": series["title"],
        "episodes": [
            {
                "number": ep["number"],
                "title": ep["title"],
                "url": ep["url"],
                "kind": ep["kind"],
                "displayTitle": ep["displayTitle"],
                "shortLabel": ep["shortLabel"],
            }
            for ep in series["episodes"]
        ],
    }
    return (
        "<script>window.WEBTOON = "
        + json.dumps(payload, ensure_ascii=False)
        + ";</script>\n"
        '<script src="../js/app.js" defer></script>'
    )


def render_home(all_series: list[dict]) -> str:
    cards = []
    for series in all_series:
        first = series["episodes"][0] if series["episodes"] else None
        href = f"{series['id']}/index.html"
        cover = series["cover"]
        hanja = f'<p class="hanja">{escape(series["title_hanja"])}</p>' if series["title_hanja"] else ""
        eyebrow = series["title_en"] or series["title_hanja"] or "WEBTOON"
        count = len(series["episodes"])
        planned = series.get("planned_episodes")
        if count and any(ep["kind"] == "concept" for ep in series["episodes"]) and not any(
            ep["kind"] == "episode" for ep in series["episodes"]
        ):
            status = f"시안 {count}편"
        else:
            status = f"현재 {count}화" if count else "연재 준비 중"
        if planned:
            status += f" · 예정 {planned}화"
        genre = " · ".join(series["genre"]) if series["genre"] else ""
        meta_bits = [bit for bit in (genre, status, series["format"]) if bit]
        cta = "작품 보기"
        cards.append(
            f"""<a class="series-card" href="{escape(href)}">
  <img class="series-card-cover" src="{escape(cover)}" alt="" width="148" height="222" loading="lazy">
  <div>
    <div class="eyebrow">{escape(eyebrow)}</div>
    <h2>{escape(series["title"])}</h2>
    {hanja}
    <p class="tagline">{escape(series["tagline"] or series["synopsis"])}</p>
    <p class="meta">{escape(" · ".join(meta_bits))}</p>
  </div>
</a>"""
        )
    body = f"""<body>
<a class="skip-link" href="#series">작품 목록으로 건너뛰기</a>
{site_header("index.html", "웹툰 서재", [("#series", "작품 목록")])}
<main class="library" id="series">
  <section class="library-intro">
    <div class="eyebrow">WEBTOON LIBRARY</div>
    <h1>웹툰 서재</h1>
    <p>세로 스크롤로 이어 읽는 작품들입니다. 원하는 작품의 표지를 눌러 회차를 고르세요.</p>
  </section>
  <section class="series-grid" aria-label="작품 목록">
    {''.join(cards)}
  </section>
</main>
<footer class="home-footer"><span class="footer-mark">웹툰 서재</span><span>회차가 추가되면 목록에 자동으로 나타납니다.</span></footer>
</body></html>
"""
    return (
        head("웹툰 서재", "세로 스크롤로 이어 읽는 웹툰을 모았습니다.", "css/style.css")
        + body
    )


def render_series(series: dict) -> str:
    episodes = series["episodes"]
    first = episodes[0] if episodes else None
    latest = episodes[-1] if episodes else None
    first_href = first["url"] if first else "#episodes"
    latest_href = latest["url"] if latest else "#episodes"
    first_label = "시안 보기" if first and first["kind"] == "concept" else "1화부터 정주행"
    latest_label = "최신화 읽기"
    if latest and latest["kind"] == "concept" and (not first or first is latest):
        latest_label = None
    cover_src = "../" + series["cover"]
    hanja = (
        f'<p class="hero-hanja">{escape(series["title_hanja"])}</p>'
        if series["title_hanja"]
        else ""
    )
    tagline_html = ""
    if series["tagline"]:
        tagline_html = "<br>".join(escape(part) for part in series["tagline"].split("\n"))
        tagline_html = f'<p class="hero-tagline">{tagline_html}</p>'
    synopsis_html = ""
    if series["synopsis"]:
        synopsis_html = "<br>".join(escape(part) for part in series["synopsis"].split("\n"))
        synopsis_html = f'<p class="hero-description">{synopsis_html}</p>'
    actions = (
        f'<a class="button button-primary" href="{escape(first_href)}" data-resume-link>'
        f'<span data-button-label>{escape(first_label)}</span>{ICON_ARROW}</a>'
    )
    if latest_label and latest and first and latest is not first:
        actions += f'<a class="button" href="{escape(latest_href)}">{escape(latest_label)}</a>'
    count = len(episodes)
    if count and all(ep["kind"] == "concept" for ep in episodes):
        count_note = f"시안 {count}편"
        heading_count = f"{count:02d}"
        heading_sub = "완성된 회차 대신 공개된 시안입니다"
    else:
        count_note = f"현재 {count}화"
        heading_count = f"{count:02d}"
        heading_sub = "첫 이야기부터 차례로"
    planned = series.get("planned_episodes")
    note_bits = []
    if series["genre"]:
        note_bits.append(escape(" · ".join(series["genre"])))
    note_bits.append(escape(count_note))
    if planned:
        note_bits.append(escape(f"예정 {planned}화"))
    note_bits.append(escape(series["format"]))
    note = "".join(
        (f'<span>{bit}</span>' if i == 0 else f'<i class="dot"></i><span>{bit}</span>')
        for i, bit in enumerate(note_bits)
    )

    rows = []
    for index, ep in enumerate(episodes):
        kicker = f"EPISODE {ep['number']:02d}"
        badges = []
        if ep["kind"] == "concept":
            badges.append('<span class="badge badge-concept">시안</span>')
            kicker = f"{ep['number']}화 시안"
        if index == len(episodes) - 1 and ep["kind"] != "concept":
            badges.append('<span class="badge">최신</span>')
        elif index == len(episodes) - 1 and len(episodes) > 1:
            badges.append('<span class="badge">최신</span>')
        heading = ep["displayTitle"]
        rows.append(
            f"""<a class="episode-row" href="{escape(ep['url'])}">
  <img class="episode-thumb" src="{escape(ep['thumb'])}" width="148" height="102" loading="lazy" alt="">
  <div>
    <div class="episode-kicker">{escape(kicker)}{''.join(badges)}</div>
    <h3>{escape(heading)}</h3>
    <p>{escape(ep['summary'])}</p>
    <span class="read-status" data-read-status="{ep['number']}" hidden></span>
  </div>
  <span class="row-arrow">{ICON_ARROW}</span>
</a>"""
        )

    footer_mark = series["title"]
    footer_text = series["footer"] or series["tagline"] or series["synopsis"]
    eyebrow = series["title_en"] or series["title_hanja"] or "WEBTOON"
    extra = js_payload(series)
    body = f"""<body>
<a class="skip-link" href="#episodes">회차 목록으로 건너뛰기</a>
{site_header("index.html", series["title"], [("#about", "작품 소개"), ("#episodes", "회차 목록")])}
<main class="home">
  <section class="hero" id="about" aria-labelledby="series-title">
    <img class="hero-art" src="{escape(cover_src)}" alt="" width="768" height="1152" fetchpriority="high">
    <div class="hero-content">
      <div class="eyebrow">{escape(eyebrow)}</div>
      <h1 id="series-title">{escape(series["title"])}</h1>
      {hanja}
      {tagline_html}
      {synopsis_html}
      <div class="hero-actions">{actions}</div>
      <p class="hero-note">{note}</p>
    </div>
  </section>
  <section class="chapter-list" id="episodes" aria-labelledby="episodes-title">
    <div class="section-heading">
      <h2 id="episodes-title">전체 회차 <span>{escape(heading_count)}</span></h2>
      <p>{escape(heading_sub)}</p>
    </div>
    {''.join(rows) if rows else '<p class="hero-description">아직 공개된 회차가 없습니다.</p>'}
  </section>
</main>
<footer class="home-footer"><span class="footer-mark">{escape(footer_mark)}</span><span>{escape(footer_text)}</span></footer>
</body></html>
"""
    desc = series["tagline"] or series["synopsis"] or series["title"]
    return head(f'{series["title"]} · 웹툰', desc, "../css/style.css", extra) + body


def render_reader(series: dict, episode: dict) -> str:
    episodes = series["episodes"]
    idx = next(i for i, item in enumerate(episodes) if item["number"] == episode["number"])
    prev_ep = episodes[idx - 1] if idx > 0 else None
    next_ep = episodes[idx + 1] if idx < len(episodes) - 1 else None
    images_html = []
    total = len(episode["images"])
    for i, image in enumerate(episode["images"]):
        attrs = [f'src="{escape(image["src"])}"', 'decoding="async"']
        if image["width"] and image["height"]:
            attrs.append(f'width="{image["width"]}"')
            attrs.append(f'height="{image["height"]}"')
        if i < 2:
            attrs.append('loading="eager"')
            attrs.append('fetchpriority="high"')
        else:
            attrs.append('loading="lazy"')
        alt = f'{episode["shortLabel"]} 원고 {i + 1} / {total}'
        if episode["kind"] == "concept" and image.get("caption"):
            alt = image["caption"]
        attrs.append(f'alt="{escape(alt)}"')
        img = f'<img {" ".join(attrs)}>'
        if image.get("caption"):
            images_html.append(
                f'<figure class="panel">{img}<figcaption>{escape(image["caption"])}</figcaption></figure>'
            )
        else:
            images_html.append(img)

    concept_banner = ""
    if episode["kind"] == "concept":
        concept_banner = (
            '<div class="concept-banner">'
            f'<strong>{escape(episode["shortLabel"])}</strong>'
            f'<p>완성된 회차 원고가 아닙니다. {escape(series["title"])} {episode["number"]}화의 주요 장면 시안입니다. 화풍은 아직 정해지는 중이라 장면마다 그림체가 다를 수 있습니다.</p>'
            "</div>"
        )

    if next_ep:
        next_label = f'{next_ep["shortLabel"]}로 이어 읽기'
        next_btn = (
            f'<a class="button button-primary" href="{escape(next_ep["url"])}" data-episode-link="{next_ep["number"]}">'
            f"{escape(next_label)} {ICON_DOWN}</a>"
        )
        end_copy = "다음 화에서 이야기가 이어집니다."
    else:
        next_btn = ""
        end_copy = (
            "아직 다음 화가 없습니다. 회차가 추가되면 이 목록에 자동으로 나타납니다."
            if episode["kind"] != "concept"
            else "완성된 1화 원고가 등록되면 이 시안 대신 본편이 이 자리에 표시됩니다."
        )
    if episode["kind"] == "concept":
        end_kicker = f'{episode["shortLabel"]} · PREVIEW'
    else:
        end_kicker = f'EPISODE {episode["number"]:02d} · END'

    dialog_items = []
    for ep in episodes:
        dialog_items.append(
            f'<a class="dialog-episode" data-episode-link="{ep["number"]}" href="{escape(ep["url"])}">'
            f'<img src="{escape(ep["thumb"])}" width="66" height="75" alt="" loading="lazy">'
            f'<span><small>{escape(ep["shortLabel"])}</small><strong>{escape(ep["title"])}</strong></span></a>'
        )

    extra = js_payload(series)
    desc = episode["summary"] or series["tagline"] or series["title"]
    body = f"""<body class="reader">
<a class="skip-link" href="#reader-main">웹툰으로 건너뛰기</a>
<div class="reader-progress-track" aria-hidden="true"><div class="reader-progress-fill"></div></div>
<header class="reader-header">
  <div class="reader-title">
    <a class="brand" href="index.html" aria-label="{escape(series['title'])} 홈">{ICON_MARK}<span>{escape(series['title'])}</span></a>
    <span class="current-title" data-current-title>{escape(episode['displayTitle'])}</span>
  </div>
  <nav class="reader-tools" aria-label="읽기 메뉴">
    <button class="icon-button" data-dialog="episodes-dialog" aria-label="회차 목록">{ICON_LIST}<span class="tool-label">회차 목록</span></button>
    <button class="icon-button" data-dialog="settings-dialog" aria-label="보기 설정">{ICON_SLIDERS}</button>
  </nav>
</header>
<main id="reader-main" class="reader-main">
  <article class="chapter" id="ep-{episode['number']}" data-episode="{episode['number']}" aria-label="{escape(episode['displayTitle'])}">
    <h1 class="sr-only">{escape(episode['displayTitle'])}</h1>
    {concept_banner}
    <div class="episode-art">{''.join(images_html)}</div>
    <footer class="chapter-end">
      <span class="small-caps">{escape(end_kicker)}</span>
      <h2>{escape(episode['title'])}</h2>
      <p>{escape(end_copy)}</p>
      <div class="end-actions">
        {next_btn}
        <a class="button" href="index.html#episodes">회차 목록</a>
      </div>
    </footer>
  </article>
</main>
<nav class="reading-dock" aria-label="회차 이동">
  <button class="icon-button" data-prev aria-label="이전 화"{' disabled' if not prev_ep else ''}>{ICON_PREV}</button>
  <span class="dock-status"><strong data-dock-episode>{escape(episode['shortLabel'])}</strong><span data-dock-progress>0%</span></span>
  <button class="icon-button" data-next aria-label="다음 화"{' disabled' if not next_ep else ''}>{ICON_NEXT}</button>
  <button class="icon-button" data-bookmark aria-label="읽던 위치 저장">{ICON_BOOKMARK}</button>
  <button class="icon-button" data-top aria-label="현재 회차 처음으로">{ICON_TOP}</button>
</nav>
<button class="focus-toggle" data-focus aria-label="집중해서 읽기" aria-pressed="false">{ICON_FOCUS}</button>
<dialog id="episodes-dialog" aria-labelledby="episode-dialog-title">
  <div class="dialog-header"><h2 id="episode-dialog-title">회차 목록</h2>
    <button class="icon-button" data-close-dialog aria-label="회차 목록 닫기">{ICON_CLOSE}</button>
  </div>
  <div class="dialog-content">
    {''.join(dialog_items)}
    <a class="dialog-home" href="index.html">작품 소개로 돌아가기</a>
  </div>
</dialog>
<dialog id="settings-dialog" aria-labelledby="settings-title">
  <div class="dialog-header"><h2 id="settings-title">보기 설정</h2>
    <button class="icon-button" data-close-dialog aria-label="보기 설정 닫기">{ICON_CLOSE}</button>
  </div>
  <div class="dialog-content">
    <fieldset class="settings-field"><legend>주변 배경</legend>
      <div class="choice-group">
        <label class="choice"><input type="radio" name="backdrop" value="dark" checked><span>어둡게</span></label>
        <label class="choice"><input type="radio" name="backdrop" value="light"><span>밝게</span></label>
      </div>
    </fieldset>
    <fieldset class="settings-field"><legend>원고 너비</legend>
      <div class="choice-group">
        <label class="choice"><input type="radio" name="width" value="820" checked><span>기본</span></label>
        <label class="choice"><input type="radio" name="width" value="1024"><span>넓게</span></label>
      </div>
    </fieldset>
    <p class="settings-note">읽던 위치와 보기 설정은 이 브라우저에 저장됩니다.</p>
  </div>
</dialog>
<div class="toast" role="status" aria-live="polite" hidden></div>
</body></html>
"""
    return head(
        f'{episode["displayTitle"]} · {series["title"]}',
        desc,
        "../css/style.css",
        extra,
    ) + body


def clean_generated(slugs: list[str]) -> None:
    assets = SITE_ROOT / "assets"
    if assets.exists():
        shutil.rmtree(assets)
    for slug in slugs:
        target = SITE_ROOT / slug
        if target.is_dir():
            shutil.rmtree(target)


def write_static() -> None:
    css_src = TEMPLATE_DIR / "style.css"
    js_src = TEMPLATE_DIR / "app.js"
    css_dest = SITE_ROOT / "css" / "style.css"
    js_dest = SITE_ROOT / "js" / "app.js"
    css_dest.parent.mkdir(parents=True, exist_ok=True)
    js_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(css_src, css_dest)
    shutil.copy2(js_src, js_dest)
    favicon = SITE_ROOT / "favicon.svg"
    favicon.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="8" fill="#171719"/>'
        '<g stroke="#d8b77c" fill="none" stroke-width="1.5">'
        '<circle cx="16" cy="16" r="9"/>'
        '<path d="M16 3v26M3 16h26"/></g></svg>\n',
        encoding="utf-8",
    )


def discover_series() -> list[Path]:
    if not SOURCE_ROOT.is_dir():
        raise SystemExit(f"소스 폴더가 없습니다: {SOURCE_ROOT}")
    found = []
    for child in sorted(SOURCE_ROOT.iterdir()):
        if child.is_dir() and (child / "series.json").is_file():
            found.append(child)
    if not found:
        raise SystemExit(f"{SOURCE_ROOT} 아래에 series.json이 있는 작품 폴더가 없습니다.")
    return found


def main() -> int:
    sources = discover_series()
    slugs = [(load_meta(path).get("id") or path.name) for path in sources]
    clean_generated(slugs)
    write_static()

    all_series = []
    for path in sources:
        series = prepare_series(path)
        if series:
            all_series.append(series)
    all_series.sort(key=lambda item: (item.get("order", 100), item["title"]))

    (SITE_ROOT / "index.html").write_text(render_home(all_series), encoding="utf-8")
    for series in all_series:
        series_dir = SITE_ROOT / series["id"]
        series_dir.mkdir(parents=True, exist_ok=True)
        (series_dir / "index.html").write_text(render_series(series), encoding="utf-8")
        for episode in series["episodes"]:
            (series_dir / episode["url"]).write_text(
                render_reader(series, episode), encoding="utf-8"
            )

    catalog = []
    for series in all_series:
        catalog.append(
            {
                "id": series["id"],
                "title": series["title"],
                "title_en": series["title_en"],
                "title_hanja": series["title_hanja"],
                "tagline": series["tagline"],
                "synopsis": series["synopsis"],
                "genre": series["genre"],
                "format": series["format"],
                "planned_episodes": series["planned_episodes"],
                "cover": series["cover"],
                "url": f"{series['id']}/index.html",
                "episodes": [
                    {
                        "number": ep["number"],
                        "title": ep["title"],
                        "summary": ep["summary"],
                        "kind": ep["kind"],
                        "displayTitle": ep["displayTitle"],
                        "url": f"{series['id']}/{ep['url']}",
                        "imageCount": len(ep["images"]),
                        "images": [img["abs"] for img in ep["images"]],
                    }
                    for ep in series["episodes"]
                ],
            }
        )
    (SITE_ROOT / "catalog.json").write_text(
        json.dumps({"series": catalog}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"built {len(all_series)} series -> {SITE_ROOT}")
    for series in all_series:
        kinds = ", ".join(
            f"{ep['shortLabel']} ({len(ep['images'])} images, {ep['kind']})"
            for ep in series["episodes"]
        )
        print(f"  - {series['title']} [{series['id']}]: {kinds or 'no episodes'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
