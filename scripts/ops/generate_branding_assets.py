"""
Generate high-fidelity Meme Hunter branding icons & favicons.
"""
import math
from PIL import Image, ImageDraw

def create_meme_hunter_icon(size=512):
    # Create canvas with RGBA transparency
    # Render at 4x supersampling for ultra smooth anti-aliased edges
    scale = 4
    dim = size * scale
    img = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = dim / 2, dim / 2
    r_outer = dim * 0.46
    r_mid = dim * 0.38
    r_inner = dim * 0.22

    # Draw dark circular cockpit HUD base
    base_r = dim * 0.48
    draw.ellipse(
        [cx - base_r, cy - base_r, cx + base_r, cy + base_r],
        fill=(10, 15, 26, 240),
        outline=(16, 185, 129, 200),
        width=int(6 * scale),
    )

    # Outer HUD Ring (Cyan glow)
    draw.ellipse(
        [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
        outline=(6, 182, 212, 160),
        width=int(4 * scale),
    )

    # Outer Reticle Tick Marks every 30 degrees
    for deg in range(0, 360, 30):
        rad = math.radians(deg)
        x1 = cx + (r_outer - 8 * scale) * math.cos(rad)
        y1 = cy + (r_outer - 8 * scale) * math.sin(rad)
        x2 = cx + (r_outer + 8 * scale) * math.cos(rad)
        y2 = cy + (r_outer + 8 * scale) * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=(16, 185, 129, 220), width=int(3 * scale))

    # Mid Ring (Emerald)
    draw.ellipse(
        [cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid],
        outline=(16, 185, 129, 180),
        width=int(3 * scale),
    )

    # Crosshair Lines (Gapped at center)
    cross_w = int(4 * scale)
    # Top
    draw.line([(cx, cy - r_outer * 1.05), (cx, cy - r_inner * 0.8)], fill=(6, 182, 212, 240), width=cross_w)
    # Bottom
    draw.line([(cx, cy + r_inner * 0.8), (cx, cy + r_outer * 1.05)], fill=(6, 182, 212, 240), width=cross_w)
    # Left
    draw.line([(cx - r_outer * 1.05, cy), (cx - r_inner * 0.8, cy)], fill=(6, 182, 212, 240), width=cross_w)
    # Right
    draw.line([(cx + r_inner * 0.8, cy), (cx + r_outer * 1.05, cy)], fill=(6, 182, 212, 240), width=cross_w)

    # Hunter's Bow Curve (Arcing from top-left to bottom-left)
    bow_pts = []
    for t in range(-45, 46, 2):
        rad = math.radians(t)
        # Parabolic or elliptical arc
        bx = cx - r_mid * 0.65 + (r_mid * 0.35) * math.cos(rad)
        by = cy + (r_mid * 0.85) * math.sin(rad)
        bow_pts.append((bx, by))
    
    for i in range(len(bow_pts) - 1):
        draw.line([bow_pts[i], bow_pts[i+1]], fill=(16, 185, 129, 255), width=int(6 * scale))

    # Bow string connecting tips
    tip_top = bow_pts[0]
    tip_bottom = bow_pts[-1]
    draw.line([tip_top, tip_bottom], fill=(56, 189, 248, 160), width=int(2 * scale))

    # Inner Radar Ring
    draw.ellipse(
        [cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner],
        outline=(56, 189, 248, 200),
        width=int(2.5 * scale),
    )

    # Tactical Arrow / Precision Bolt (Pointing towards the right, locked on target)
    arrow_y = cy
    arrow_x_tail = cx - r_mid * 0.5
    arrow_x_head = cx + r_mid * 0.85

    # Shaft
    draw.line(
        [(arrow_x_tail, arrow_y), (arrow_x_head, arrow_y)],
        fill=(56, 189, 248, 255),
        width=int(5 * scale),
    )

    # Arrow Head (Polygon)
    head_len = 28 * scale
    head_w = 16 * scale
    p_tip = (arrow_x_head + head_len, arrow_y)
    p_top = (arrow_x_head, arrow_y - head_w)
    p_notch = (arrow_x_head + head_len * 0.3, arrow_y)
    p_bot = (arrow_x_head, arrow_y + head_w)

    draw.polygon([p_tip, p_top, p_notch, p_bot], fill=(16, 185, 129, 255))

    # Arrow Fletching
    fletch_len = 14 * scale
    fletch_w = 10 * scale
    draw.line([(arrow_x_tail, arrow_y), (arrow_x_tail - fletch_len, arrow_y - fletch_w)], fill=(56, 189, 248, 240), width=int(3 * scale))
    draw.line([(arrow_x_tail, arrow_y), (arrow_x_tail - fletch_len, arrow_y + fletch_w)], fill=(56, 189, 248, 240), width=int(3 * scale))
    draw.line([(arrow_x_tail + 8*scale, arrow_y), (arrow_x_tail - fletch_len + 8*scale, arrow_y - fletch_w)], fill=(56, 189, 248, 240), width=int(3 * scale))
    draw.line([(arrow_x_tail + 8*scale, arrow_y), (arrow_x_tail - fletch_len + 8*scale, arrow_y + fletch_w)], fill=(56, 189, 248, 240), width=int(3 * scale))

    # Center Reticle Glow Core
    core_r = 12 * scale
    draw.ellipse(
        [cx - core_r, cy - core_r, cx + core_r, cy + core_r],
        fill=(16, 185, 129, 220),
    )
    inner_dot = 5 * scale
    draw.ellipse(
        [cx - inner_dot, cy - inner_dot, cx + inner_dot, cy + inner_dot],
        fill=(255, 255, 255, 255),
    )

    # Downsample with LANCZOS for high quality
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_img


def main():
    print("Generating Meme Hunter institutional icons & favicons...")
    master_512 = create_meme_hunter_icon(512)
    master_256 = create_meme_hunter_icon(256)
    master_180 = create_meme_hunter_icon(180)
    master_64 = create_meme_hunter_icon(64)
    master_48 = create_meme_hunter_icon(48)
    master_32 = create_meme_hunter_icon(32)
    master_16 = create_meme_hunter_icon(16)

    # 1. Public Favicon ICO (Multi-resolution)
    ico_path = "web/frequi/public/favicon.ico"
    master_256.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Saved: {ico_path}")

    # 2. Public PNG favicons
    png_fav = "web/frequi/public/favicon.png"
    master_256.save(png_fav, format="PNG")
    print(f"Saved: {png_fav}")

    apple_fav = "web/frequi/public/apple-touch-icon.png"
    master_180.save(apple_fav, format="PNG")
    print(f"Saved: {apple_fav}")

    # 3. Assets
    asset_logo = "web/frequi/src/assets/meme-hunter-logo.png"
    master_512.save(asset_logo, format="PNG")
    print(f"Saved: {asset_logo}")

    # Overwrite legacy asset logos so nothing breaks
    master_512.save("web/frequi/src/assets/freqtrade-logo.png", format="PNG")
    master_512.save("web/frequi/src/assets/freqtrade-logo-mask.png", format="PNG")
    print("Updated legacy asset logos with Meme Hunter artwork.")


if __name__ == "__main__":
    main()
