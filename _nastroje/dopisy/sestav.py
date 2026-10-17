"""Dopisy pro autoservisy: z firmy.json vyrobí HTML (A4) pro každý dopis. PDF z nich udělá pdf.js.
Adresy podle vzoru PostServis (VzorAdresy.pdf): odesílatel x 19,5 mm / y 9,7 mm, adresát x 121,6 mm / y 53,9 mm."""
import html, json, re, sys
from pathlib import Path
from urllib.parse import urlencode
import qrcode

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "html"
OUT.mkdir(exist_ok=True)
DATUM = "19. 10. 2026"
BASE = "https://www.kudlimarketing.cz/ukazka-zdarma"
NBSP = " "


def cz(t: str) -> str:
    """Nezlomitelná mezera po jednopísmenných slovech a v „8 000 Kč“, pak escapování."""
    t = re.sub(r"(?<![\w])([ksvzouaiKSVZOUAI]) ", lambda m: m.group(1) + NBSP, t)
    t = t.replace("8 000 Kč", f"8{NBSP}000{NBSP}Kč")
    return html.escape(t, quote=False)


def qr_svg(data: str) -> tuple[str, int]:
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    q.add_data(data)
    q.make(fit=True)
    m = q.get_matrix()
    n = len(m)
    parts = []
    for y, row in enumerate(m):
        x = 0
        while x < n:
            if row[x]:
                s = x
                while x < n and row[x]:
                    x += 1
                parts.append(f"M{s} {y}h{x - s}v1h-{x - s}z")
            else:
                x += 1
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges" '
           f'role="img" aria-label="QR kód"><path d="{"".join(parts)}" fill="#111"/></svg>')
    return svg, q.version


def url_pro(f: dict) -> str:
    p = [("z", "dopis-" + f["kod"]), ("f", f["firma"])]
    if f["web"]:
        p.append(("w", f["web"]))
    p.append(("o", f["obor"]))
    return BASE + "?" + urlencode(p) + "#zadost"


