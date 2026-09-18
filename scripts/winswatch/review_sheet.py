"""Tile every lab poster (plus first season poster and first episode still per show) into one PNG for review.
Usage: python review_sheet.py --sections 4,5 --out review.png"""
import argparse, os, io, urllib.parse, requests
from PIL import Image, ImageDraw
from dotenv import load_dotenv

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sections", required=True); ap.add_argument("--out", default="review.png"); ap.add_argument("--env", default="/mnt/nastower/appdata/scripts/winswatch/.env")
    a = ap.parse_args(); load_dotenv(a.env); url, tok = os.environ["PLEX_URL"], os.environ["PLEX_TOKEN"]
    H = {"X-Plex-Token": tok, "Accept": "application/json"}
    tiles = []
    for sec in a.sections.split(","):
        for it in requests.get(f"{url}/library/sections/{sec}/all", headers=H, timeout=60).json()["MediaContainer"].get("Metadata", []):
            tiles.append((it["title"], it["thumb"], False))
            if it["type"] == "show":
                for s in requests.get(f"{url}{it['key']}", headers=H, timeout=60).json()["MediaContainer"].get("Metadata", [])[:1]:
                    tiles.append((f"{it['title']} · {s['title']}", s["thumb"], False))
                    eps = requests.get(f"{url}{s['key']}", headers=H, timeout=60).json()["MediaContainer"].get("Metadata", [])
                    if eps: tiles.append((f"{it['title']} · {eps[0]['title'][:24]}", eps[0]["thumb"], True))
    W, Hh = 300, 450; cols = 6; rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W, rows * (Hh + 26)), "#101014"); d = ImageDraw.Draw(sheet)
    for i, (title, thumb, wide) in enumerate(tiles):
        img = Image.open(io.BytesIO(requests.get(f"{url}/photo/:/transcode?url={urllib.parse.quote(thumb)}&width=600&height={338 if wide else 900}&minSize=1&upscale=1&X-Plex-Token={tok}", timeout=60).content)).convert("RGB")
        img.thumbnail((W, Hh)); x, y = (i % cols) * W, (i // cols) * (Hh + 26)
        sheet.paste(img, (x + (W - img.width) // 2, y)); d.text((x + 4, y + Hh + 6), title[:40], fill="white")
    sheet.save(a.out); print(f"wrote {a.out} with {len(tiles)} tiles")

if __name__ == "__main__":
    main()
