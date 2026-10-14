#!/usr/bin/env python3
"""Generátor ukázkových webů pro autoservisy (Kudli. marketing).

Použití:
  python3 generator.py data/<slug>.json             ukázka (lišta „ukázka“ + noindex)
  python3 generator.py data/<slug>.json --qr        navíc QR kód na adresu ukázky (PNG do nahled/)
  python3 generator.py data/<slug>.json --ostry     ostrý web pro klienta (bez lišty, indexovatelný)

Kam se zapíše výsledek:
  * vymyšlená firma ("fiktivni": true) nebo firma s vyplněným "zverejneni"
      -> <repo>/ukazky/<slug>/index.html   (po pushi na www.kudlimarketing.cz/ukazky/<slug>/)
  * ostatní -> _nastroje/ukazky/nahled/<slug>/index.html   (jen náhled, není v gitu ani na webu)
  * --ostry -> _nastroje/ukazky/ostre/<slug>/index.html    (nahrává se na vlastní doménu klienta)

Pravidla pro data skutečných firem (generátor je vynucuje, co jde):
  * jen fakta z veřejného rejstříku (ARES) a z toho, co firma sama zveřejňuje (vlastní web, firmy.cz);
  * žádné texty ani fotky převzaté z cizích webů, žádné recenze, ceny ani sliby;
  * "zdroje" (odkazy, odkud fakta jsou) a "overeno" (datum kontroly) jsou povinné;
  * "zverejneni" vyplnit jen tehdy, když firma o ukázku požádala, nebo to schválil Ondra.
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
WEB = "https://www.kudlimarketing.cz"

DNY = [("po", "Pondělí", "Po", "Monday"), ("ut", "Úterý", "Út", "Tuesday"), ("st", "Středa", "St", "Wednesday"),
       ("ct", "Čtvrtek", "Čt", "Thursday"), ("pa", "Pátek", "Pá", "Friday"), ("so", "Sobota", "So", "Saturday"),
       ("ne", "Neděle", "Ne", "Sunday")]

# klíč: (název, popis, ikona, tvar do úvodní věty)
SLUZBY = {
    "servis": ("Servis a údržba", "Pravidelné prohlídky, výměna oleje a filtrů.", "wrench", "servis"),
    "opravy": ("Mechanické opravy", "Motor, podvozek, řízení, výfuk.", "settings", "opravy"),
    "brzdy": ("Brzdy", "Destičky, kotouče, brzdová kapalina.", "disc-3", "opravy brzd"),
    "diagnostika": ("Diagnostika", "Načtení a vymazání chybových kódů, kontrola řídicích jednotek.", "activity", "diagnostika"),
    "pneuservis": ("Pneuservis", "Přezutí, vyvážení kol, oprava defektu.", "life-buoy", "pneuservis"),
    "uskladneni": ("Uskladnění pneumatik", "Sezónní sadu pneumatik uložíme do příštího přezutí.", "warehouse", "uskladnění pneumatik"),
    "prodej_pneu": ("Prodej pneumatik", "Letní, zimní i celoroční pneumatiky.", "package", "prodej pneumatik"),
    "klimatizace": ("Klimatizace", "Plnění, kontrola těsnosti, dezinfekce.", "snowflake", "servis klimatizací"),
    "geometrie": ("Geometrie", "Měření a seřízení geometrie náprav.", "crosshair", "geometrie"),
    "stk": ("Příprava na STK", "Prohlídka a opravy před technickou kontrolou.", "clipboard-check", "příprava na STK"),
    "elektro": ("Autoelektrika", "Elektroinstalace, startéry, alternátory, osvětlení.", "zap", "autoelektrika"),
    "baterie": ("Autobaterie", "Kontrola a výměna akumulátoru.", "battery-charging", "výměna autobaterií"),
    "karoserie": ("Karosářské práce", "Opravy karoserie po nehodě i drobných poškození.", "hammer", "karosářské práce"),
    "lakovani": ("Lakování", "Lakování dílů i celých vozů.", "spray-can", "lakování"),
    "pojistne": ("Pojistné události", "Opravy vozů po nehodě hrazené pojišťovnou.", "shield-check", "opravy z pojištění"),
    "autoskla": ("Autoskla", "Výměna a oprava čelních skel.", "car-front", "výměna autoskel"),
    "tazne": ("Tažná zařízení", "Montáž tažného zařízení včetně elektroinstalace.", "caravan", "montáž tažných zařízení"),
    "odtah": ("Odtahová služba", "Odtah nepojízdného vozu.", "truck", "odtahová služba"),
    "spojky": ("Spojky a převodovky", "Výměna spojky, opravy převodovek.", "cog", "opravy spojek a převodovek"),
    "rozvody": ("Rozvody", "Výměna rozvodového řemene nebo řetězu.", "link", "výměna rozvodů"),
    "vyfuky": ("Výfuky", "Opravy a výměna výfukového systému.", "wind", "opravy výfuků"),
    "uzitkova": ("Užitková vozidla", "Servis dodávek a užitkových aut.", "bus", "servis užitkových vozů"),
    "lpg": ("LPG a CNG", "Servis plynových zařízení.", "fuel", "servis LPG a CNG"),
    "olej": ("Výměna oleje", "Motorový olej a filtry podle předpisu výrobce.", "droplet", "výměna oleje"),
    "cisteni": ("Čištění interiéru", "Tepování sedaček a čištění interiéru.", "sparkles", "čištění interiéru"),
    "ozon": ("Ozonové čištění", "Odstranění pachů z interiéru a klimatizace.", "wind", "ozonové čištění"),
}

UI_IKONY = {"phone", "map-pin", "clock", "navigation", "mail", "calendar-check"}
NEVYZNAMNA = {"a", "u", "na", "v", "ve", "s", "se", "z", "ze", "k", "ke", "do", "pod", "nad", "za", "pro", "o", "i",
              "s.r.o.", "spol.", "r.o.", "a.s.", "k.s.", "v.o.s.", "&"}

BANNER = """<!-- kudli-demo:start -->
<div id="kudli-demo-banner" role="note" lang="cs" style="all:initial;box-sizing:border-box;display:block;position:fixed;left:0;right:0;bottom:0;z-index:2147483647;width:100%;margin:0;padding:9px 16px calc(9px + env(safe-area-inset-bottom, 0px));background:#14181c;color:#f3f4f6;font:500 13px/1.45 system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;text-align:center;border-top:1px solid rgba(255,255,255,.16);box-shadow:0 -2px 12px rgba(0,0,0,.25)">@@TEXT@@ Připravil <a href="https://www.kudlimarketing.cz/" target="_blank" rel="noopener" style="all:initial;font:inherit;color:#ffffff;text-decoration:underline;cursor:pointer">Kudli.&nbsp;marketing</a>.</div>
<script>(function(){try{var b=document.getElementById('kudli-demo-banner');if(!b)return;var d=document.body,t=0;function fit(){var h=b.offsetHeight||0,vh=window.innerHeight||0;d.style.removeProperty('padding-bottom');var base=parseFloat(getComputedStyle(d).paddingBottom)||0;d.style.setProperty('padding-bottom',(base+h)+'px','important');var els=d.getElementsByTagName('*');for(var i=0;i<els.length;i++){var el=els[i];if(el===b||b.contains(el))continue;var o=el.getAttribute('data-kudli-bottom');if(o===null){var cs=getComputedStyle(el);if(cs.position!=='fixed')continue;var r=el.getBoundingClientRect();if(!r.width||!r.height||r.top<vh*0.5||r.bottom<vh-160)continue;o=parseFloat(cs.bottom);if(isNaN(o))continue;el.setAttribute('data-kudli-bottom',String(o));}el.style.setProperty('bottom',(parseFloat(o)+h)+'px','important');}}function later(){clearTimeout(t);t=setTimeout(fit,150);}fit();window.addEventListener('load',fit);window.addEventListener('resize',later);window.addEventListener('scroll',later,{passive:true});setTimeout(fit,1200);setTimeout(fit,3500);}catch(e){}})();</script>
<!-- kudli-demo:end -->
"""
BANNER_TEXT = "Nezávazná ukázka webu, nejde o oficiální stránky firmy."
BANNER_TEXT_FIKTIVNI = "Ukázka šablony, firma je vymyšlená."


class Chyba(Exception):
    pass


def esc(s):
    return html.escape(str(s), quote=True)


# ---------- barvy ----------

def _rgb(hexa):
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", hexa or "")
    if not m:
        raise Chyba("barva musí být ve tvaru #rrggbb, ne %r" % hexa)
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


def barvy(hexa):
    """Odvodí z hlavní barvy odstíny tak, aby text všude splnil kontrast WCAG AA (4,5 : 1)."""
    a = _rgb(hexa)
    white, black, ink = (255, 255, 255), (17, 17, 17), (14, 17, 22)
    ink_text = "#ffffff" if kontrast(a, white) >= 4.5 else "#111111"
    if ink_text == "#111111" and kontrast(a, black) < 4.5:
        ink_text = "#ffffff" if kontrast(a, white) >= kontrast(a, black) else "#111111"
    na_svetle = a
    t = 0.0
    while kontrast(na_svetle, white) < 4.5 and t < 1:
        t += 0.05
        na_svetle = _mix(a, (0, 0, 0), t)
    na_tmave = a
    t = 0.0
    while kontrast(na_tmave, ink) < 4.5 and t < 1:
        t += 0.05
        na_tmave = _mix(a, white, t)
    return {
        "accent": _hex(a),
        "accent_ink": ink_text,
        "accent_text": _hex(na_svetle),
        "accent_dark": _hex(na_tmave),
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
    cisla = re.sub(r"[^\d+]", "", t or "")
    if cisla.startswith("00"):
        cisla = "+" + cisla[2:]
    if re.fullmatch(r"\d{9}", cisla):
        cisla = "+420" + cisla
    m = re.fullmatch(r"\+420(\d{9})", cisla)
    if m:
        n = m.group(1)
        mistni = "\u00a0".join((n[:3], n[3:6], n[6:]))       # nedělitelné mezery: číslo se nezalomí
        return {"href": "tel:+420" + n, "display": mistni, "intl": "+420\u00a0" + mistni}
    if re.fullmatch(r"\+\d{8,15}", cisla):
        hezky = re.sub(r"\s+", "\u00a0", t.strip())
        return {"href": "tel:" + cisla, "display": hezky, "intl": hezky}
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


def hodiny(data):
    h = data.get("hodiny")
    if not isinstance(h, dict):
        raise Chyba('chybí "hodiny" (otevírací doba pro po, ut, st, ct, pa, so, ne)')
    navic = set(h) - {d[0] for d in DNY}
    if navic:
        raise Chyba("neznámé dny v hodinách: %s" % ", ".join(sorted(navic)))
    out = []
    for key, *_ in DNY:
        if key not in h:
            raise Chyba('v "hodiny" chybí den "%s" (zavřeno = [])' % key)
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
    for a, b, v in skupiny(ints):
        if not v:
            continue
        dny = DNY[a][2] if a == b else "%s–%s" % (DNY[a][2], DNY[b][2])
        text = "%s %s–%s" % (dny, fmt(v[0][0]), fmt(v[-1][1]))
        return text + (" s přestávkou" if len(v) > 1 else "")
    return ""


# ---------- šablona ----------

def vypln(tpl, ctx):
    def blok(m):
        return m.group(2) if ctx.get(m.group(1)) else ""
    prev = None
    while prev != tpl:
        prev = tpl
        tpl = re.sub(r"<!--\?(\w+)-->(.*?)<!--/\?\1-->\n?", blok, tpl, flags=re.S)
    misto = re.compile(r"\{\{\{(\w+)\}\}\}|\{\{(\w+)\}\}")
    # kontrola šablony před dosazením (dosazený obsah se už neprohledává)
    bez_mist = misto.sub("", tpl)
    zbytek = re.findall(r"\{\{|<!--/?\?\w*-->", bez_mist)
    if zbytek:
        raise Chyba("šablona má neuzavřený blok nebo vadné místo: %s" % zbytek[:3])
    chybi = sorted({k for m in misto.finditer(tpl) for k in m.groups() if k and k not in ctx})
    if chybi:
        raise Chyba("šablona chce hodnoty, které generátor nezná: %s" % ", ".join(chybi))

    def dosad(m):
        return str(ctx[m.group(1)]) if m.group(1) else esc(ctx[m.group(2)])
    return misto.sub(dosad, tpl)


def ikona(n, cls="i"):
    return '<svg class="%s" aria-hidden="true"><use href="#i-%s"/></svg>' % (cls, n)


def inicialy(nazev):
    slova = [w for w in re.split(r"\s+", nazev) if w and w.lower() not in NEVYZNAMNA]
    pis = [w[0] for w in slova if w[0].isalpha()]
    return ("".join(pis[:2]) or nazev[:1]).upper()


def sestav(data, ostry=False):
    fikt = bool(data.get("fiktivni"))
    for k in ("slug", "nazev", "firma", "lokalita", "kde", "adresa"):
        if not data.get(k):
            raise Chyba('chybí povinné pole "%s"' % k)
    slug = data["slug"]
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,58})[a-z0-9]", slug):
        raise Chyba("slug smí mít jen malá písmena bez diakritiky, číslice a pomlčky (3–60 znaků)")
    adr = data["adresa"]
    for k in ("ulice", "psc", "obec"):
        if not adr.get(k):
            raise Chyba('v "adresa" chybí "%s"' % k)
    if not re.fullmatch(r"\d{3} ?\d{2}", adr["psc"]):
        raise Chyba("PSČ musí mít 5 číslic, ne %r" % adr["psc"])
    psc = re.sub(r"^(\d{3}) ?(\d{2})$", r"\1 \2", adr["psc"])
    varovani = []
    if not fikt:
        if not data.get("zdroje"):
            raise Chyba('u skutečné firmy jsou povinné "zdroje" (odkazy, odkud fakta jsou)')
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data.get("overeno", ""))):
            raise Chyba('u skutečné firmy je povinné "overeno" (datum kontroly faktů, RRRR-MM-DD)')
        if not data.get("ico"):
            raise Chyba('u skutečné firmy je povinné "ico"')
    ico = str(data.get("ico", "")).replace(" ", "")
    if ico and not fikt and not ico_platne(ico):
        raise Chyba("IČO %s nemá platný kontrolní součet, zkontroluj ho v ARES" % ico)
    if not data.get("telefon") and not data.get("email"):
        raise Chyba("firma musí mít aspoň telefon nebo e-mail")
    tel = telefon(data["telefon"]) if data.get("telefon") else None
    email = data.get("email", "")
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", email, flags=re.I):
        raise Chyba("neplatný e-mail %r" % email)
    rok = data.get("zalozeno")
    if rok is not None and not (isinstance(rok, int) and 1900 <= rok <= dt.date.today().year):
        raise Chyba('"zalozeno" musí být rok, např. 2009')
    ints = hodiny(data)
    souhrn = souhrn_hodin(ints)
    svatky = data.get("svatky", "")
    if svatky not in ("", "zavreno", "otevreno"):
        raise Chyba('"svatky" může být "zavreno", "otevreno", nebo chybět (když to nevíme)')
    pozn = data.get("hodiny_pozn", "")
    if svatky == "zavreno" and "svát" not in pozn.lower():
        pozn = ("Ve státní svátky zavřeno. " + pozn).strip()
    if not data.get("sluzby"):
        varovani.append("bez služeb: sekce Služby se nezobrazí")
    if ostry and not data.get("domena"):
        raise Chyba('ostrý web potřebuje "domena" (např. www.autoservis-novak.cz)')

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
            zaklad = SLUZBY.get(s.get("klic", ""), (None, None, "wrench", None))
            nazev_s = s.get("nazev") or zaklad[0]
            popis = s.get("popis") or zaklad[1]
            ico_s = s.get("ikona") or zaklad[2]
            veta = s.get("veta") or zaklad[3]
            if not nazev_s or not popis:
                raise Chyba("vlastní služba potřebuje nazev a popis: %r" % s)
        else:
            raise Chyba("služba musí být klíč nebo objekt, ne %r" % s)
        if ico_s not in IKONY:
            raise Chyba("neznámá ikona %r" % ico_s)
        pouzite.add(ico_s)
        if veta:
            vety.append(veta)
        sl_html.append('<li class="svc"><span class="svc-ico">%s</span><div><h3>%s</h3><p>%s</p></div></li>'
                       % (ikona(ico_s), esc(nazev_s), esc(popis)))

    obor = data.get("obor", "Autoservis")
    if data.get("uvod"):
        uvod = data["uvod"]
        uvod_html = esc(uvod)
    else:
        if vety:
            v = vety[:3]
            spoj = v[0] if len(v) == 1 else ", ".join(v[:-1]) + " a " + v[-1]
            zacatek = spoj[0].upper() + spoj[1:]
        else:
            zacatek = obor
        uvod = "%s %s." % (zacatek, data["kde"])
        # místo se nezalomí uprostřed (např. „v Brně-/Líšni“)
        uvod_html = '%s <span class="nw">%s</span>.' % (esc(zacatek), esc(data["kde"]))

    # nadpis s barevným posledním slovem
    slova = data["nazev"].split()
    h1 = esc(data["nazev"]) if len(slova) < 2 else esc(" ".join(slova[:-1])) + ' <span class="hl">%s</span>' % esc(slova[-1])

    # odkazy na mapu
    dotaz = data.get("mapa_dotaz") or "%s, %s %s" % (adr["ulice"], psc, adr["obec"])
    if fikt:
        nav_href = mapy_href = "#kontakt"
        ext = ""
        tel_href = "#kontakt"
    else:
        nav_href = "https://www.google.com/maps/dir/?api=1&destination=" + urllib.parse.quote(dotaz)
        mapy_href = "https://mapy.com/fnc/v1/search?query=" + urllib.parse.quote(dotaz)
        ext = ' target="_blank" rel="noopener"'
        tel_href = tel["href"] if tel else ""

    # štítky pod tlačítky
    chips = []
    if souhrn:
        chips.append("<li>%s%s</li>" % (ikona("clock"), esc(souhrn)))
    chips.append("<li>%s%s</li>" % (ikona("map-pin"), esc(data["lokalita"])))
    if rok:
        chips.append("<li>%sOd roku %d</li>" % (ikona("calendar-check"), rok))

    # otevírací doba
    rows = []
    for i, (key, dlouhy, kratky, _en) in enumerate(DNY):
        v = ints[i]
        dd = ("<dd>%s</dd>" % "".join("<span>%s–%s%s</span>" % (fmt(a), fmt(b), "," if j < len(v) - 1 else "")
                                      for j, (a, b) in enumerate(v))) if v \
            else '<dd class="closed">zavřeno</dd>'
        rows.append('<div class="row" data-d="%d"><dt>%s</dt>%s</div>' % (i + 1, dlouhy, dd))

    # kontakty
    kontakty = []
    if tel:
        kontakty.append('<li><span class="ci">%s</span><div><span class="cl">Telefon</span><a class="cv" href="%s">%s</a></div></li>'
                        % (ikona("phone"), esc(tel_href), esc(tel["intl"])))
    if email:
        mail_href = "#kontakt" if fikt else "mailto:" + email
        kontakty.append('<li><span class="ci">%s</span><div><span class="cl">E-mail</span><a class="cv" href="%s">%s</a></div></li>'
                        % (ikona("mail"), esc(mail_href), esc(email)))
    if souhrn:
        kontakty.append('<li><span class="ci">%s</span><div><span class="cl">Otevírací doba</span><a class="cv" href="#hodiny">%s</a></div></li>'
                        % (ikona("clock"), esc(souhrn)))

    # patička: sídlo (u OSVČ jen když je výslovně zadané, ať se nezveřejní adresa bydliště)
    forma = data.get("pravni_forma", "sro")
    if data.get("sidlo"):
        sidlo = data["sidlo"]
    elif forma == "osvc":
        sidlo = ""
    else:
        sidlo = "%s, %s %s" % (adr["ulice"], psc, adr["obec"])
    sidlo_label = "místo podnikání" if forma == "osvc" else "sídlo"

    b = barvy(data.get("barva", "#d0312d"))
    ini = inicialy(data["nazev"])
    fav = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='14' fill='%s'/>"
           "<text x='32' y='42' font-family='Arial,Helvetica,sans-serif' font-size='%d' font-weight='700' "
           "text-anchor='middle' fill='%s'>%s</text></svg>") % (b["accent"], 28 if len(ini) > 1 else 34, b["accent_ink"], esc(ini))
    favicon = "data:image/svg+xml," + urllib.parse.quote(fav, safe=" '=:/,")

    if obor.lower() in data["nazev"].lower():
        title = "%s – %s" % (data["nazev"], data["lokalita"])
    else:
        title = "%s – %s %s" % (data["nazev"], obor.lower(), data["lokalita"])
    description = uvod + (" Telefon %s." % tel["display"] if tel else "")

    canonical = ""
    if ostry:
        canonical = "https://" + re.sub(r"^https?://", "", data["domena"]).strip("/") + "/"

    jsonld = ""
    if not fikt:
        ld = {"@context": "https://schema.org", "@type": "AutoRepair", "name": data["nazev"], "legalName": data["firma"],
              "address": {"@type": "PostalAddress", "streetAddress": adr["ulice"], "postalCode": psc,
                          "addressLocality": adr["obec"], "addressCountry": "CZ"}}
        if tel:
            ld["telephone"] = tel["intl"]
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
                             "opens": "%02d:%02d" % divmod(a, 60), "closes": "%02d:%02d" % divmod(b2, 60)})
        ld["openingHoursSpecification"] = spec
        jsonld = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")

    sprite = ('<svg xmlns="http://www.w3.org/2000/svg" style="display:none">'
              + "".join('<symbol id="i-%s" viewBox="0 0 24 24">%s</symbol>' % (n, IKONY[n]) for n in sorted(pouzite))
              + "</svg>")
    licence = ik["_licence"].replace("--", "-")

    if ostry:
        banner = ""
    else:
        banner = BANNER.replace("@@TEXT@@", esc(BANNER_TEXT_FIKTIVNI if fikt else BANNER_TEXT))

    ctx = dict(b)
    ctx.update({
        "robots": not ostry, "canonical": canonical, "title": title, "description": description,
        "favicon": favicon, "jsonld": jsonld, "sprite": sprite, "nazev": data["nazev"], "inicialy": ini,
        "telefon": bool(tel), "tel_href": tel_href, "tel_display": tel["display"] if tel else "",
        "eyebrow": "%s · %s" % (obor, data["lokalita"]), "h1": h1, "uvod": uvod,
        "nav_href": nav_href, "mapy_href": mapy_href, "ext": ext, "chips": "".join(chips),
        "hodiny_rows": "".join(rows), "hodiny_pozn": pozn, "svatky": svatky,
        "hodiny_json": json.dumps([[list(iv) for iv in d] for d in ints], separators=(",", ":")),
        "uvod_html": uvod_html,
        "sluzby": "".join(sl_html), "znacky": "".join("<li>%s</li>" % esc(z) for z in data.get("znacky", [])),
        "ulice": adr["ulice"], "psc_obec": "%s %s" % (psc, adr["obec"]), "kontakty": "".join(kontakty),
        "firma": data["firma"], "sidlo": sidlo, "sidlo_label": sidlo_label, "ico": ico,
        "rejstrik": data.get("rejstrik", ""), "kredit": data.get("kredit", True),
        "lucide_licence": licence, "banner": banner,
    })
    with open(os.path.join(HERE, "sablona-autoservis.html"), encoding="utf-8") as f:
        tpl = f.read()
    return vypln(tpl, ctx), varovani


def main(argv=None):
    ap = argparse.ArgumentParser(description="Vyrobí ukázkový web autoservisu z JSON dat.")
    ap.add_argument("data", help="cesta k JSON souboru s daty firmy")
    ap.add_argument("--ostry", action="store_true", help="ostrý web bez lišty ukázky (pro klienta)")
    ap.add_argument("--qr", action="store_true", help="vytvořit QR kód na adresu ukázky")
    a = ap.parse_args(argv)
    try:
        with open(a.data, encoding="utf-8") as f:
            data = json.load(f)
        page, varovani = sestav(data, ostry=a.ostry)
    except (Chyba, json.JSONDecodeError, OSError) as e:
        print("CHYBA: %s" % e, file=sys.stderr)
        return 1
    slug = data["slug"]
    if a.ostry:
        cil = os.path.join(HERE, "ostre", slug)
    elif data.get("fiktivni") or data.get("zverejneni"):
        cil = os.path.join(REPO, "ukazky", slug)
    else:
        cil = os.path.join(HERE, "nahled", slug)
    os.makedirs(cil, exist_ok=True)
    out = os.path.join(cil, "index.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print("Hotovo: %s (%d kB)" % (os.path.relpath(out, REPO), round(len(page.encode("utf-8")) / 1024)))
    if cil.startswith(os.path.join(REPO, "ukazky")):
        print("Po pushi: %s/ukazky/%s/" % (WEB, slug))
    else:
        print("Jen náhled, na web se nedostane." if not a.ostry else "Ostrý web: nahrát na doménu klienta.")
    for v in varovani:
        print("Pozor: " + v)
    if a.qr:
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
