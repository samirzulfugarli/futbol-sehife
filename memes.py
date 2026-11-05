import datetime
import json
import os
import urllib.request
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

STATE_FILE = "telegram_state.json"
SLOTS = {12: "gunorta", 20: "axsam"}
W = H = 1080


def font(size, bold=True):
    path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap(draw, text, f, max_width):
    lines, line = [], ""
    for word in str(text).split():
        test = (line + " " + word).strip()
        if draw.textbbox((0, 0), test, font=f)[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def centered(draw, text, y, f, color, max_width=800):
    lines = wrap(draw, text, f, max_width)
    for line in lines:
        box = draw.textbbox((0, 0), line, font=f)
        x = (W - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=f, fill=color)
        y += f.size + 18


def meme_text(matclar, xeberler, slot):
    finished = []
    qarabag = []
    allowed = {419, 420, 418, 2, 3, 848, 39, 40, 45, 48, 140, 135, 78, 61, 203, 94, 88}
    for m in matclar:
        if m.get("league", {}).get("id") not in allowed:
            continue
        home = m.get("teams", {}).get("home", {}).get("name", "")
        away = m.get("teams", {}).get("away", {}).get("name", "")
        goals = m.get("goals", {})
        status = m.get("fixture", {}).get("status", {}).get("short", "")
        if "qarabağ" in (home + " " + away).lower():
            qarabag.append((home, away, status))
        if status in ("FT", "AET", "PEN") and goals.get("home") is not None:
            finished.append((home, away, goals, m.get("league", {}).get("name", "")))

    if finished:
        home, away, goals, league = finished[-1]
        score = f'{home}  {goals["home"]}:{goals["away"]}  {away}'
        if goals["home"] == goals["away"]:
            return "HEÇ-HEÇƏDƏN SONRA", score, "Heç kim sevinmir, heç kim də razı deyil.", league
        winner = home if goals["home"] > goals["away"] else away
        return "QƏLƏBƏDƏN SONRA", score, f"{winner} azarkeşləri: Bu gecə yatmaq yoxdur!", league

    if qarabag:
        home, away, status = qarabag[0]
        if status in ("NS", "TBD"):
            return "QARABAĞ OYUNA ÇIXANDA", "Mən: Sakit izləyəcəyəm.", "Hər təhlükəli hücumda: Ayağa qalx!", f"{home} – {away}"
        return "QARABAĞ MATÇI GEDƏNDƏ", "Mən: Sakit olacağam.", "Ürəyim: 90 dəqiqəlik sprint!", f"{home} – {away}"

    if xeberler and "transfer" in xeberler[0][1].lower():
        return "TRANSFER XƏBƏRLƏRİ", "Klub: Büdcəmiz məhduddur.", "Azarkeş: Bəs 3 ulduz futbolçu alsaq?", "Futbol gündəmi"

    if slot == "gunorta":
        return "MƏN: BU GÜN FUTBOL YOXDUR", "Saat 12:00 — sakit gün planı", "Saat 12:05 — nəticələrə bir baxım...", "Futbol sevgisi belə bir şeydir"
    return "MƏN: BU GÜN TEZ YATACAĞAM", "Saat 20:00 — telefonu kənara qoyuram", "Saat 20:01 — görəsən hesab neçə-neçədir?", "Futbol sevgisi belə bir şeydir"


def make_meme(top, middle, bottom, footer):
    img = Image.new("RGB", (W, H), "#101827")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((45, 45, 1035, 1035), radius=40, outline="#36D399", width=7)
    draw.text((85, 85), "FUTBOL AZ", font=font(42), fill="#36D399")
    draw.text((85, 150), "FUTBOL MEMİ", font=font(25, False), fill="#B8C7D9")
    centered(draw, top, 255, font(52), "#FFFFFF", 900)
    draw.rounded_rectangle((95, 425, 985, 650), radius=28, fill="#25364B")
    centered(draw, middle, 495, font(40), "#FFFFFF", 800)
    draw.rounded_rectangle((95, 690, 985, 900), radius=28, fill="#174B3B")
    centered(draw, bottom, 755, font(40), "#FFFFFF", 800)
    draw.text((85, 955), str(footer)[:65], font=font(22, False), fill="#B8C7D9")
    draw.text((830, 955), "@FUTBOLAZ", font=font(22), fill="#36D399")
    return img


def send_photo(img, caption):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("Telegram token və ya chat ID tapılmadı")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90, optimize=True)
    boundary = "----FutbolAzBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    for name, value in (("chat_id", chat_id), ("caption", caption[:900])):
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode("utf-8"))
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"futbolaz_meme.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode())
    body.extend(buf.getvalue())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto", data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Telegram şəkil xətası: {result}")


def avtomatik_mem_paylas(matclar, xeberler, now):
    slot = SLOTS.get(now.hour)
    if not slot:
        return
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {"initialized": False, "news": [], "fixtures": {}}
    posted = state.setdefault("meme_slots", {})
    today = now.strftime("%Y-%m-%d")
    if slot in posted.get(today, []):
        print(f"{slot} memi artıq paylaşılıb.")
        return
    top, middle, bottom, footer = meme_text(matclar, xeberler, slot)
    img = make_meme(top, middle, bottom, footer)
    caption = f"😂 {top}\n\n{middle}\n{bottom}\n\n⚽ @futbolaz_official"
    send_photo(img, caption)
    posted.setdefault(today, []).append(slot)
    cutoff = (now.date() - datetime.timedelta(days=14)).isoformat()
    state["meme_slots"] = {day: slots for day, slots in posted.items() if day >= cutoff}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"Futbol AZ memi Telegram-a göndərildi: {slot}")
