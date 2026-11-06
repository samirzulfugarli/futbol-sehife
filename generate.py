import datetime
import email.utils
import html
import json
import os
import re
import time
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from memes import avtomatik_mem_paylas
import visuals as V
from athlete import idmanci_tap

API_KEY = os.environ["API_FOOTBALL_KEY"].strip()
print("Acar uzunlugu:", len(API_KEY))
BASE = "https://v3.football.api-sports.io"
BAKU = datetime.timezone(datetime.timedelta(hours=4))
KANAL = "https://t.me/futbolaz_official"
SORGULAR = ["Premyer Liqa futbol", "Qarabağ futbol"]

LIQALAR = {
    419: "Premyer Liqa",
    420: "Azərbaycan Kuboku",
    418: "Birinci Liqa",
    2: "Çempionlar Liqası",
    3: "Avropa Liqası",
    848: "Konfrans Liqası",
    39: "İngiltərə Premyer Liqası",
    40: "Championship",
    45: "FA Kuboku",
    48: "Liqa Kuboku",
    140: "La Liqa",
    135: "Serie A",
    78: "Bundesliqa",
    61: "Liqa 1",
    203: "Türkiyə Süper Liqası",
    94: "Portuqaliya Liqası",
    88: "Niderland Liqası",
}

SOZLER = [
    "futbol", "qol", "matç", "oyun", "liqa", "komanda", "kubok",
    "çempion", "transfer", "məşqçi", "qarabağ", "neftçi", "sabah",
    "zirə", "sumqayıt", "qəbələ", "məğlub", "qalib", "heç-heçə",
    "yığma", "milli", "uefa", "affa", "premyer liqa",
    "real madrid", "barcelona", "liverpool", "arsenal",
    "manchester city", "champions league", "avropa liqası",
    "çempionlar liqası", "fənərbaxça", "qalatasaray",
    "besiktas", "futbolçu", "baş məşqçi", "stadion",
]

STATUS_AD = {
    "1H": "1-ci hissə", "HT": "fasilə", "2H": "2-ci hissə",
    "ET": "əlavə vaxt", "BT": "əlavə vaxt arası", "P": "penalti seriyası",
    "FT": "bitdi", "AET": "əlavə vaxtdan sonra", "PEN": "penaltilərlə",
    "LIVE": "canlı", "SUSP": "dayandırılıb", "INT": "dayandırılıb",
    "PST": "təxirə salınıb", "CANC": "ləğv olunub", "ABD": "yarımçıq qalıb",
}


def get(url, headers=None):
    h = {"User-Agent": "Mozilla/5.0"}
    h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        print("HTTP xetasi:", e.code, e.read()[:300])
        raise


def matclar_cek(now):
    gunler = [now.date(), now.date() + datetime.timedelta(days=1)]
    hamisi = []
    for g in gunler:
        url = f"{BASE}/fixtures?date={g.isoformat()}&timezone=Asia/Baku"
        data = json.loads(get(url, {"x-apisports-key": API_KEY}))
        if data.get("errors"):
            raise SystemExit(f"API xetasi: {data['errors']}")
        hamisi += data.get("response", [])
    return hamisi


def gunun_penceresi(now):
    bas = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if now < bas:
        bas -= datetime.timedelta(days=1)
    return bas.timestamp(), (bas + datetime.timedelta(days=1)).timestamp()


def hesab(x):
    return "-" if x is None else str(x)


def matc_html(m):
    f = m["fixture"]
    st = f["status"]["short"]
    ev = html.escape(m["teams"]["home"]["name"])
    qon = html.escape(m["teams"]["away"]["name"])
    if st in ("NS", "TBD"):
        orta = f'<span class="saat">{f["date"][11:16]}</span>'
        durum = ""
    else:
        g = m["goals"]
        orta = f'<span class="hesab">{hesab(g["home"])} : {hesab(g["away"])}</span>'
        durum = STATUS_AD.get(st, st)
    return (
        f'<li><span class="ev">{ev}</span>{orta}<span class="qon">{qon}</span>'
        f'<span class="durum">{html.escape(durum)}</span></li>'
    )


