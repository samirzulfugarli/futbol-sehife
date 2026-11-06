"""Xəbər başlığında adı çəkilən futbolçu/idmançını tapıb Vikipediyadan portret fotosunu gətirir.

Fotolar yalnız Vikipediya təsvirində idmançı olduğu təsdiqlənəndə götürülür; təsdiqlənməsə
heç nə qaytarılmır (səhv şəxsin fotosu qoyulmasın deyə).
"""
import io
import json
import re
import unicodedata
import urllib.parse
import urllib.request

from PIL import Image

UA = {"User-Agent": "FutbolAZ-bot/1.0 (https://t.me/futbolaz_official)"}

CAP = r"[A-ZƏÖÜÇŞĞİ]"
LOW = r"[a-zəöüçşğıi'’\-]"
NAME_RE = re.compile(rf"{CAP}{LOW}{{2,}}(?:\s+{CAP}{LOW}{{2,}}){{0,2}}")

# Başlıqda tez-tez olan, şəxs olmayan sözlər (Vikipediyaya boş yerə sorğu getməsin).
STOP = {
    "qarabağ", "neftçi", "sabah", "zirə", "sumqayıt", "qəbələ", "real", "madrid",
    "barcelona", "liverpool", "arsenal", "manchester", "city", "united", "uefa",
    "affa", "premyer", "liqa", "çempionlar", "avropa", "konfrans", "milli", "yığma",
    "azərbaycan", "türkiyə", "fənərbaxça", "qalatasaray", "beşiktaş", "besiktas",
    "bu", "bir", "və", "üçün", "futbol", "oyun", "matç", "məşqçi", "baş", "transfer",
    "çempion", "kubok", "fifa", "var", "bakı", "london", "paris", "roma", "milan",
    "inter", "juventus", "chelsea", "tottenham", "bayern", "dortmund", "psj", "psg",
}

SPORT_WORDS = (
    "footballer", "football player", "soccer player", "football manager", "futbolçu",
    "futbol", "basketball", "tennis", "boxer", "wrestler", "judoka", "swimmer",
    "gymnast", "weightlifter", "sprinter", "athlete", "racing driver", "cyclist",
    "fighter", "mixed martial", "idmançı", "olympic", "taekwondo", "karate",
    "volleyball", "handball", "chess", "grandmaster",
)


def _norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.replace("ı", "i").replace("ə", "e")


def _get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def _get_bytes(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def namizedler(basliq):
    """Başlıqdakı böyük hərflə başlayan söz yığınlarını (şəxs adı ola biləcək) qaytarır."""
    cands = []
    for m in NAME_RE.finditer(basliq):
        words = m.group(0).split()
        words = [w for w in words if _norm(w) not in {_norm(x) for x in STOP}]
        if not words:
            continue
        cands.append(" ".join(words))
    # Uzun (tam ad) olanlar öncə gəlsin
    cands.sort(key=lambda c: -len(c.split()))
    seen, out = set(), []
    for c in cands:
        if c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out[:5]


def _ad_uygundur(namized, title):
    """Azərbaycan şəkilçiləri (Messinin, Ronaldonun) üçün sərbəst uyğunluq yoxlaması."""
    n = _norm(namized)
    for w in _norm(title).split():
        if len(w) >= 4 and (n.startswith(w) or w.startswith(n[:5]) and len(n) >= 5 or w in n):
            return True
    return False


def _idmancidir(tesvir):
    t = (tesvir or "").lower()
    return any(k in t for k in SPORT_WORDS)


def idmanci_tap(basliq):
    """(ad, PIL.Image, təsvir) və ya None qaytarır."""
    for namized in namizedler(basliq):
        try:
            q = urllib.parse.quote(namized + " footballer")
            res = _get_json(
                "https://en.wikipedia.org/w/api.php?action=query&list=search&format=json"
                f"&srlimit=3&srsearch={q}"
            )
            hits = res.get("query", {}).get("search", [])
        except Exception as e:
            print("Vikipediya axtarışı alınmadı:", e)
            continue

        for hit in hits:
            title = hit.get("title", "")
            if not _ad_uygundur(namized, title):
                continue
            try:
                s = _get_json(
                    "https://en.wikipedia.org/api/rest_v1/page/summary/"
                    + urllib.parse.quote(title.replace(" ", "_"))
                )
            except Exception as e:
                print("Vikipediya xülasəsi alınmadı:", e)
                continue
            if not _idmancidir(s.get("description", "")):
                continue
            src = (s.get("originalimage") or s.get("thumbnail") or {}).get("source")
            thumb = (s.get("thumbnail") or {}).get("source")
            for url in (thumb, src):
                if not url:
                    continue
                try:
                    img = Image.open(io.BytesIO(_get_bytes(url))).convert("RGB")
                except Exception as e:
                    print("Foto yüklənmədi:", e)
                    continue
                if img.width >= 200 and img.height >= 200:
                    print(f"İdmançı tapıldı: {title}")
                    return title, img, s.get("description", "")
    return None
