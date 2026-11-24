"""The app icon, drawn in code so the package needs no image files."""
from PIL import Image, ImageDraw

BG = (20, 20, 24, 255)
ACCENT = (76, 194, 255, 255)


def draw(size: int = 256) -> Image.Image:
    s = 4  # draw large, then downsample for smooth edges
    n = size * s
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, n - 1, n - 1), radius=n * 0.22, fill=BG)
    w = n * 0.11  # stroke width
    cx = n / 2
    # down arrow
    d.rectangle((cx - w / 2, n * 0.2, cx + w / 2, n * 0.56), fill=ACCENT)
    d.polygon([(cx - n * 0.22, n * 0.44), (cx + n * 0.22, n * 0.44), (cx, n * 0.68)], fill=ACCENT)
    # tray line
    d.rounded_rectangle((n * 0.22, n * 0.76, n * 0.78, n * 0.76 + w), radius=w / 2, fill=ACCENT)
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "icon.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    draw(512).save(out)
