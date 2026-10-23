from PIL import Image, ImageDraw

def create_cctv_icon(filepath="cctv_icon.ico"):
    # Buat image RGBA 256x256
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle (Dark slate blue gradient look)
    draw.ellipse([10, 10, 246, 246], fill="#1e293b", outline="#3b82f6", width=8)

    # CCTV Body (Camera Base)
    draw.rounded_rectangle([70, 90, 186, 150], radius=15, fill="#e2e8f0", outline="#0f172a", width=4)
    
    # CCTV Lens Mount & Lens
    draw.polygon([(65, 120), (35, 95), (35, 145)], fill="#ef4444", outline="#b91c1c", width=3)
    draw.ellipse([155, 100, 175, 140], fill="#0f172a")
    draw.ellipse([160, 110, 170, 130], fill="#38bdf8")

    # Stand / Mount Bracket
    draw.rectangle([120, 150, 136, 190], fill="#94a3b8")
    draw.rectangle([100, 185, 156, 200], fill="#64748b")

    # Recording LED Dot
    draw.ellipse([175, 75, 195, 95], fill="#ef4444")

    # Simpan sebagai ICO
    img.save(filepath, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print(f"Icon dibuat: {filepath}")

if __name__ == "__main__":
    create_cctv_icon()
