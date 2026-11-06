import datetime
import json
import os
import urllib.request
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import visuals as V
from athlete import idmanci_tap

STATE_FILE = "telegram_state.json"
W = H = 1080
DAILY_LIMIT = 40

# 40 ayrı mövzu. Hər gün indekslər tarixə görə dəyişir; eyni gündə təkrar seçilmir.
TOPICS = [
    ("VAR otağında", "Hakim: Oyunu davam etdirin.", "Azarkeş: Mən artıq 4 dəfə təkrar baxmışam!", "VAR və mübahisəli qərarlar"),
    ("Qapıçı səhv edəndə", "Məşqçi: Sadə oynayın.", "Qapıçı: Mən oyuna bir az həyəcan qatdım.", "Qapıçı səhvləri"),
    ("Transfer pəncərəsi", "Klub: Büdcəmiz hazırdır.", "Azarkeş: Bəs transferlər haradadır?", "Transfer gözləntiləri"),
    ("90+ dəqiqə", "Hakim: 4 dəqiqə əlavə vaxt.", "Azarkeş: Bu 4 dəqiqə niyə 40 dəqiqədir?", "Əlavə vaxt həyəcanı"),
    ("Penalti anı", "Mən: Sakitəm, problem yoxdur.", "Top penalti nöqtəsinə qoyulanda: Dua başlayır.", "Penalti həyəcanı"),
    ("Derbi günü", "Dostum: Bu sadəcə oyundur.", "Mən: Bu gün dostluq fasilədədir.", "Derbi rəqabəti"),
    ("Favorit komanda uduzanda", "Matçdan əvvəl: Bu dəfə rahat qələbə.", "Matçdan sonra: Hakim, meydança, hava...", "Məğlubiyyətdən sonra bəhanələr"),
    ("Ofsayd", "Hücumçu: Mən vaxtında qaçdım.", "Yan xətt hakimi: Bir az da səbirli olaydın.", "Ofsayd qərarları"),
    ("Boş qapı", "Azarkeş: Bunu vurmaq daha asandır.", "Futbolçu: Çətinliyi sevirəm.", "Qaçırılan qol fürsətləri"),
    ("Məşqçinin əvəzetməsi", "Mən: İndi hücumçu çıxaracaq.", "Məşqçi: Müdafiəçi meydana.", "Əvəzetmə qərarları"),
    ("Qarabağ oyunu", "Mən: Bu gün sakit izləyəcəyəm.", "Qarabağ hücuma keçəndə: Hamı ayağa!", "Qarabağ azarkeşliyi"),
    ("Milli komanda", "Mən: Bu dəfə qrupdan çıxırıq.", "Ümid: Həmişə sonuncu tərk edir.", "Milli komanda ümidləri"),
    ("Fantaziya futbolu", "Real həyatda: Ehtiyat oyunçudur.", "Mənim fantaziya komandamda: Kapitan!", "Fantaziya futbolu"),
    ("Futbol statistikası", "Dostum: Komandanız çox qol vurub?", "Mən: Topa sahib olma faizimizə bax!", "Statistika mübahisələri"),
    ("Məşq günü", "Məşqçi: Yüngül məşq edəcəyik.", "Məşqin sonunda: Sabah pilləkənlə düşə bilməyəcəyik.", "Məşq yükü"),
    ("Qış transferi", "Klub: Bir neçə variantımız var.", "Azarkeş: Təqdimat videosunu artıq seçmişəm.", "Qış transfer pəncərəsi"),
    ("Qırmızı vərəqə", "Hakim: Meydanı tərk edin.", "Futbolçu: Mən sadəcə salamlaşırdım.", "Qırmızı vərəqələr"),
    ("Künc zərbəsi", "Azarkeş: Bu dəfə qol gəlir.", "Top: Birbaşa tribunaya.", "Standart vəziyyətlər"),
    ("Qol sevinci", "Futbolçu: Sakit qalacağam.", "Komanda yoldaşları: Üstünə hamı!", "Qol sevincləri"),
    ("Məğlubiyyətdən sonra", "Mən: Bu oyuna baxmayacağam.", "Növbəti matç başlayanda: Yenə buradayam.", "Azarkeş sədaqəti"),
    ("Çempionlar Liqası gecəsi", "Saat: 23:00.", "Mən: Sabah iş var... amma bu oyun da var.", "Avropa futbolu gecələri"),
    ("Qapıya zərbə", "Şərhçi: Təhlükəli zərbə!", "Top: Stadionun damı ilə tanış olun.", "Dəqiqlik problemi"),
    ("Müdafiə xətti", "Məşqçi: Xətti qoruyun.", "Müdafiəçi: Hansı xətti?", "Müdafiə səhvləri"),
    ("Qış fasiləsi", "Azarkeş: Futbol üçün darıxmışam.", "Təqvim: Hələ bir neçə həftə var.", "Futbolsuz günlər"),
    ("Matç bileti", "Mən: Bir bilet kifayətdir.", "Dostlar: Biz də gəlirik!", "Stadiona getmək"),
    ("Hakim fit çalanda", "Mən: Hələ bir hücum da olsun.", "Hakim: Matç bitdi.", "Matçın son fitindən sonra"),
    ("Yeni forma", "Klub: Yeni forma satışda!", "Azarkeş: Əvvəlki formanın borcu hələ bitməyib.", "Klub formaları"),
    ("Qol təkrarı", "Mən: Bir dəfə baxdım, kifayətdir.", "Mən 5 dəqiqə sonra: Bir də göstər!", "Qol təkrarları"),
    ("Qapı dirəyi", "Hücumçu: Qol vurduğumu düşündüm.", "Dirək: Bu gün yox.", "Dirəyə dəyən zərbələr"),
    ("Mətbuat konfransı", "Jurnalist: Niyə uduzdunuz?", "Məşqçi: Növbəti suala keçək.", "Mətbuat konfransları"),
    ("Azarkeş proqnozu", "Matçdan əvvəl: 3:0 udacağıq.", "Matçdan sonra: Əsas odur ki, ruhdan düşməyək.", "Hesab proqnozları"),
    ("Futbol tətbiqləri", "Mən: Telefonu kənara qoyuram.", "Bildiriş: Komandanız qol buraxdı.", "Canlı hesab bildirişləri"),
    ("Penalti seriyası", "Qapıçı: Hansı tərəfə atacaq?", "Mən ekran qarşısında: Mən də bilmək istəyirəm!", "Penalti seriyası"),
    ("Yeni baş məşqçi", "Klub: Yeni dövr başlayır.", "Azarkeş: İlk 3 oyunda səbr edəcəyik.", "Baş məşqçi dəyişikliyi"),
    ("Qol vurmayanda", "Şərhçi: Komanda təzyiq edir.", "Azarkeş: Təzyiq yox, qol lazımdır.", "Qol çatışmazlığı"),
    ("Futbol mübahisəsi", "Dostum: Mənim komandam daha güclüdür.", "Mən: Gəl, bunu 90 dəqiqə danışaq.", "Azarkeş mübahisələri"),
    ("Son dəqiqə qolu", "Mən: Artıq heç nə dəyişməz.", "Komanda: Hələ fit çalınmayıb!", "Son dəqiqə qolları"),
    ("Ehtiyat oyunçular skamyası", "Futbolçu: Hazıram, məşqçi!", "Məşqçi: Bir azdan... (80-ci dəqiqə)", "Ehtiyat oyunçular"),
    ("Matçdan sonrakı analiz", "Mən: Oyunu analiz edəcəyəm.", "Mən 2 dəqiqə sonra: Sadəcə qələbə lazım idi.", "Matç analizi"),
]

