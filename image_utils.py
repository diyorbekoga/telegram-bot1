from PIL import Image, ImageDraw, ImageFont


def add_warning_text(input_path, output_path, text="3 MARTA KECH QOLGAN!"):
    img = Image.open(input_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    font_size = max(40, w // 15)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding = 20
    draw.rectangle([(0, 0), (w, text_h + padding * 2)], fill=(220, 0, 0))
    draw.text(((w - text_w) // 2, padding), text, fill=(255, 255, 255), font=font)

    img.save(output_path, quality=95)