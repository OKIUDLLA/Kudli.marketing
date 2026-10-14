#!/usr/bin/env python3
"""Generátor ukázkových webů pro autoservisy (Kudli. marketing).

Použití:
  python3 generator.py data/<slug>.json             ukázka (lišta „ukázka“ + noindex)
  python3 generator.py data/<slug>.json --qr        navíc QR kód na adresu zveřejněné ukázky
  python3 generator.py data/<slug>.json --ostry     ostrý web pro klienta (bez lišty, indexovatelný)

Kam se zapíše výsledek:
  * vzorová vymyšlená firma, nebo skutečná firma s platným "zverejneni"
      -> <repo>/ukazky/<slug>/index.html   (po pushi na www.kudlimarketing.cz/ukazky/<slug>/)
  * ostatní -> _nastroje/ukazky/nahled/<slug>/index.html   (jen náhled, není v gitu ani na webu)
  * --ostry -> _nastroje/ukazky/ostre/<slug>/index.html    (nahrává se na vlastní doménu klienta)

Pravidla pro data skutečných firem vynucuje generátor, co to jde (viz _nastroje/README.md).
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
VEREJNE = os.path.join(REPO, "ukazky")
WEB = "https://www.kudlimarketing.cz"
VZOROVE_SLUGY = {"klic-a-kolo"}          # jen tyto ukázky smí být s vymyšlenou firmou

DNY = [("po", "Pondělí", "Po", "Monday"), ("ut", "Úterý", "Út", "Tuesday"), ("st", "Středa", "St", "Wednesday"),
       ("ct", "Čtvrtek", "Čt", "Thursday"), ("pa", "Pátek", "Pá", "Friday"), ("so", "Sobota", "So", "Saturday"),
       ("ne", "Neděle", "Ne", "Sunday")]

# klíč: (název, popis, ikona, tvar do úvodní věty). Popisy jsou obecné, nic neslibují;
# když firma uvádí víc, patří do dat vlastní "popis".
SLUZBY = {
    "servis": ("Servis a údržba", "Pravidelné servisní prohlídky a údržba vozu.", "wrench", "servis"),
    "opravy": ("Mechanické opravy", "Opravy mechanických závad osobních aut.", "settings", "opravy"),
    "brzdy": ("Brzdy", "Kontrola a výměna brzdových dílů.", "disc-3", "brzdy"),
    "diagnostika": ("Diagnostika", "Počítačová diagnostika závad.", "activity", "diagnostika"),
    "pneuservis": ("Pneuservis", "Přezouvání a vyvažování kol.", "life-buoy", "pneuservis"),
    "uskladneni": ("Uskladnění pneumatik", "Uložení sezónní sady pneumatik.", "warehouse", "uskladnění pneumatik"),
    "prodej_pneu": ("Prodej pneumatik", "Prodej nových pneumatik.", "package", "prodej pneumatik"),
    "klimatizace": ("Klimatizace", "Servis a plnění klimatizace.", "snowflake", "klimatizace"),
    "geometrie": ("Geometrie", "Měření a seřízení geometrie náprav.", "crosshair", "měření geometrie"),
    "stk": ("Příprava na STK", "Kontrola vozu před technickou prohlídkou.", "clipboard-check", "příprava na STK"),
    "elektro": ("Autoelektrika", "Opravy elektroinstalace vozu.", "zap", "autoelektrika"),
    "baterie": ("Autobaterie", "Kontrola a výměna autobaterie.", "battery-charging", "výměna autobaterií"),
    "karoserie": ("Karosářské práce", "Opravy poškozené karoserie.", "hammer", "karosářské práce"),
    "lakovani": ("Lakování", "Lakování karosářských dílů.", "spray-can", "lakování"),
    "pojistne": ("Pojistné události", "Opravy vozů po pojistné události.", "shield-check", "opravy po nehodách"),
    "autoskla": ("Autoskla", "Výměna a opravy autoskel.", "car-front", "autoskla"),
    "tazne": ("Tažná zařízení", "Montáž tažných zařízení.", "caravan", "montáž tažných zařízení"),
    "odtah": ("Odtahová služba", "Odtah nepojízdného vozu.", "truck", "odtahová služba"),
    "spojky": ("Spojky", "Výměna spojky.", "circle-dot", "spojky"),
    "prevodovky": ("Převodovky", "Opravy převodovek.", "cog", "převodovky"),
    "rozvody": ("Rozvody", "Výměna rozvodového řemene nebo řetězu.", "link", "rozvody"),
    "vyfuky": ("Výfuky", "Opravy a výměna výfuků.", "wind", "výfuky"),
    "uzitkova": ("Užitková auta", "Servis dodávek a užitkových aut.", "bus", "užitková auta"),
    "lpg": ("LPG a CNG", "Servis plynových zástaveb.", "fuel", "plynové zástavby"),
    "olej": ("Výměna oleje", "Výměna motorového oleje a filtrů.", "droplet", "výměna oleje"),
    "cisteni": ("Čištění interiéru", "Tepování sedaček a koberečků.", "sparkles", "čištění interiéru"),
    "ozon": ("Ozonové čištění", "Odstranění pachů z interiéru ozonem.", "wind", "ozonové čištění"),
}

UI_IKONY = {"phone", "map-pin", "clock", "navigation", "mail", "calendar-check"}
PRAVNI_FORMY = {"sro": "sídlo", "as": "sídlo", "jina": "sídlo", "osvc": "místo podnikání"}
ZVEREJNENI_DUVODY = {"zadost-firmy", "schvalil-ondra"}
NEVYZNAMNA = {"a", "u", "na", "v", "ve", "s", "se", "z", "ze", "k", "ke", "do", "pod", "nad", "za", "pro", "o", "i",
              "s.r.o.", "spol.", "r.o.", "a.s.", "k.s.", "v.o.s.", "&"}
NEZVYRAZNIT = {"syn", "synové", "dcera", "spol", "sro", "group"}

# Známá pole a jejich typy (kvůli překlepům a špatným typům v datech).
POLE = {
    "slug": str, "nazev": str, "firma": str, "obor": str, "lokalita": str, "kde": str, "adresa": dict,
    "sidlo": str, "sidlo_zverejnit": bool, "pravni_forma": str, "telefon": str, "email": str, "ico": str,
    "rejstrik": str, "od_roku": int, "hodiny": dict, "svatky": str, "hodiny_pozn": str, "sluzby": list,
    "znacky": list, "barva": str, "uvod": str, "mapa_dotaz": str, "zdroje": list, "overeno": str,
    "zverejneni": dict, "domena": str, "kredit": bool, "fiktivni": bool, "poznamka": str,
}

BANNER = """<!-- kudli-demo:start -->
<aside id="kudli-demo-banner" aria-label="Upozornění" lang="cs" style="all:initial;box-sizing:border-box;display:block;position:fixed;left:0;right:0;bottom:0;z-index:2147483647;width:100%;margin:0;padding:9px 16px calc(9px + env(safe-area-inset-bottom, 0px));background:#14181c;color:#f3f4f6;font:500 13px/1.45 system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;text-align:center;border-top:1px solid rgba(255,255,255,.16);box-shadow:0 -2px 12px rgba(0,0,0,.25)">@@TEXT@@ Připravil <a href="https://www.kudlimarketing.cz/" style="all:initial;font:inherit;color:#ffffff;text-decoration:underline;cursor:pointer">Kudli.&nbsp;marketing</a>.</aside>
<script>(function(){try{var b=document.getElementById('kudli-demo-banner');if(!b)return;var d=document.body,t=0;function fit(){var h=b.offsetHeight||0,vh=window.innerHeight||0;d.style.removeProperty('padding-bottom');var base=parseFloat(getComputedStyle(d).paddingBottom)||0;d.style.setProperty('padding-bottom',(base+h)+'px','important');var els=d.getElementsByTagName('*');for(var i=0;i<els.length;i++){var el=els[i];if(el===b||b.contains(el))continue;var o=el.getAttribute('data-kudli-bottom');if(o===null){var cs=getComputedStyle(el);if(cs.position!=='fixed')continue;var r=el.getBoundingClientRect();if(!r.width||!r.height||r.top<vh*0.5||r.bottom<vh-160)continue;o=parseFloat(cs.bottom);if(isNaN(o))continue;el.setAttribute('data-kudli-bottom',String(o));}el.style.setProperty('bottom',(parseFloat(o)+h)+'px','important');}}function later(){clearTimeout(t);t=setTimeout(fit,150);}fit();window.addEventListener('load',fit);window.addEventListener('resize',later);window.addEventListener('scroll',later,{passive:true});setTimeout(fit,1200);setTimeout(fit,3500);}catch(e){}})();</script>
<!-- kudli-demo:end -->
"""
BANNER_TEXT = "Nezávazná ukázka webu, nejde o oficiální stránky firmy."
BANNER_TEXT_FIKTIVNI = "Ukázka šablony, firma je vymyšlená."


class Chyba(Exception):
    pass


def esc(s):
    return html.escape(str(s), quote=True)


def cz(text):
    """Česká typografie: jednopísmenná předložka nebo spojka nezůstane na konci řádku."""
    return re.sub(r"(?<!\w)([vVsSzZkKoOuUiIaA]) ", "\\1\u00a0", text)


def nbsp(text):
    return text.replace(" ", "\u00a0")


# ---------- barvy ----------

BILA, CERNA, TEXT_TMAVY, INK, POZADI = (255, 255, 255), (0, 0, 0), (17, 17, 17), (14, 17, 22), (244, 245, 247)


def _rgb(hexa):
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", hexa or "")
    if not m:
        raise Chyba('"barva" musí být ve tvaru #rrggbb, ne %r' % hexa)
    v = m.group(1)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c))) for c in rgb)


def _lum(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def kontrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def text_na(bg):
    """Barva textu s kontrastem aspoň 4,5 : 1, nebo None."""
    if kontrast(bg, BILA) >= 4.5:
        return "#ffffff"
    if kontrast(bg, TEXT_TMAVY) >= 4.5:
        return "#111111"
    return None


def nejblizsi(a, ok):
    """Nejbližší odstín (ztmavený nebo zesvětlený), který splní podmínku."""
    for i in range(0, 101):
        for cil in (CERNA, BILA):
            c = tuple(round(x) for x in _mix(a, cil, i / 100))
            if ok(c):
                return c
    raise Chyba("k barvě nejde najít čitelný odstín")


def tlacitko(a, ok):
    """Odstín pro tlačítko: když to jde s malou změnou barvy, s bílým písmem (vypadá lépe), jinak s tmavým."""
    for i in range(0, 13):
        for cil in (CERNA, BILA):
            c = tuple(round(x) for x in _mix(a, cil, i / 100))
            if ok(c) and kontrast(c, BILA) >= 4.5:
                return c, "#ffffff"
    c = nejblizsi(a, lambda c: ok(c) and text_na(c))
    return c, text_na(c)


def barvy(hexa):
    """Odstíny hlavní barvy pro světlé i tmavé plochy.
    Text má všude kontrast aspoň 4,5 : 1, tlačítka a plochy aspoň 3 : 1 vůči okolí (WCAG 2.1 AA)."""
    a = _rgb(hexa)
    btn_t, ink_t = tlacitko(a, lambda c: kontrast(c, INK) >= 3)
    btn_s, ink_s = tlacitko(a, lambda c: kontrast(c, BILA) >= 3 and kontrast(c, POZADI) >= 3)
    return {
        "accent_text": _hex(nejblizsi(a, lambda c: kontrast(c, POZADI) >= 4.5)),   # text na světlém
        "accent_dark": _hex(nejblizsi(a, lambda c: kontrast(c, INK) >= 4.5)),      # text na tmavém
        "btn_dark": _hex(btn_t), "btn_dark_ink": ink_t,                            # tlačítka na tmavém
        "btn_light": _hex(btn_s), "btn_light_ink": ink_s,                          # tlačítka a pruh na světlém
        "accent_soft": "rgba(%d,%d,%d,.11)" % a,
        "accent_glow": "rgba(%d,%d,%d,.30)" % a,
    }


# ---------- kontrola dat ----------

def ico_platne(ico):
    if not re.fullmatch(r"\d{8}", ico):
        return False
    s = sum(int(ico[i]) * (8 - i) for i in range(7))
    return (11 - s % 11) % 10 == int(ico[7])


def telefon(t):
    cisla = re.sub(r"[^\d+]", "", t)
    if cisla.startswith("00"):
        cisla = "+" + cisla[2:]
    if re.fullmatch(r"\d{9}", cisla):
        cisla = "+420" + cisla
    if cisla.startswith("+420"):
        n = cisla[4:]
        if not re.fullmatch(r"\d{9}", n):
            raise Chyba("české číslo musí mít 9 číslic, ne %r" % t)
        mistni = nbsp("%s %s %s" % (n[:3], n[3:6], n[6:]))       # nedělitelné mezery: číslo se nezalomí
        return {"href": "tel:+420" + n, "display": mistni, "intl": "+420\u00a0" + mistni,
                "ld": "+420 %s %s %s" % (n[:3], n[3:6], n[6:])}
    if re.fullmatch(r"\+\d{8,15}", cisla):
        hezky = re.sub(r"\s+", " ", t.strip())
        return {"href": "tel:" + cisla, "display": nbsp(hezky), "intl": nbsp(hezky), "ld": hezky}
    raise Chyba("neplatné telefonní číslo %r" % t)


def cas(s):
    m = re.fullmatch(r"(\d{1,2})[:.](\d{2})", s.strip())
    if not m:
        raise Chyba("čas musí být ve tvaru 7:30, ne %r" % s)
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 24 or mi > 59 or (h == 24 and mi):
        raise Chyba("neplatný čas %r" % s)
    return h * 60 + mi


def fmt(mins):
    return "%d:%02d" % divmod(mins, 60)


def datum(s, co):
    try:
        d = dt.date.fromisoformat(s)
    except (TypeError, ValueError):
        raise Chyba('%s musí být datum RRRR-MM-DD, ne %r' % (co, s))
    if d > dt.date.today():
        raise Chyba("%s nemůže být v budoucnosti (%s)" % (co, s))
    return d


def hodiny(h):
    navic = set(h) - {d[0] for d in DNY}
    if navic:
        raise Chyba("neznámé dny v hodinách: %s" % ", ".join(sorted(navic)))
    out = []
    for key, *_ in DNY:
        if key not in h:
            raise Chyba('v "hodiny" chybí den "%s" (zavřeno = [])' % key)
        if not isinstance(h[key], list) or not all(isinstance(x, str) for x in h[key]):
            raise Chyba('"hodiny" → "%s" musí být seznam jako ["7:00-12:00"]' % key)
        ints = []
        for iv in h[key]:
            parts = re.split(r"\s*[-–]\s*", iv.strip())
            if len(parts) != 2:
                raise Chyba("interval musí být ve tvaru 7:00-12:00, ne %r" % iv)
            a, b = cas(parts[0]), cas(parts[1])
            if a >= b:
                raise Chyba("interval %r končí dřív, než začne" % iv)
            if ints and a <= ints[-1][1]:
                raise Chyba("intervaly v %s se překrývají nebo nejsou seřazené" % key)
            ints.append((a, b))
        out.append(ints)
    if not any(out):
        raise Chyba("otevírací doba je prázdná, firma by byla pořád zavřená")
    return out


def skupiny(ints):
    """Spojí po sobě jdoucí dny se stejnou dobou: [(od_dne, do_dne, intervaly)]."""
    g = []
    for i, v in enumerate(ints):
        if g and g[-1][2] == v and g[-1][1] == i - 1:
            g[-1] = (g[-1][0], i, v)
        else:
            g.append((i, i, v))
    return g


def souhrn_hodin(ints):
    if all(v == [(0, 1440)] for v in ints):
        return "Nonstop"
    casti = []
    for a, b, v in skupiny(ints):
        if not v:
            continue
        dny = DNY[a][2] if a == b else "%s–%s" % (DNY[a][2], DNY[b][2])
        if v == [(0, 1440)]:
            doba = "nonstop"
        else:
            doba = "%s–%s" % (fmt(v[0][0]), fmt(v[-1][1])) + (" s přestávkou" if len(v) > 1 else "")
        casti.append("%s %s" % (dny, doba))
    if len(casti) <= 3:
        return ", ".join(casti)
    otevreno = [i for i, v in enumerate(ints) if v]
    if otevreno == list(range(otevreno[0], otevreno[-1] + 1)):
        return "Otevřeno %s–%s" % (DNY[otevreno[0]][2], DNY[otevreno[-1]][2])
    return "Otevírací doba podle dnů"


def kontrola_typu(data):
    varovani = []
    for k, v in data.items():
        if k not in POLE:
            varovani.append('neznámé pole "%s" se nepoužije (překlep?)' % k)
            continue
        if not isinstance(v, POLE[k]) or (POLE[k] is int and isinstance(v, bool)):
            raise Chyba('"%s" má mít typ %s' % (k, {str: "text", dict: "objekt {…}", list: "seznam […]",
                                                      int: "celé číslo", bool: "true/false"}[POLE[k]]))
    if "DOPLNIT" in json.dumps(data, ensure_ascii=False):
        raise Chyba('v datech zůstalo „DOPLNIT“')
    for k in ("znacky", "zdroje"):
        if not all(isinstance(x, str) and x.strip() for x in data.get(k, [])):
            raise Chyba('"%s" musí být seznam textů' % k)
    adr = data.get("adresa", {})
    for k in ("ulice", "psc", "obec"):
        if not isinstance(adr.get(k), str) or not adr.get(k).strip():
            raise Chyba('v "adresa" chybí text "%s"' % k)
    return varovani


def zverejneni(z):
    if not isinstance(z, dict) or z.get("duvod") not in ZVEREJNENI_DUVODY:
        raise Chyba('"zverejneni" musí být {"duvod": "zadost-firmy" nebo "schvalil-ondra", "datum": "RRRR-MM-DD"}')
    d = datum(z.get("datum"), '"zverejneni" → "datum"')
    return "%s %d. %d. %d" % ("žádost firmy" if z["duvod"] == "zadost-firmy" else "schválil Ondra", d.day, d.month, d.year)


# ---------- šablona ----------

def vypln(tpl, ctx):
    bloky = set(re.findall(r"<!--/?\?(\w+)-->", tpl))
    mista = {k for m in re.finditer(r"\{\{\{(\w+)\}\}\}|\{\{(\w+)\}\}", tpl) for k in m.groups() if k}
    chybi = sorted((bloky | mista) - set(ctx))
    if chybi:
        raise Chyba("šablona chce hodnoty, které generátor nezná: %s" % ", ".join(chybi))

    def blok(m):
        return m.group(2) if ctx[m.group(1)] else ""
    prev = None
    while prev != tpl:
        prev = tpl
        tpl = re.sub(r"<!--\?(\w+)-->(.*?)<!--/\?\1-->\n?", blok, tpl, flags=re.S)
    misto = re.compile(r"\{\{\{(\w+)\}\}\}|\{\{(\w+)\}\}")
    zbytek = re.findall(r"\{\{|<!--/?\?\w*-->", misto.sub("", tpl))
    if zbytek:
        raise Chyba("šablona má neuzavřený blok nebo vadné místo: %s" % zbytek[:3])

    def dosad(m):
        return str(ctx[m.group(1)]) if m.group(1) else esc(ctx[m.group(2)])
    return misto.sub(dosad, tpl)       # dosazený obsah se už neprohledává


def ikona(n, cls="i"):
    return '<svg class="%s" aria-hidden="true"><use href="#i-%s"/></svg>' % (cls, n)


def inicialy(nazev):
    slova = [w for w in re.split(r"\s+", nazev) if w and w.lower() not in NEVYZNAMNA]
    pis = [w[0] for w in slova if w[0].isalpha()]
    return ("".join(pis[:2]) or nazev[:1]).upper()


def nadpis(nazev):
    """Poslední slovo názvu barevně, jen když je to opravdu jméno (ne „s.r.o.“, „syn“, „a“)."""
    slova = nazev.split()
    w = slova[-1] if slova else ""
    if len(slova) >= 2 and len(w) >= 3 and w.isalpha() and w.lower() not in NEZVYRAZNIT:
        return esc(" ".join(slova[:-1])) + ' <span class="hl">%s</span>' % esc(w)
    return esc(nazev)


def uvodni_veta(vety, obor):
    """Nejvýš tři služby; přeskočí tu, jejíž slovo už ve větě je („opravy… opravy brzd“)."""
    vybrane, slova = [], set()
    for v in vety:
        w = {x.lower() for x in v.split() if len(x) >= 4}
        if w & slova:
            continue
        vybrane.append(v)
        slova |= w
        if len(vybrane) == 3:
            break
    if not vybrane:
        return obor
    spoj = vybrane[0] if len(vybrane) == 1 else ", ".join(vybrane[:-1]) + " a " + vybrane[-1]
    return spoj[0].upper() + spoj[1:]


def sestav(data, ostry=False):
    if not isinstance(data, dict):
        raise Chyba("data musí být objekt {…}")
    varovani = kontrola_typu(data)
    for k in ("slug", "nazev", "firma", "lokalita", "kde", "adresa", "hodiny"):
        if not data.get(k):
            raise Chyba('chybí povinné pole "%s"' % k)
    slug = data["slug"]
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,58})[a-z0-9]", slug):
        raise Chyba("slug smí mít jen malá písmena bez diakritiky, číslice a pomlčky (3–60 znaků)")
    fikt = data.get("fiktivni", False)
    ico = data.get("ico", "").replace(" ", "")
    if fikt:
        if slug not in VZOROVE_SLUGY:
            raise Chyba('"fiktivni" je jen pro vzorovou ukázku (%s). Pro skutečnou firmu zkopíruj '
                        'data/_vzor-skutecna-firma.json.' % ", ".join(sorted(VZOROVE_SLUGY)))
        if ico_platne(ico):
            raise Chyba("vymyšlená firma nesmí mít platné IČO (mohlo by patřit skutečné firmě)")
        if data.get("zverejneni") or ostry:
            raise Chyba("vymyšlená firma se nezveřejňuje jako skutečná ani nestaví jako ostrý web")
    forma = data.get("pravni_forma", "sro" if fikt else "")
    if forma not in PRAVNI_FORMY:
        raise Chyba('"pravni_forma" musí být jedna z: %s' % ", ".join(PRAVNI_FORMY))
    if not fikt:
        if not data.get("zdroje") or not all(re.match(r"https?://", z) for z in data["zdroje"]):
            raise Chyba('u skutečné firmy jsou povinné "zdroje": odkazy (https://…), odkud fakta jsou')
        datum(data.get("overeno"), '"overeno" (kdy byla fakta zkontrolovaná)')
        if not ico_platne(ico):
            raise Chyba("IČO %r chybí nebo nemá platný kontrolní součet, zkontroluj ho v ARES" % ico)
        if forma != "osvc" and not data.get("sidlo"):
            raise Chyba('u skutečné firmy je povinné "sidlo" z ARES (i když je stejné jako provozovna)')
        if not data.get("rejstrik"):
            if ostry:
                raise Chyba('ostrý web musí mít "rejstrik" (§ 435 občanského zákoníku)')
            varovani.append('chybí "rejstrik": u ostrého webu bude povinný')
    if ostry:
        if not data.get("domena"):
            raise Chyba('ostrý web potřebuje "domena" (např. www.autoservis-novak.cz)')
        if forma == "osvc" and not data.get("sidlo"):
            raise Chyba('ostrý web OSVČ musí mít "sidlo" (místo podnikání, § 435 občanského zákoníku)')
    zverejneno = zverejneni(data["zverejneni"]) if data.get("zverejneni") else ""

    adr = data["adresa"]
    if not re.fullmatch(r"\d{3} ?\d{2}", adr["psc"]):
        raise Chyba("PSČ musí mít 5 číslic, ne %r" % adr["psc"])
    psc = re.sub(r"^(\d{3}) ?(\d{2})$", r"\1 \2", adr["psc"])
    tel = telefon(data["telefon"]) if data.get("telefon") else None
    email = data.get("email", "")
    if not tel and not email:
        raise Chyba("firma musí mít aspoň telefon nebo e-mail")
    if email and not re.fullmatch(r"[^@\s<>\"']+@[^@\s<>\"']+\.[a-z]{2,}", email, flags=re.I):
        raise Chyba("neplatný e-mail %r" % email)
    rok = data.get("od_roku")
    if rok is not None and not (1900 <= rok <= dt.date.today().year):
        raise Chyba('"od_roku" musí být rok, např. 1998')
    ints = hodiny(data["hodiny"])
    souhrn = souhrn_hodin(ints)
    svatky = data.get("svatky", "")
    if svatky not in ("", "zavreno", "otevreno"):
        raise Chyba('"svatky" může být "zavreno", "otevreno", nebo chybět (když to nevíme)')
    pozn = data.get("hodiny_pozn", "")
    if svatky == "zavreno" and "svát" not in pozn.lower():
        pozn = ("Ve svátky zavřeno. " + pozn).strip()
    if not data.get("sluzby"):
        varovani.append("bez služeb: sekce Služby se nezobrazí")
    barva = data.get("barva", "#d0312d")

    with open(os.path.join(HERE, "ikony.json"), encoding="utf-8") as f:
        ik = json.load(f)
    IKONY = ik["ikony"]
    pouzite = set(UI_IKONY)

    # služby
    sl_html, vety = [], []
    for s in data.get("sluzby", []):
        if isinstance(s, str):
            if s not in SLUZBY:
                raise Chyba("neznámá služba %r (povolené: %s)" % (s, ", ".join(SLUZBY)))
            nazev_s, popis, ico_s, veta = SLUZBY[s]
        elif isinstance(s, dict):
            if s.get("klic") and s["klic"] not in SLUZBY:
                raise Chyba("neznámý klíč služby %r" % s["klic"])
            zaklad = SLUZBY.get(s.get("klic", ""), (None, None, "wrench", None))
            nazev_s = s.get("nazev") or zaklad[0]
            popis = s.get("popis") or zaklad[1]
            ico_s = s.get("ikona") or zaklad[2]
            veta = s.get("veta", zaklad[3])
            if not isinstance(nazev_s, str) or not isinstance(popis, str) or not nazev_s or not popis:
                raise Chyba("vlastní služba potřebuje text nazev a popis: %r" % s)
        else:
            raise Chyba("služba musí být klíč nebo objekt, ne %r" % s)
        if ico_s not in IKONY:
            raise Chyba("neznámá ikona %r (povolené: %s)" % (ico_s, ", ".join(sorted(IKONY))))
        pouzite.add(ico_s)
        if veta:
            vety.append(veta)
        sl_html.append('<li class="svc"><span class="svc-ico">%s</span><div><h3>%s</h3><p>%s</p></div></li>'
                       % (ikona(ico_s), esc(cz(nazev_s)), esc(cz(popis))))

    obor = data.get("obor", "Autoservis")
    if data.get("uvod"):
        uvod = data["uvod"]
        uvod_html = esc(cz(uvod))
    else:
        zacatek = uvodni_veta(vety, obor)
        uvod = "%s %s." % (zacatek, data["kde"])
        misto = cz(data["kde"]).replace("-", "\u2011")       # místo se nezalomí uprostřed („v Brně-/Líšni“)
        uvod_html = "%s %s." % (esc(cz(zacatek)), esc(misto))

    # odkazy
    dotaz = data.get("mapa_dotaz") or "%s, %s %s" % (adr["ulice"], psc, adr["obec"])
    if fikt:
        nav_href = mapy_href = tel_href = mail_href = "#kontakt"
    else:
        nav_href = "https://www.google.com/maps/dir/?api=1&destination=" + urllib.parse.quote(dotaz)
        mapy_href = "https://mapy.com/fnc/v1/search?query=" + urllib.parse.quote(dotaz)
        tel_href = tel["href"] if tel else ""
        mail_href = "mailto:" + email if email else ""

    # štítky pod tlačítky
    chips = []
    if souhrn:
        chips.append("<li>%s%s</li>" % (ikona("clock"), esc(cz(souhrn))))
    chips.append("<li>%s%s</li>" % (ikona("map-pin"), esc(data["lokalita"])))
    if rok:
        chips.append("<li>%sOd roku %d</li>" % (ikona("calendar-check"), rok))

    # otevírací doba
    rows = []
    for i, (_key, dlouhy, _kratky, _en) in enumerate(DNY):
        v = ints[i]
        if v == [(0, 1440)]:
            dd = "<dd>nonstop</dd>"
        elif v:
            dd = "<dd>%s</dd>" % "".join("<span>%s–%s%s</span>" % (fmt(a), fmt(b), "," if j < len(v) - 1 else "")
                                         for j, (a, b) in enumerate(v))
        else:
            dd = '<dd class="closed">zavřeno</dd>'
        rows.append('<div class="row" data-d="%d"><dt>%s</dt>%s</div>' % (i + 1, dlouhy, dd))

    # kontakty
    kontakty = []
    if tel:
        kontakty.append('<li><span class="ci">%s</span><div><span class="cl">Telefon</span><a class="cv" href="%s">%s</a></div></li>'
                        % (ikona("phone"), esc(tel_href), esc(tel["intl"])))
    if email:
        kontakty.append('<li><span class="ci">%s</span><div><span class="cl">E-mail</span><a class="cv" href="%s">%s</a></div></li>'
                        % (ikona("mail"), esc(mail_href), esc(email)))
    if souhrn:
        kontakty.append('<li><span class="ci">%s</span><div><span class="cl">Otevírací doba</span><a class="cv" href="#hodiny">%s</a></div></li>'
                        % (ikona("clock"), esc(cz(souhrn))))

    # patička: obchodní firma, sídlo, IČO, zápis (§ 435 OZ). U OSVČ se v ukázce adresa nezveřejňuje
    # (bývá to bydliště), jen když ji firma sama uvádí ("sidlo_zverejnit": true); ostrý web ji mít musí.
    if fikt:
        sidlo = data.get("sidlo") or "%s, %s %s" % (adr["ulice"], psc, adr["obec"])
    elif forma == "osvc" and not (ostry or data.get("sidlo_zverejnit")):
        sidlo = ""
    else:
        sidlo = data.get("sidlo", "")
    if forma == "osvc" and data.get("sidlo") and not (ostry or data.get("sidlo_zverejnit")):
        varovani.append('OSVČ: místo podnikání se v ukázce nezobrazí (zapni "sidlo_zverejnit", když ho firma sama uvádí)')

    b = barvy(barva)
    ini = inicialy(data["nazev"])
    fav = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='14' fill='%s'/>"
           "<text x='32' y='42' font-family='Arial,Helvetica,sans-serif' font-size='%d' font-weight='700' "
           "text-anchor='middle' fill='%s'>%s</text></svg>") % (b["btn_light"], 28 if len(ini) > 1 else 34,
                                                              b["btn_light_ink"], esc(ini))
    favicon = "data:image/svg+xml," + urllib.parse.quote(fav, safe=" '=:/,")

    obor_maly = obor[0].lower() + obor[1:] if len(obor) > 1 and obor[1].islower() else obor
    if obor.lower() in data["nazev"].lower():
        title = "%s – %s" % (data["nazev"], data["lokalita"])
    else:
        title = "%s – %s %s" % (data["nazev"], obor_maly, data["lokalita"])
    if not ostry:
        title = "Ukázka webu: " + title
    description = uvod + (" Telefon %s." % tel["display"].replace("\u00a0", " ") if tel else "")

    canonical = ""
    if ostry:
        canonical = "https://" + re.sub(r"^https?://", "", data["domena"]).strip("/") + "/"

    jsonld = ""
    if not fikt:
        ld = {"@context": "https://schema.org", "@type": "AutoRepair", "name": data["nazev"], "legalName": data["firma"],
              "address": {"@type": "PostalAddress", "streetAddress": adr["ulice"], "postalCode": psc,
                          "addressLocality": adr["obec"], "addressCountry": "CZ"}}
        if tel:
            ld["telephone"] = tel["ld"]
        if email:
            ld["email"] = email
        if rok:
            ld["foundingDate"] = str(rok)
        if canonical:
            ld["url"] = canonical
        spec = []
        for i, v in enumerate(ints):
            for a, b2 in v:
                spec.append({"@type": "OpeningHoursSpecification", "dayOfWeek": DNY[i][3],
                             "opens": "%02d:%02d" % divmod(a, 60),
                             "closes": "23:59" if b2 == 1440 else "%02d:%02d" % divmod(b2, 60)})
        ld["openingHoursSpecification"] = spec
        jsonld = (json.dumps(ld, ensure_ascii=False)
                  .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e"))

    sprite = ('<svg xmlns="http://www.w3.org/2000/svg" style="display:none">'
              + "".join('<symbol id="i-%s" viewBox="0 0 24 24">%s</symbol>' % (n, IKONY[n]) for n in sorted(pouzite))
              + "</svg>")
    licence = ik["_licence"].replace("--", "-")
    banner_text = BANNER_TEXT_FIKTIVNI if fikt else BANNER_TEXT
    banner = "" if ostry else BANNER.replace("@@TEXT@@", esc(banner_text))

    ctx = dict(b)
    ctx.update({
        "ukazka": not ostry, "canonical": canonical, "title": title, "description": description,
        "favicon": favicon, "jsonld": jsonld, "sprite": sprite, "nazev": data["nazev"], "inicialy": ini,
        "telefon": bool(tel), "tel_href": tel_href, "tel_display": tel["display"] if tel else "",
        "hero_mail": bool(email and not tel), "mail_href": mail_href,
        "eyebrow": "%s · %s" % (obor, data["lokalita"]), "h1": nadpis(data["nazev"]), "uvod_html": uvod_html,
        "nav_href": nav_href, "mapy_href": mapy_href, "chips": "".join(chips),
        "hodiny_rows": "".join(rows), "hodiny_pozn": cz(pozn), "svatky": svatky,
        "hodiny_json": json.dumps([[list(iv) for iv in d] for d in ints], separators=(",", ":")),
        "sekce_sluzby": bool(sl_html or data.get("znacky")), "sluzby": "".join(sl_html),
        "znacky": "".join("<li>%s</li>" % esc(z) for z in data.get("znacky", [])),
        "ulice": adr["ulice"], "psc_obec": "%s %s" % (psc, adr["obec"]), "kontakty": "".join(kontakty),
        "firma": data["firma"], "sidlo": sidlo, "sidlo_label": PRAVNI_FORMY[forma], "ico": ico,
        "rejstrik": cz(data.get("rejstrik", "")), "kredit": data.get("kredit", True),
        "lucide_licence": licence, "banner": banner, "banner_text": banner_text,
    })
    with open(os.path.join(HERE, "sablona-autoservis.html"), encoding="utf-8") as f:
        tpl = f.read()
    return vypln(tpl, ctx), varovani, zverejneno


def main(argv=None):
    ap = argparse.ArgumentParser(description="Vyrobí ukázkový web autoservisu z JSON dat.")
    ap.add_argument("data", help="cesta k JSON souboru s daty firmy")
    ap.add_argument("--ostry", action="store_true", help="ostrý web bez lišty ukázky (pro klienta)")
    ap.add_argument("--qr", action="store_true", help="QR kód na adresu zveřejněné ukázky")
    a = ap.parse_args(argv)
    try:
        with open(a.data, encoding="utf-8") as f:
            data = json.load(f)
        page, varovani, zverejneno = sestav(data, ostry=a.ostry)
    except (Chyba, json.JSONDecodeError, OSError) as e:
        print("CHYBA: %s" % e, file=sys.stderr)
        return 1
    except Exception as e:                       # cokoli nečekaného: srozumitelně a nic nezapsat
        print("CHYBA v datech nebo generátoru (%s: %s)" % (type(e).__name__, e), file=sys.stderr)
        return 1
    slug = data["slug"]
    if a.ostry:
        cil = os.path.join(HERE, "ostre", slug)
    elif data.get("fiktivni") or zverejneno:
        cil = os.path.join(VEREJNE, slug)
    else:
        cil = os.path.join(HERE, "nahled", slug)
    os.makedirs(cil, exist_ok=True)
    out = os.path.join(cil, "index.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print("Hotovo: %s (%d kB)" % (os.path.relpath(out, REPO), round(len(page.encode("utf-8")) / 1024)))
    verejne = os.path.dirname(cil) == VEREJNE
    if verejne:
        print("Po pushi: %s/ukazky/%s/%s" % (WEB, slug, ("  (zveřejnění: %s)" % zverejneno) if zverejneno else ""))
    elif a.ostry:
        print("Ostrý web: nahrát na doménu klienta.")
    else:
        print('Jen náhled, na web se nedostane (pro zveřejnění doplň "zverejneni").')
    for v in varovani:
        print("Pozor: " + v)
    if a.qr:
        if not verejne:
            print("QR: jen pro zveřejněnou ukázku (jinak by vedl na neexistující stránku).", file=sys.stderr)
            return 1
        try:
            import qrcode
        except ImportError:
            print("QR: chybí knihovna qrcode (pip install qrcode[pil])", file=sys.stderr)
            return 1
        url = "%s/ukazky/%s/" % (WEB, slug)
        os.makedirs(os.path.join(HERE, "nahled"), exist_ok=True)
        qpath = os.path.join(HERE, "nahled", slug + "-qr.png")
        q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=4)
        q.add_data(url)
        q.make(fit=True)
        q.make_image(fill_color="black", back_color="white").save(qpath)
        print("QR: %s -> %s" % (os.path.relpath(qpath, REPO), url))
    return 0


if __name__ == "__main__":
    sys.exit(main())
