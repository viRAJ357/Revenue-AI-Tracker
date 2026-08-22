import os, math
from PIL import Image, ImageDraw, ImageFont

W, H = 900, 500
FPS = 30
TOTAL_FRAMES = 180

BG     = (13,  17,  23)
WHITE  = (201, 209, 217)
DIM    = (48,  54,  61)

STEPS = [
    ("01", "Project Setup",         (88,  166, 255)),
    ("02", "Data Ingestion",        (63,  185, 180)),
    ("03", "Preprocessing",         (63,  185, 180)),
    ("04", "EDA",                   (47,  160,  87)),
    ("05", "Feature Engineering",   (47,  160,  87)),
    ("06", "AI Model Training",     (229, 192,  89)),
    ("07", "Model Evaluation",      (229, 192,  89)),
    ("08", "Revenue Prediction API",(248, 102, 102)),
    ("09", "Dashboard",             (188, 140, 255)),
    ("10", "Deployment",            (248, 102, 102)),
]

def load_font(size):
    for name in ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except:
            pass
    return ImageFont.load_default()

font_title = load_font(30)
font_step  = load_font(15)
font_num   = load_font(13)

def ease_out(t):
    return 1 - (1 - max(0, min(1, t))) ** 3

def node_pos(i):
    t = i / (len(STEPS) - 1)
    x = 70 + t * (W - 140)
    y = H // 2 + math.sin(t * math.pi * 1.5) * -110
    return (int(x), int(y))

positions = [node_pos(i) for i in range(len(STEPS))]
NODE_R = 20
frames = []

for f in range(TOTAL_FRAMES):
    img  = Image.new("RGBA", (W, H), BG + (255,))
    draw = ImageDraw.Draw(img, "RGBA")

    # grid dots
    for gx in range(0, W, 40):
        for gy in range(0, H, 40):
            draw.rectangle([gx, gy, gx+1, gy+1], fill=(30, 40, 50, 100))

    # title pulse
    pulse = int(180 + 75 * math.sin(f * 0.1))
    draw.text((30, 16), "Revenue AI Tracker — Data Flow", font=font_title,
              fill=(pulse, 200, 100, 255))
    draw.text((30, 52), "github.com/viRAJ357/Revenue-AI-Tracker", font=font_num,
              fill=DIM + (200,))

    APPEAR = 18
    for i in range(len(STEPS) - 1):
        edge_t = ease_out((f - APPEAR - i * 10 - 8) / 16.0)
        if edge_t <= 0:
            continue
        x1, y1 = positions[i]
        x2, y2 = positions[i + 1]
        ex = int(x1 + (x2 - x1) * edge_t)
        ey = int(y1 + (y2 - y1) * edge_t)
        draw.line([(x1, y1), (ex, ey)], fill=DIM + (180,), width=2)
        # flowing particle
        if edge_t >= 1.0:
            pt = (f % 28) / 28.0
            px = int(x1 + (x2 - x1) * pt)
            py = int(y1 + (y2 - y1) * pt)
            draw.ellipse([px-4, py-4, px+4, py+4], fill=(47, 160, 87, 200))

    for i, (num, label, color) in enumerate(STEPS):
        nt = ease_out((f - APPEAR - i * 10) / 16.0)
        if nt <= 0:
            continue
        x, y = positions[i]
        r = int(NODE_R * nt)
        a = int(255 * nt)
        pulse_r = r + int(4 * math.sin(f * 0.18 + i))
        draw.ellipse([x-pulse_r-4, y-pulse_r-4, x+pulse_r+4, y+pulse_r+4],
                     fill=color + (25,))
        draw.ellipse([x-pulse_r, y-pulse_r, x+pulse_r, y+pulse_r],
                     outline=color + (a,), width=2)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=color + (a,))
        draw.text((x-7, y-6), num, font=font_num, fill=BG + (a,))

        bb = draw.textbbox((0, 0), label, font=font_step)
        lw = bb[2] - bb[0]
        lx, ly = x - lw // 2, (y + r + 6) if i % 2 == 0 else (y - r - 22)
        draw.rounded_rectangle([lx-5, ly-2, lx+lw+5, ly+18], radius=4,
                                fill=(22, 27, 34, int(200*nt)),
                                outline=color + (int(110*nt),), width=1)
        draw.text((lx, ly), label, font=font_step, fill=WHITE + (a,))

    frames.append(img.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=128))

out = r"C:\Users\nikhi\OneDrive\Desktop\TOCPRACTICAL\Revenue-AI-Tracker\assets\flow_animation.gif"
os.makedirs(os.path.dirname(out), exist_ok=True)
frames[0].save(out, save_all=True, append_images=frames[1:],
               loop=0, duration=int(1000/FPS), optimize=True)
print(f"Done: {out}  ({len(frames)} frames, {os.path.getsize(out)//1024} KB)")