PALETTES = [
    ("#101827", "#36D399", "#25364B", "#174B3B", "#FFFFFF", "#B8C7D9"),
    ("#241332", "#F7B267", "#49305E", "#713F5B", "#FFFFFF", "#E8DDF0"),
    ("#142D3B", "#55C1FF", "#254B5C", "#1D5960", "#FFFFFF", "#C7DCE8"),
    ("#302018", "#FFC857", "#59402B", "#714A2C", "#FFF8E8", "#E7D2B5"),
    ("#202020", "#FF6B6B", "#3B3B3B", "#5A3030", "#FFFFFF", "#D0D0D0"),
    ("#17251D", "#B8E986", "#2E4938", "#426B4C", "#FFFFFF", "#D2E2D4"),
]


def font(size, bold=True):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for path in candidates:
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


def centered(draw, text, y, f, color, max_width=850):
    lines = wrap(draw, text, f, max_width)
    line_height = f.size + 16
    for line in lines:
        box = draw.textbbox((0, 0), line, font=f)
        x = (W - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=f, fill=color)
        y += line_height


def centered_v(draw, text, top, height, f, color, max_width=850):
    """Mətni kartın şaquli mərkəzində yerləşdirir."""
    n = len(wrap(draw, text, f, max_width))
    block = n * (f.size + 16) - 16
    centered(draw, text, top + (height - block) // 2 - 4, f, color, max_width)


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"initialized": False, "news": [], "fixtures": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        print("Xəbərdarlıq: telegram_state.json oxunmadı; yeni vəziyyət yaradılır.")
        return {"initialized": False, "news": [], "fixtures": {}}


def select_topic(now, state):
    day = now.strftime("%Y-%m-%d")
    sent = state.setdefault("meme_daily", {})
    used = sent.setdefault(day, [])
    # Tarixə görə başlanğıc nöqtəsi dəyişir; gün ərzində mövzu təkrarlanmır.
    start = now.date().toordinal() % len(TOPICS)
    for offset in range(len(TOPICS)):
        idx = (start + offset) % len(TOPICS)
        if idx not in used:
            return idx, TOPICS[idx]
    return None, None


def make_meme(top, middle, bottom, footer, index=0, day_seed=0, idmanci=None):
    """Rəngli futbol memi. idmanci verilərsə, xəbərdəki futbolçunun portreti əlavə olunur."""
    n = index + day_seed
    top_c, bot_c, accent = V.SCHEMES[n % len(V.SCHEMES)]
    dark = (10, 20, 60)
    on_accent = dark if accent != (255, 255, 255) else top_c
    img = V.fast_gradient((W, H), top_c, bot_c)
    V.confetti(img, [V.YELLOW, V.PINK, V.BLUE, (255, 255, 255)], seed=n, count=36)
    draw = ImageDraw.Draw(img)
    V.tricolor(draw, 0, W, 18)
    V.tricolor(draw, H - 18, W, 18)

    # Başlıq zolağı
    draw.rounded_rectangle((40, 46, 330, 116), radius=35, fill=(255, 255, 255))
    draw.text((68, 58), "FUTBOL AZ", font=font(38), fill=top_c)
    V.pill(draw, (W - 330, 48), f"MEM  {index + 1:02d}/40", accent, on_accent, font(26))

    portrait_h = 0
    if idmanci:
        ad, portret, _ = idmanci
        ring = V.circle_portrait(V.boost(portret), 250, ring=accent, ring_w=12)
        img.paste(ring, (W // 2 - ring.width // 2, 140), ring)
        draw = ImageDraw.Draw(img)
        nf = font(26)
        nw = draw.textbbox((0, 0), ad.upper(), font=nf)[2]
        draw.rounded_rectangle((W // 2 - nw // 2 - 24, 408, W // 2 + nw // 2 + 24, 452), radius=22, fill=accent)
        draw.text((W // 2 - nw // 2, 413), ad.upper(), font=nf, fill=on_accent)
        portrait_h = 320
    else:
        V.ball(draw, W // 2, 215, 80, patch=top_c)
        portrait_h = 160

    y0 = 140 + portrait_h
    # Üç rəngli kart: mövzu / ilk sətir / ikinci sətir
    draw.rounded_rectangle((60, y0, W - 60, y0 + 140), radius=36, fill=accent)
    centered_v(draw, top, y0, 140, font(46), on_accent, 880)
    draw.rounded_rectangle((60, y0 + 160, W - 60, y0 + 330), radius=36, fill=(255, 255, 255))
    centered_v(draw, middle, y0 + 160, 170, font(36), dark, 840)
    draw.rounded_rectangle((60, y0 + 350, W - 60, y0 + 520), radius=36, fill=dark)
    centered_v(draw, bottom, y0 + 350, 170, font(36), (255, 255, 255), 840)

    draw.text((70, H - 70), str(footer)[:50], font=font(21, False), fill=(255, 255, 255))
    draw.text((W - 270, H - 72), "@FUTBOLAZ", font=font(24), fill=accent)
    return img


def send_photo(img, caption):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    admin_id = os.environ.get("TELEGRAM_ADMIN_ID", "").strip()
    if not token or not admin_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN və ya TELEGRAM_ADMIN_ID tapılmadı")

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90, optimize=True)
    boundary = "----FutbolAzBoundary7MA4YWxkTrZu0gW"
    keyboard = {"inline_keyboard": [[
        {"text": "✅ Paylaş", "callback_data": "share"},
        {"text": "❌ Ləğv et", "callback_data": "cancel"}
    ]]}

    body = bytearray()
    fields = [
        ("chat_id", admin_id),
        ("caption", caption[:900]),
        ("reply_markup", json.dumps(keyboard, ensure_ascii=False))
    ]
    for name, value in fields:
        body.extend(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode("utf-8")
        )
    body.extend(
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="photo"; filename="futbolaz_meme.jpg"\r\n'
        "Content-Type: image/jpeg\r\n\r\n".encode()
    )
    body.extend(buf.getvalue())
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Telegram şəkil xətası: {result}")
    print("Mem şəxsi Telegram-a təsdiq üçün göndərildi.")
    return result


def avtomatik_mem_paylas(matclar, xeberler, now):
    state = load_state()
    today = now.strftime("%Y-%m-%d")
    test_mode = os.environ.get("TELEGRAM_MEME_TEST") == "1"

    used = state.setdefault("meme_daily", {}).setdefault(today, [])
    if not test_mode and len(used) >= DAILY_LIMIT:
        print("Bu gün üçün 40 mem limiti tamamlanıb.")
        return

    idx, topic = select_topic(now, state)
    if topic is None:
        print("Bu gün üçün fərqli mövzu qalmayıb.")
        return

    top, middle, bottom, footer = topic
    # Mövcud matç/xəbər məlumatı varsa, mövzunu fakt uydurmadan kontekstə bağla.
    if "qarabağ" in top.lower():
        qarabag_game = next(
            (m for m in matclar
             if "qarabağ" in (
                 m.get("teams", {}).get("home", {}).get("name", "") + " " +
                 m.get("teams", {}).get("away", {}).get("name", "")
             ).lower()),
            None
        )
        if qarabag_game:
            home = qarabag_game.get("teams", {}).get("home", {}).get("name", "")
            away = qarabag_game.get("teams", {}).get("away", {}).get("name", "")
            footer = f"{home} – {away}"

    day_seed = now.date().toordinal()
    # Son xəbərlərdə adı keçən futbolçu/idmançı varsa, memə onun portreti əlavə olunur.
    idmanci = None
    for item in (xeberler or [])[:3]:
        try:
            idmanci = idmanci_tap(item[1])
        except Exception as e:
            print("Mem üçün idmançı fotosu tapılmadı:", e)
        if idmanci:
            break
    img = make_meme(top, middle, bottom, footer, idx, day_seed, idmanci)
    caption = f"😂 {top}\n\n{middle}\n{bottom}\n\n⚽ @futbolaz_official"
    result = send_photo(img, caption)

    if not test_mode:
        used.append(idx)
        cutoff = (now.date() - datetime.timedelta(days=14)).isoformat()
        state["meme_daily"] = {
            day: indexes for day, indexes in state["meme_daily"].items()
            if day >= cutoff
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"Futbol AZ memi təsdiq üçün göndərildi: mövzu {idx + 1}/40")