FONTDIR = ROOT / "fonty" / "node_modules" / "@fontsource" / "inter"
FONTY = "".join(f'<link rel="stylesheet" href="{(FONTDIR / w).as_uri()}">' for w in ("400.css", "600.css", "800.css"))

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 210mm; height: 297mm; }
body { position: relative; font-family: Inter, "DejaVu Sans", sans-serif; color: #16181d; font-size: 10.4pt;
       line-height: 1.47; -webkit-print-color-adjust: exact; print-color-adjust: exact; background: #fff; }
.abs { position: absolute; }
.odesilatel { left: 19.5mm; top: 9.7mm; font-size: 9.6pt; line-height: 14.2pt; }
.odesilatel b { font-weight: 600; }
.znacka { right: 20mm; top: 10mm; font-size: 13pt; font-weight: 800; letter-spacing: -0.02em; }
.znacka span { color: #d0312d; }
.adresat { left: 121.6mm; top: 53.9mm; width: 64mm; font-size: 10.6pt; line-height: 14.4pt; }
.datum { right: 22mm; top: 85mm; font-size: 10pt; color: #3b4048; }
.text { left: 25mm; top: 99mm; width: 161mm; }
.text p { margin-bottom: 2.6mm; }
.podpis { margin-top: 4mm; }
.text .podpis p { margin-bottom: 0; }
.podpis .jm { font-weight: 600; margin-top: 5mm; }
.ukazka { left: 25mm; top: 203mm; width: 118mm; height: 66mm; }
.pc { position: absolute; left: 0; top: 0; width: 104mm; border-radius: 2.2mm; overflow: hidden;
      border: 0.3mm solid #c9ccd2; background: #f3f4f6; }
.pc .lista { height: 4.2mm; display: flex; align-items: center; gap: 1.1mm; padding-left: 2.2mm; background: #e9eaee; }
.pc .lista i { width: 1.6mm; height: 1.6mm; border-radius: 50%; background: #c3c6cc; display: block; }
.pc img { display: block; width: 100%; }
.mobil { position: absolute; left: 88mm; top: 13mm; width: 27mm; border-radius: 3.6mm; overflow: hidden;
         border: 1.1mm solid #1d1f24; background: #1d1f24; }
.mobil img { display: block; width: 100%; }
.popisek { left: 25mm; top: 266.5mm; width: 118mm; font-size: 8.2pt; color: #4a4f57; }
.qr { left: 150mm; top: 203mm; width: 36mm; text-align: center; }
.qr .kod { width: 30mm; height: 30mm; margin: 0 auto; }
.qr .kod svg { width: 100%; height: 100%; display: block; }
.qr .t1 { font-size: 9pt; font-weight: 600; margin-top: 2.2mm; line-height: 1.3; }
.qr .t2 { font-size: 8pt; color: #4a4f57; margin-top: 1mm; line-height: 1.3; }
.pata { left: 25mm; top: 281mm; width: 161mm; font-size: 7.8pt; color: #5b616a; border-top: 0.25mm solid #e1e3e7; padding-top: 2mm; }
"""


def dopis(f: dict) -> str:
    url = url_pro(f)
    svg, verze = qr_svg(url)
    if verze > 10:
        sys.exit(f"QR pro {f['kod']} je moc hustý (verze {verze}), zkrať adresu.")
    pc = (ROOT / "vzor-pc-crop.png").as_uri()
    mob = (ROOT / "vzor-mobil-crop.png").as_uri()
    adresa = "<br>".join(html.escape(x) for x in [f["firma"], *f["adresa"]])
    odstavce = [
        "Dobrý den,",
        "jmenuji se Ondřej Kudlička a dělám weby pro menší firmy v Brně. " + f["veta"],
        "Rád vám zdarma a nezávazně připravím ukázku nového webu přímo pro vaši firmu. Jak taková ukázka vypadá, "
        "vidíte na obrázku dole: je to web vymyšleného autoservisu, který jsem udělal jako vzor. Funguje na mobilu "
        "i na počítači, má kontakty, služby a otevírací dobu a zákazníkům ukáže, jestli máte právě otevřeno.",
        "Když se vám ukázka bude líbit, web stojí od 8 000 Kč (nejsem plátce DPH). Když ne, nic neplatíte "
        "a nic dalšího vám posílat nebudu.",
        "O ukázku si řeknete přes QR kód vpravo dole, kde už je název vaší firmy vyplněný, nebo na adrese "
        "kudlimarketing.cz/ukazka-zdarma.",
    ]
    body = "".join(f"<p>{cz(o)}</p>" for o in odstavce)
    return f"""<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><title>Dopis – {html.escape(f['firma'])}</title>{FONTY}<style>{CSS}</style></head>
<body>
<div class="abs odesilatel"><b>Ondřej Kudlička – Kudli. marketing</b><br>Hubrova 2263/7<br>628 00 Brno<br>IČO 07271751</div>
<div class="abs znacka">Kudli<span>.</span></div>
<div class="abs adresat">{adresa}</div>
<div class="abs datum">V Brně {DATUM}</div>
<div class="abs text">{body}
<div class="podpis"><p>S pozdravem</p><p class="jm">Ondřej Kudlička</p><p>o.kudlicka@gmail.com</p></div></div>
<div class="abs ukazka">
  <div class="pc"><div class="lista"><i></i><i></i><i></i></div><img src="{pc}" alt=""></div>
  <div class="mobil"><img src="{mob}" alt=""></div>
</div>
<div class="abs popisek">{cz("Vzor: web vymyšleného autoservisu Klíč a kolo, který si můžete prohlédnout na kudlimarketing.cz/ukazky/klic-a-kolo.")}</div>
<div class="abs qr"><div class="kod">{svg}</div>
  <p class="t1">{cz("Ukázka pro " + f["kratce"])}</p><p class="t2">{cz("Naskenujte fotoaparátem v telefonu.")}</p></div>
<div class="abs pata">{cz("Pokud ode mě nechcete dostávat další dopisy, napište mi na o.kudlicka@gmail.com a už vám nic nepošlu.")}</div>
</body></html>"""


def main():
    firmy = json.loads((ROOT / "firmy.json").read_text(encoding="utf-8"))
    for f in firmy:
        (OUT / f"dopis-{f['kod']}.html").write_text(dopis(f), encoding="utf-8")
        print(f["kod"], url_pro(f), sep="\t")


if __name__ == "__main__":
    main()