def matclar_html(matclar, now):
    bas, son = gunun_penceresi(now)
    qruplar = {}
    for m in matclar:
        lid = m["league"]["id"]
        if lid in LIQALAR and bas <= m["fixture"]["timestamp"] < son:
            qruplar.setdefault(lid, []).append(m)
    if not qruplar:
        return "<p>Bu gün seçilmiş liqalarda matç yoxdur.</p>"
    cixis = []
    for lid, ad in LIQALAR.items():
        if lid not in qruplar:
            continue
        cixis.append(f"<h3>{html.escape(ad)}</h3><ul>")
        for m in sorted(qruplar[lid], key=lambda x: x["fixture"]["timestamp"]):
            cixis.append(matc_html(m))
        cixis.append("</ul>")
    return "\n".join(cixis)



def rss_sekli_tap(item):
    """RSS-dən foto, başlıq və qısa təsvir məlumatlarını çıxarır."""
    for element in item.iter():
        tag = element.tag.lower() if isinstance(element.tag, str) else ""
        if tag.endswith("}thumbnail") or tag.endswith("}content") or tag == "enclosure":
            url = element.attrib.get("url", "").strip()
            tip = element.attrib.get("type", "").lower()
            if url.startswith("https://") and (not tip or tip.startswith("image/")):
                return url
    description = item.findtext("description") or ""
    match = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"']", description, re.I)
    if match:
        url = html.unescape(match.group(1))
        if url.startswith("https://"):
            return url
    return ""


def rss_metn_tap(item):
    description = item.findtext("description") or ""
    description = html.unescape(re.sub(r"<[^>]+>", " ", description))
    description = re.sub(r"\s+", " ", description).strip()
    return description[:500]


def sehife_sekli_tap(link):
    """RSS fotosu yoxdursa, məqalənin og:image/twitter:image fotosunu axtarır."""
    try:
        page = get(link, {"User-Agent": "Mozilla/5.0 (compatible; FutbolAZ/1.0)"}).decode("utf-8", "ignore")
        for pattern in (
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
        ):
            m = re.search(pattern, page, re.I)
            if m:
                image_url = html.unescape(m.group(1)).strip()
                if image_url.startswith("https://"):
                    return image_url
    except Exception as e:
        print("Məqalə fotosu tapılmadı:", e)
    return ""


def sekli_yukle(url):
    if not url:
        return None
    try:
        raw = get(url, {"User-Agent": "Mozilla/5.0", "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"})
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        if image.width < 320 or image.height < 180:
            return None
        return image
    except Exception as e:
        print("Xəbər fotosu yüklənmədi:", e)
        return None


