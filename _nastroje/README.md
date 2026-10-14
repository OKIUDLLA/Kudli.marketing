# Nástroje (nejsou na webu)

Složka `_nastroje/` se na www.kudlimarketing.cz nezobrazuje: `netlify.toml` na ni vrací 404.
Repozitář je na GitHubu **veřejný**, proto sem nepatří hesla ani data skutečných firem, které ukázku ještě nedostaly.

| Nástroj | K čemu |
|---|---|
| `ukazky/generator.py` | Z JSON dat vyrobí ukázkový web autoservisu (šablona `ukazky/sablona-autoservis.html`). |
| `oznacit_demo.py` | Do hotového dema v samostatném repu doplní spodní lištu „Nezávazná ukázka webu…“ a zákaz indexování. |

## Ukázka pro autoservis

```bash
cd _nastroje/ukazky
cp data/klic-a-kolo.json data/novak.json   # a vyplnit fakta firmy
python3 generator.py data/novak.json         # náhled: nahled/novak/index.html
```

Náhled se otevře v prohlížeči přímo ze souboru. Na web se nedostane, dokud v datech není `"zverejneni"`.

### Pravidla pro data
- Fakta jen z ARES (název, sídlo, IČO, rok vzniku, zápis v rejstříku) a z toho, co firma sama zveřejňuje (vlastní web, firmy.cz): telefon, e-mail, otevírací doba, služby, značky.
- Žádné texty ani fotky z cizích webů, žádné recenze, ceny, sliby („do 24 hodin“, „nejlepší“). Popisy služeb bere generátor ze svého katalogu.
- `"zdroje"` (odkazy, odkud fakta jsou) a `"overeno"` (datum kontroly) jsou u skutečné firmy povinné, generátor bez nich nic nevyrobí. Kontroluje i kontrolní součet IČO.
- U OSVČ (`"pravni_forma": "osvc"`) se do patičky nedává adresa (bývá to bydliště), jen jméno a IČO.
- Data skutečné firmy neukládat do gitu (`.gitignore` je hlídá). Trvalá kopie patří do projektu GOD WEB, dokument `ukazky-data/<slug>.json`.

### Zveřejnění a smazání
1. Firma o ukázku požádala (formulář na /ukazka-zdarma), nebo ji Ondra schválil. Do dat dopsat `"zverejneni": "žádost z formuláře 15. 10. 2026"` (nebo kdo a kdy schválil).
2. `python3 generator.py data/novak.json --qr` → `ukazky/novak/index.html` + QR kód v `nahled/`.
3. Commit a push do `main` → za minutu běží na `https://www.kudlimarketing.cz/ukazky/novak/`.
   Každá ukázka má lištu „Nezávazná ukázka webu, nejde o oficiální stránky firmy“, `noindex` v HTML i v hlavičce (`netlify.toml`).
4. Smazání: odstranit složku `ukazky/novak/` a pushnout.

### Ostrý web pro klienta
`python3 generator.py data/novak.json --ostry` (v datech `"domena": "www.autoservis-novak.cz"`) → `ostre/novak/index.html` bez lišty a s povoleným indexováním. Nahrává se na doménu klienta.

### Pole v datech
| Pole | Povinné | Příklad / poznámka |
|---|---|---|
| `slug` | ano | `autoservis-novak` (adresa ukázky) |
| `nazev` | ano | `Autoservis Novák` (co je velkým písmem nahoře) |
| `firma` | ano | `Autoservis Novák s.r.o.` (obchodní firma do patičky) |
| `lokalita` | ano | `Brno-Židenice` (1. pád) |
| `kde` | ano | `v Brně-Židenicích` (6. pád s předložkou, do úvodní věty) |
| `adresa` | ano | `{"ulice": "…", "psc": "615 00", "obec": "Brno"}`: provozovna, kam se jezdí |
| `sidlo` | ne | jen když se sídlo liší od provozovny |
| `telefon`, `email` | aspoň jedno | |
| `ico` | u skutečné firmy | kontroluje se součet |
| `rejstrik` | ne | celá věta, např. „Zapsaná v obchodním rejstříku vedeném Krajským soudem v Brně, oddíl C, vložka 12345.“ |
| `zalozeno` | ne | rok vzniku z ARES |
| `hodiny` | ano | všech 7 dní `po`–`ne`, např. `["7:00-12:00", "12:30-16:00"]`, zavřeno `[]` |
| `svatky` | ne | `"zavreno"` / `"otevreno"`; když to nevíme, vynechat (web pak o svátku napíše, že doba se může lišit) |
| `hodiny_pozn` | ne | krátká poznámka pod otevírací dobou |
| `sluzby` | ne | klíče z katalogu (níže) nebo `{"nazev": "…", "popis": "…", "ikona": "wrench"}` |
| `znacky` | ne | jen když je firma sama uvádí |
| `barva` | ne | `#rrggbb`; kontrast textu dopočítá generátor |
| `uvod` | ne | vlastní úvodní věta místo automatické |
| `zdroje`, `overeno` | u skutečné firmy | |
| `zverejneni` | pro zveřejnění | kdo a kdy schválil |
| `fiktivni` | ne | `true` jen u vymyšlené vzorové firmy |

Klíče služeb: `servis, opravy, brzdy, diagnostika, pneuservis, uskladneni, prodej_pneu, klimatizace, geometrie, stk, elektro, baterie, karoserie, lakovani, pojistne, autoskla, tazne, odtah, spojky, rozvody, vyfuky, uzitkova, lpg, olej, cisteni, ozon`.

### Co web umí
- Funguje bez externích souborů (žádná písma ani mapy z Googlu), takže projde bezpečnostní hlavičkou webu a nesbírá cookies.
- Podle času v Praze ukáže „Otevřeno do 16:30“ nebo „Zavřeno, otevíráme zítra v 7:00“ a zvýrazní dnešní den. Počítá se státními svátky včetně Velikonoc.
- Ikony: Lucide (licence ISC, text licence je v každé vyrobené stránce).
