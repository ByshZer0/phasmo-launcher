"""生成应用图标（需要 Pillow，仅开发/打包时使用）。

用法：``python scripts/generate_icon.py``
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SCALE = 2
SIZE = 512
S = SIZE * SCALE


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (8 * SCALE, 8 * SCALE, 504 * SCALE, 504 * SCALE),
        radius=112 * SCALE,
        fill="#0B0D12",
        outline="#2A3446",
        width=4 * SCALE,
    )

    # 绿色光晕，增加幽灵主题的氛围。
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        (110 * SCALE, 80 * SCALE, 402 * SCALE, 430 * SCALE),
        fill=(124, 227, 161, 105),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(34 * SCALE))
    image.alpha_composite(glow)

    ghost = "#E9FFF1"
    shade = "#B9E9C9"
    eye = "#0B0D12"

    # 幽灵身体：顶部圆头 + 矩形身体 + 底部三个圆脚。
    draw.ellipse((128 * SCALE, 88 * SCALE, 384 * SCALE, 344 * SCALE), fill=ghost)
    draw.rectangle((128 * SCALE, 216 * SCALE, 384 * SCALE, 356 * SCALE), fill=ghost)
    for left in (128, 211, 294):
        draw.ellipse(
            (left * SCALE, 306 * SCALE, (left + 90) * SCALE, 396 * SCALE),
            fill=ghost,
        )

    # 一点点侧边阴影，避免纯色太平。
    draw.ellipse((330 * SCALE, 110 * SCALE, 384 * SCALE, 330 * SCALE), fill=shade)
    draw.ellipse((128 * SCALE, 88 * SCALE, 384 * SCALE, 344 * SCALE), fill=ghost)

    # 眼睛与嘴巴。
    draw.rounded_rectangle(
        (190 * SCALE, 188 * SCALE, 224 * SCALE, 246 * SCALE),
        radius=17 * SCALE,
        fill=eye,
    )
    draw.rounded_rectangle(
        (288 * SCALE, 188 * SCALE, 322 * SCALE, 246 * SCALE),
        radius=17 * SCALE,
        fill=eye,
    )
    draw.ellipse((242 * SCALE, 274 * SCALE, 270 * SCALE, 298 * SCALE), fill=eye)

    # 高光。
    draw.ellipse((199 * SCALE, 197 * SCALE, 210 * SCALE, 211 * SCALE), fill="#7CE3A1")
    draw.ellipse((297 * SCALE, 197 * SCALE, 308 * SCALE, 211 * SCALE), fill="#7CE3A1")

    icon = image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    icon.save(ASSETS / "icon.png")
    icon.save(
        ASSETS / "app.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"已生成：{ASSETS / 'app.ico'}")
    print(f"已生成：{ASSETS / 'icon.png'}")


if __name__ == "__main__":
    main()