def font_tap(size, bold=False):
    namiz = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in namiz:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def metni_sətirlərə_böl(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def futbolaz_xeber_qrafikasi(basliq, menbe, foto, idmanci=None, sema=0):
    """1080x1080 rəngli Futbol AZ xəbər kartı.

    foto    – xəbər fotosu (və ya None)
    idmanci – (ad, PIL şəkil, təsvir): xəbərdə adı çəkilən futbolçu/idmançı
    sema    – rəng sxemi indeksi (hər xəbər fərqli rəngdə olsun)
    """
    W = H = 1080
    top_c, bot_c, accent = V.SCHEMES[sema % len(V.SCHEMES)]
    PH = 700  # foto hissəsinin hündürlüyü

    canvas = V.fast_gradient((W, H), top_c, bot_c)
    d = ImageDraw.Draw(canvas)

    if idmanci:
        # Rəngli fon üzərində iri futbolçu portreti: topla və konfettilə canlandırılır.
        ad, portret, _ = idmanci
        V.confetti(canvas, [V.YELLOW, V.PINK, V.BLUE, (255, 255, 255)], seed=sema + 3, region=(0, 130, W, PH), count=30)
        d = ImageDraw.Draw(canvas)
        V.ball(d, 900, 250, 120, patch=top_c)
        d.ellipse((60, 90, 70, 100), fill=accent)
        pw, ph = 600, PH - 120
        p = V.boost(V.cover(portret, pw, ph, focus_top=0.08))
        mask = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=44, fill=255)
        frame = Image.new("RGB", (pw + 24, ph + 24), accent)
        fm = Image.new("L", frame.size, 0)
        ImageDraw.Draw(fm).rounded_rectangle((0, 0, frame.width - 1, frame.height - 1), radius=56, fill=255)
        canvas.paste(frame, (240 - 12, 150 - 12), fm)
        canvas.paste(p, (240, 150), mask)
        d = ImageDraw.Draw(canvas)
    elif foto:
        foto = V.boost(V.cover(foto, W, PH, focus_top=0.25)).filter(ImageFilter.GaussianBlur(0.3))
        canvas.paste(foto, (0, 0))
        # Aşağıya doğru rəngli (tünd qara yox) keçid
        ov = Image.new("RGBA", (W, PH), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        for y in range(PH):
            t = max(0.0, (y - PH * 0.45) / (PH * 0.55))
            od.line((0, y, W, y), fill=bot_c + (int(235 * t),))
        canvas.paste(ov, (0, 0), ov)
        d = ImageDraw.Draw(canvas)
    else:
        # Foto yoxdursa: canlı rəngli fon, top və konfetti (saxta foto istifadə edilmir).
        V.confetti(canvas, [V.YELLOW, V.PINK, V.BLUE, (255, 255, 255)], seed=sema, region=(0, 100, W, PH), count=34)
        d = ImageDraw.Draw(canvas)
        V.ball(d, W // 2, 380, 210, patch=top_c)

    V.tricolor(d, 0, W, 16)
    d.rounded_rectangle((50, 44, 360, 118), radius=37, fill=(255, 255, 255))
    d.text((80, 58), "FUTBOL AZ", font=font_tap(40, True), fill=top_c)
    V.pill(d, (W - 330, 48), "XƏBƏR", accent, (10, 20, 60) if accent != (255, 255, 255) else top_c, font_tap(26, True))

    if idmanci:
        ad = idmanci[0]
        nf = font_tap(34, True)
        nw = d.textbbox((0, 0), ad.upper(), font=nf)[2]
        d.rounded_rectangle((60, PH - 50, 60 + nw + 56, PH + 20), radius=35, fill=accent)
        d.text((88, PH - 40), ad.upper(), font=nf, fill=(10, 20, 60) if accent != (255, 255, 255) else top_c)

    # Başlıq paneli
    d.rounded_rectangle((36, PH + 44, W - 36, H - 36), radius=40, fill=(255, 255, 255))
    d.rectangle((70, PH + 78, 190, PH + 90), fill=accent if accent != (255, 255, 255) else top_c)
    title_font = font_tap(50, True)
    lines = metni_sətirlərə_böl(d, basliq, title_font, 940)
    if len(lines) > 4:
        title_font = font_tap(42, True)
        lines = metni_sətirlərə_böl(d, basliq, title_font, 940)
    y = PH + 108
    for line in lines[:4]:
        d.text((70, y), line, font=title_font, fill=(15, 23, 60))
        y += title_font.size + 12
    d.text((70, H - 78), f"MƏNBƏ: {(menbe or 'Futbol xəbərləri')[:38]}", font=font_tap(20, True), fill=(100, 110, 140))
    d.text((W - 340, H - 78), "t.me/futbolaz_official", font=font_tap(20, True), fill=top_c)
    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=92, optimize=True)
    out.seek(0)
    return out


def telegram_xeber_onayina_gonder(basliq, menbe, link, sekil="", tesvir=""):
    """Brendli xəbər kartını adminə təsdiq üçün göndərir."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    admin_id = os.environ.get("TELEGRAM_ADMIN_ID", "").strip()
    if not token or not admin_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN və ya TELEGRAM_ADMIN_ID tapılmadı")

    keyboard = json.dumps({"inline_keyboard": [[
        {"text": "✅ Paylaş", "callback_data": "share"},
        {"text": "❌ Ləğv et", "callback_data": "cancel"}
    ]]}, ensure_ascii=False)
    caption = (
        f"⚽ {basliq}\n\n"
        + ((tesvir[:500].strip() + "\n\n") if tesvir else "")
        + f"🗞 Mənbə: {menbe or 'Mənbə göstərilməyib'}\n"
        + f"🔗 {link}\n"
        + f"📢 {KANAL}"
    )
    photo = sekli_yukle(sekil)
    try:
        idmanci = idmanci_tap(basliq)  # xəbərdə adı çəkilən futbolçu/idmançı
    except Exception as e:
        print("İdmançı fotosu axtarışı alınmadı:", e)
        idmanci = None
    sema = sum(ord(c) for c in basliq) % len(V.SCHEMES)
    graphic = futbolaz_xeber_qrafikasi(basliq, menbe, photo, idmanci, sema)

    boundary = "----FutbolAZBoundary7MA4YWxkTrZu0gW"
    fields = {"chat_id": admin_id, "caption": caption[:1024], "reply_markup": keyboard}
    body = bytearray()
    for key, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="photo"; filename="futbolaz_xeber.jpg"\r\n')
    body.extend(b"Content-Type: image/jpeg\r\n\r\n")
    body.extend(graphic.getvalue())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Xəbər təsdiqə göndərilmədi: {result}")


def xeberler_html():
    indi = time.time()
    netice = {}

    for sorgu in SORGULAR:
        url = (
            "https://news.google.com/rss/search?q="
            + urllib.parse.quote_plus(sorgu)
            + "&hl=az&gl=AZ&ceid=AZ:az"
        )
        try:
            root = ET.fromstring(get(url))
        except Exception as e:
            print("RSS xetasi:", e)
            continue

        for it in root.iter("item"):
            basliq = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            menbe = (it.findtext("source") or "").strip()

            if menbe and basliq.endswith(" - " + menbe):
                basliq = basliq[: -len(" - " + menbe)]

            if not basliq or not link.startswith("http"):
                continue
            if "todaypress.tv" in (menbe + " " + link).lower():
                continue
            if "abb" in basliq.lower() or "abb-bank.az" in link.lower() or "abb-bank.az" in menbe.lower():
                continue
            if any("\u0400" <= c <= "\u04FF" for c in basliq):
                continue

            kicik = basliq.lower()
            if len(basliq) < 20 or not any(s in kicik for s in SOZLER):
                continue

            try:
                ts = email.utils.parsedate_to_datetime(
                    it.findtext("pubDate")
                ).timestamp()
            except Exception:
                continue

            if ts > indi + 3600 or indi - ts > 3 * 86400:
                continue

            netice[link] = (ts, basliq, menbe, link, rss_sekli_tap(it), rss_metn_tap(it))

    sirali = sorted(netice.values(), reverse=True)[:12]

    if not sirali:
        return "<p>Hələ yeni xəbər yoxdur.</p>", []

    cixis = ["<ul class='xeber'>"]

    for ts, basliq, menbe, link, sekil, tesvir in sirali:
        vaxt = datetime.datetime.fromtimestamp(
            ts, BAKU
        ).strftime("%d.%m %H:%M")

        cixis.append(
            f'<li><a href="{html.escape(link)}" target="_blank" rel="noopener noreferrer">'
            f"{html.escape(basliq)}</a>"
            f'<span class="meta">{html.escape(menbe)} · {vaxt}</span></li>'
        )

    cixis.append("</ul>")
    return "\n".join(cixis), sirali


STATE_FILE = "telegram_state.json"


def telegrama_gonder(metn):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        raise RuntimeError("Telegram token və ya chat ID tapılmadı")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": metn,
        "disable_web_page_preview": "true",
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as r:
        cavab = json.loads(r.read().decode("utf-8"))

    if not cavab.get("ok"):
        raise RuntimeError(f"Telegram xətası: {cavab}")


def state_yaz(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)



def telegram_yenilikleri(matclar, xeberler, now):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        raise RuntimeError("Telegram məlumatları GitHub Secrets-də tapılmadı")

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {"initialized": False, "news": [], "fixtures": {}}

    if not state.get("initialized"):
        state["news"] = [x[3] for x in xeberler]
        bas, son = gunun_penceresi(now)
        for m in matclar:
            if m["league"]["id"] not in LIQALAR:
                continue
            if bas <= m["fixture"]["timestamp"] < son:
                state["fixtures"][str(m["fixture"]["id"])] = fixture_melumat(m)

        state["initialized"] = True
        state_yaz(state)
        print("İlkin məlumatlar yaddaşa yazıldı. Təkrar paylaşım edilmədi.")
        return

    gorulmus_xeberler = set(state.get("news", []))
    evvelki_matclar = state.get("fixtures", {})
    yeni_matclar = dict(evvelki_matclar)

    xeber_mesajlari = []
    bitmis_qruplar = {}
    canli_qruplar = {}
    gunun_oyunlari = []

    # Yeni xəbərlər: əvvəlcə adminə təsdiq üçün göndərilir.
    for ts, basliq, menbe, link, sekil, tesvir in reversed(xeberler):
        if link not in gorulmus_xeberler:
            sekil = sekil or sehife_sekli_tap(link)
            telegram_xeber_onayina_gonder(basliq, menbe, link, sekil, tesvir)
            xeber_mesajlari.append(link)
            gorulmus_xeberler.add(link)

    bas, son = gunun_penceresi(now)
    bitmis_statuslar = ("FT", "AET", "PEN")
    canli_statuslar = ("1H", "HT", "2H", "ET", "BT", "P", "LIVE")

    for m in matclar:
        if m["league"]["id"] not in LIQALAR:
            continue
        if not (bas <= m["fixture"]["timestamp"] < son):
            continue

        fid = str(m["fixture"]["id"])
        cari = fixture_melumat(m)
        kohne = evvelki_matclar.get(fid)

        ev = cari["home"]
        qonaq = cari["away"]
        liqa = cari["league"]
        hesab_text = f'{hesab(cari["home_goals"])} : {hesab(cari["away_goals"])}'
        status = cari["status"]
        matc_setri = f"{ev} {hesab_text} {qonaq}"

        if kohne is None:
            if status in ("NS", "TBD"):
                gunun_oyunlari.append(
                    f"🏆 {liqa}\n⚽ {ev} - {qonaq}\n"
                    f"🕒 Başlama vaxtı: {cari['date'][11:16]}"
                )
            elif status in canli_statuslar:
                canli_qruplar.setdefault(liqa, []).append(
                    f"{matc_setri}  ·  {STATUS_AD.get(status, status)}"
                )
        else:
            kohne_hesab = (kohne.get("home_goals"), kohne.get("away_goals"))
            cari_hesab = (cari["home_goals"], cari["away_goals"])
            kohne_status = kohne.get("status")
            kohne_bitib = kohne_status in bitmis_statuslar
            cari_bitib = status in bitmis_statuslar

            if cari_bitib and not kohne_bitib:
                bitmis_qruplar.setdefault(liqa, []).append(matc_setri)
            elif status in canli_statuslar and (
                cari_hesab != kohne_hesab or status != kohne_status
            ):
                canli_qruplar.setdefault(liqa, []).append(
                    f"{matc_setri}  ·  {STATUS_AD.get(status, status)}"
                )

        yeni_matclar[fid] = cari

    # Bitmiş oyunları bir ümumi başlıq altında, liqalara görə qruplaşdır.
    if bitmis_qruplar:
        hisseler = ["🏁 BAŞA ÇATMIŞ OYUNLAR"]
        for liqa, oyunlar in bitmis_qruplar.items():
            hisseler.append(f"\n{liqa}\n" + "\n".join(oyunlar))
        telegrama_gonder("⚽ FUTBOL AZ — NƏTİCƏLƏR\n\n" + "\n".join(hisseler))

    # Hesabı və ya statusu yenilənən canlı oyunlar.
    if canli_qruplar:
        hisseler = ["🔴 CANLI MATÇLAR"]
        for liqa, oyunlar in canli_qruplar.items():
            hisseler.append(f"\n{liqa}\n" + "\n".join(oyunlar))
        telegrama_gonder("⚽ FUTBOL AZ — YENİLİKLƏR\n\n" + "\n".join(hisseler))

    if gunun_oyunlari:
        telegrama_gonder(
            "📅 GÜNÜN OYUNLARI\n\n" + "\n\n".join(gunun_oyunlari)
        )

    # Xəbərlər kanala birbaşa deyil, admin təsdiqinə göndərilir.

    state["news"] = list(gorulmus_xeberler)[-500:]
    state["fixtures"] = yeni_matclar
    state_yaz(state)

    if not (bitmis_qruplar or canli_qruplar or gunun_oyunlari or xeber_mesajlari):
        print("Telegram üçün yeni xəbər və matç dəyişikliyi yoxdur.")



def fixture_melumat(m):
    f = m["fixture"]
    return {
        "home": m["teams"]["home"]["name"],
        "away": m["teams"]["away"]["name"],
        "league": m["league"]["name"],
        "date": f["date"],
        "status": f["status"]["short"],
        "home_goals": m["goals"]["home"],
        "away_goals": m["goals"]["away"],
    }


SABLON = """<!DOCTYPE html>
<html lang="az">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="600">
<title>Futbol Az: nəticələr və xəbərlər</title>
<style>
:root { --bg:#f6f7f9; --card:#fff; --text:#1c1f24; --muted:#6b7280; --accent:#1a7f37; --line:#e5e7eb; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#14171a; --card:#1d2126; --text:#e8eaed; --muted:#9aa3ad; --accent:#3fb950; --line:#2b3138; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text); font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
.wrap { max-width:760px; margin:0 auto; padding:16px; }
header { display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }
h1 { margin:8px 0; font-size:1.5rem; }
h2 { font-size:1.15rem; margin:24px 0 8px; }
h3 { font-size:1rem; margin:16px 0 6px; color:var(--accent); }
.btn { background:var(--accent); color:#fff; padding:8px 14px; border-radius:8px; text-decoration:none; font-weight:600; }
.card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:4px 14px 14px; }
ul { list-style:none; margin:0; padding:0; }
li { padding:8px 0; border-bottom:1px solid var(--line); }
li:last-child { border-bottom:0; }
.card ul:not(.xeber) li { display:grid; grid-template-columns:1fr auto 1fr; gap:8px; align-items:center; }
.ev { text-align:right; } .qon { text-align:left; }
.saat, .hesab { font-weight:700; min-width:58px; text-align:center; }
.durum { grid-column:1 / -1; text-align:center; font-size:.8rem; color:var(--muted); }
.durum:empty { display:none; }
.xeber a { color:var(--text); text-decoration:none; font-weight:600; }
.xeber a:hover { text-decoration:underline; }
.meta { display:block; font-size:.8rem; color:var(--muted); margin-top:2px; }
footer { margin:24px 0; font-size:.8rem; color:var(--muted); }
</style>
</head>
<body>
<div class="wrap">
<header>
<h1>⚽ Futbol Az</h1>
<a class="btn" href="__KANAL__" target="_blank" rel="noopener noreferrer">Telegram kanalımız</a>
</header>
<p style="color:var(--muted)">Yenilənib: __YENILENIB__ (Bakı vaxtı)</p>
<h2>Bugünkü matçlar və nəticələr</h2>
<div class="card">__MATCLAR__</div>
<h2>Xəbərlər</h2>
<div class="card">__XEBERLER__</div>
<footer>Xəbərlərin müəllifi göstərilən saytlardır, başlıqlar mənbəyə yönləndirir. Səhifə avtomatik yenilənir.</footer>
</div>
</body>
</html>
"""



def main():
    now = datetime.datetime.now(BAKU)
    matclar = matclar_cek(now)

    xeber_html, xeberler = xeberler_html()

    telegram_yenilikleri(matclar, xeberler, now)
    avtomatik_mem_paylas(matclar, xeberler, now)
    sehife = (
        SABLON.replace("__KANAL__", KANAL)
        .replace("__YENILENIB__", now.strftime("%d.%m.%Y %H:%M"))
        .replace("__MATCLAR__", matclar_html(matclar, now))
        .replace("__XEBERLER__", xeber_html)
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(sehife)

    print("index.html yaradildi")


if __name__ == "__main__":
    if os.environ.get("TELEGRAM_TEST") == "1":
        telegrama_gonder(
            "⚽ FUTBOL AZ\n\nTelegram botu uğurla işləyir! ✅"
        )
        print("Test mesajı göndərildi.")
    main()
