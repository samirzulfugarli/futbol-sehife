import datetime
import email.utils
import html
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from memes import avtomatik_mem_paylas

API_KEY = os.environ["API_FOOTBALL_KEY"].strip()
print("Acar uzunlugu:", len(API_KEY))
BASE = "https://v3.football.api-sports.io"
BAKU = datetime.timezone(datetime.timedelta(hours=4))
KANAL = "https://t.me/futbolaz_official"
SORGULAR = ["Premyer Liqa futbol", "Qarabağ futbol"]

LIQALAR = {
    419: "Premyer Liqa",
    420: "Azərbaycan Kuboku",
    418: "Birinci Divizion",
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

            netice[link] = (ts, basliq, menbe, link)

    sirali = sorted(netice.values(), reverse=True)[:12]

    if not sirali:
        return "<p>Hələ yeni xəbər yoxdur.</p>", []

    cixis = ["<ul class='xeber'>"]

    for ts, basliq, menbe, link in sirali:
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
        state = {
            "initialized": False,
            "news": [],
            "fixtures": {}
        }

    if not state.get("initialized"):
        state["news"] = [x[3] for x in xeberler]

        bas, son = gunun_penceresi(now)
        for m in matclar:
            if m["league"]["id"] not in LIQALAR:
                continue
            if not (bas <= m["fixture"]["timestamp"] < son):
                continue

            fid = str(m["fixture"]["id"])
            state["fixtures"][fid] = fixture_melumat(m)

        state["initialized"] = True
        state_yaz(state)
        print("İlkin məlumatlar yaddaşa yazıldı. Təkrar paylaşım edilmədi.")
        return

    gorulmus_xeberler = set(state.get("news", []))
    evvelki_matclar = state.get("fixtures", {})
    yeni_matclar = dict(evvelki_matclar)

    mesajlar = []

    # Yeni xəbərləri tap
    for ts, basliq, menbe, link in reversed(xeberler):
        if link not in gorulmus_xeberler:
            mesajlar.append(
                f"📰 YENİ FUTBOL XƏBƏRİ\n\n"
                f"{basliq}\n"
                f"Mənbə: {menbe}\n"
                f"{link}"
            )
            gorulmus_xeberler.add(link)

    # Yeni matçları və hesab dəyişikliklərini tap
    bas, son = gunun_penceresi(now)

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
        hesab_text = f'{cari["home_goals"]} : {cari["away_goals"]}'
        status = cari["status"]

        if kohne is None:
            mesajlar.append(
                f"⚽ YENİ MATÇ\n\n"
                f"{liqa}\n{ev} - {qonaq}\n"
                f"Başlama vaxtı: {cari['date'][11:16]}"
            )
        else:
            kohne_hesab = (
                kohne.get("home_goals"),
                kohne.get("away_goals")
            )
            cari_hesab = (
                cari["home_goals"],
                cari["away_goals"]
            )

            kohne_bitib = kohne.get("status") in ("FT", "AET", "PEN")
            cari_bitib = status in ("FT", "AET", "PEN")

            if cari_bitib and not kohne_bitib:
                mesajlar.append(
                    f"🏁 MATÇ BAŞA ÇATDI\n\n"
                    f"{liqa}\n{ev} {hesab_text} {qonaq}\n"
                    f"Yekun nəticə: {STATUS_AD.get(status, status)}"
                )
            elif cari_hesab != kohne_hesab:
                mesajlar.append(
                    f"⚽ HESAB DƏYİŞDİ\n\n"
                    f"{liqa}\n{ev} {hesab_text} {qonaq}\n"
                    f"Status: {STATUS_AD.get(status, status)}"
                )

        yeni_matclar[fid] = cari

    # Mesajları Telegram-a göndər
    if mesajlar:
        hisseler = []
        cari_hisse = "⚽ FUTBOL AZ — YENİLİKLƏR\n\n"

        for mesaj in mesajlar:
            if len(cari_hisse) + len(mesaj) + 2 > 3500:
                hisseler.append(cari_hisse)
                cari_hisse = "⚽ FUTBOL AZ — DAVAMI\n\n"

            cari_hisse += mesaj + "\n\n"

        if cari_hisse.strip():
            hisseler.append(cari_hisse)

        for hisse in hisseler:
            telegrama_gonder(hisse)

        print("Telegram paylaşımı göndərildi:", len(mesajlar))
    else:
        print("Telegram üçün yeni məlumat yoxdur.")

    state["news"] = list(gorulmus_xeberler)[-500:]
    state["fixtures"] = yeni_matclar
    state_yaz(state)


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
    samir
    main()

