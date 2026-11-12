#!/usr/bin/env python3
import argparse
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image


DEFAULT_SLUG = "little-maple-henesys-adventures"
PAGE_URL = f"https://e.kakao.com/t/{DEFAULT_SLUG}?t_obj=creator_items_recommended"
DETAIL_API_TEMPLATE = "https://e.kakao.com/api/items/{slug}"


def extension_from_content_type(content_type: str | None) -> str:
    if not content_type:
        return ".bin"
    content_type = content_type.split(";", 1)[0].strip().lower()
    if content_type == "image/webp":
        return ".webp"
    if content_type == "image/gif":
        return ".gif"
    if content_type == "image/png":
        return ".png"
    if content_type == "image/jpeg":
        return ".jpg"
    return ".bin"


def filename_from_url(url: str, index: int, content_type: str | None) -> str:
    name = Path(urlparse(url).path).name
    ext = extension_from_content_type(content_type)
    if not name:
        name = f"{index:03d}{ext}"
    elif Path(name).suffix.lower() != ext:
        name = f"{name}{ext}"
    return name


def slug_from_url(url: str) -> str:
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "items" and parts[2]:
        return parts[2]
    if len(parts) >= 2 and parts[0] == "t" and parts[1]:
        return parts[1]
    if len(parts) == 1 and parts[0]:
        return parts[0]
    raise SystemExit(f"cannot parse slug from URL: {url}")


def fetch_animated_urls(session: requests.Session, slug: str) -> list[str]:
    resp = session.get(DETAIL_API_TEMPLATE.format(slug=slug), timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    items = payload.get("contents", {}).get("items", [])
    urls = []
    for item in items:
        url = item.get("animatedUrl")
        if isinstance(url, str) and url:
            urls.append(url)

    if not urls:
        raise SystemExit("No animatedUrl entries found in contents.items")

    return urls


def convert_webp_to_gif(source_path: Path, gif_path: Path) -> None:
    with Image.open(source_path) as image:
        frames = []
        durations = []
        transparent_index = 255

        for frame_index in range(getattr(image, "n_frames", 1)):
            image.seek(frame_index)
            frame = image.convert("RGBA")
            alpha = frame.getchannel("A")
            rgb_frame = Image.new("RGB", frame.size, (0, 0, 0))
            rgb_frame.paste(frame, mask=alpha)

            # Keep one palette slot free for transparency.
            palette_frame = rgb_frame.quantize(colors=255)
            palette = palette_frame.getpalette() or []
            if len(palette) < 768:
                palette.extend([0] * (768 - len(palette)))
            palette_frame.putpalette(palette)

            transparent_mask = alpha.point(lambda value: 255 if value == 0 else 0)
            palette_frame.paste(transparent_index, mask=transparent_mask)
            palette_frame.info["transparency"] = transparent_index
            palette_frame.info["disposal"] = 2

            frames.append(palette_frame)
            durations.append(image.info.get("duration", 100))

        if not frames:
            raise RuntimeError(f"No frames found in {source_path}")

        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            loop=0,
            duration=durations,
            transparency=transparent_index,
            disposal=2,
        )


def download_files(session: requests.Session, urls: list[str], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(urls, start=1):
        resp = session.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        path = out_dir / filename_from_url(url, index, resp.headers.get("content-type"))

        with path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)

        print(f"saved {path}")

        if path.suffix.lower() == ".webp":
            gif_path = path.with_suffix(".gif")
            convert_webp_to_gif(path, gif_path)
            print(f"converted {gif_path}")

    print(f"done: {len(urls)} file(s) -> {out_dir}")


def main():
    parser = argparse.ArgumentParser(description="Download animated images from a Kakao emoticon detail page.")
    parser.add_argument("--slug", default=DEFAULT_SLUG, help="Kakao emoticon slug")
    parser.add_argument("--url", default=None, help="Full Kakao emoticon page URL (overrides --slug), e.g. https://e.kakao.com/t/<slug>")
    parser.add_argument("--out", default="kakao_section_animations", help="Output directory")
    args = parser.parse_args()

    if args.url:
        slug = slug_from_url(args.url)
        page_url = args.url
    else:
        slug = args.slug
        page_url = f"https://e.kakao.com/t/{slug}?t_obj=creator_items_recommended"
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Referer": page_url,
            "Accept": "application/json, text/plain, */*",
        }
    )

    urls = fetch_animated_urls(session, slug)
    out_dir = Path(args.out) / slug
    download_files(session, urls, out_dir)


if __name__ == "__main__":
    main()
