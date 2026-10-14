# Nástroje (nejsou na webu)

Složka `_nastroje/` se na www.kudlimarketing.cz nezobrazuje: `netlify.toml` na ni vrací 404.
Repozitář je na GitHubu **veřejný**, proto sem nepatří hesla ani data skutečných firem.

| Nástroj | K čemu |
|---|---|
| `ukazky/generator.py` | Z JSON dat vyrobí ukázkový web autoservisu (šablona `ukazky/sablona-autoservis.html`). |
| `oznacit_demo.py` | Do hotového dema v samostatném repu doplní spodní lištu „Nezávazná ukázka webu…“ a zákaz indexování. |

## Ukázka pro autoservis

```bash
cd _nastroje/ukazky
cp data/_vzor-skutecna-firma.json data/novak.json   # vyplnit všechna DOPLNIT
python3 generator.py data/novak.json                 # náhled: nahled/novak/index.html
```

Náhled se otevře v prohlížeči přímo ze souboru. Na web se nedostane, dokud v datech není `"zverejneni"`.
`data/klic-a-kolo.json` je vymyšlená vzorová firma. Generátor nedovolí použít `"fiktivni"` pro jinou ukázku, takže její kopie pro skutečnou firmu skončí chybou.

### Pravidla pro data
- Fakta jen z ARES (obchodní firma, sídlo, IČO, zápis v rejstříku) a z toho, co firma sama zveřejňuje (vlastní web, firmy.cz): telefon, e-mail, otevírací doba, služby, značky, „od roku“.
- Žádné texty ani fotky z cizích webů, žádné recenze, ceny, sliby („do 24 hodin“, „nejlepší“). Popisy služeb bere generátor ze svého katalogu a jsou schválně obecné. Když firma uvádí víc, napiš vlastní `popis`.
- `"zdroje"` (odkazy, odkud fakta jsou) a `"overeno"` (datum kontroly) jsou u skutečné firmy povinné, stejně jako platné IČO (kontroluje se součet) a u s.r.o. `"sidlo"` z ARES.
- U OSVČ (`"pravni_forma": "osvc"`) se v ukázce adresa nezobrazuje (bývá to bydliště), jen jméno a IČO. Když firma místo podnikání sama zveřejňuje, nastav `"sidlo_zverejnit": true`. Ostrý web adresu mít musí (§ 435 občanského zákoníku).
- Data skutečné firmy neukládat do gitu (`.gitignore` je hlídá). Trvalá kopie patří do projektu GOD WEB, dokument `ukazky-data/<slug>.json`.

### Zveřejnění a smazání
0. **Před první skutečnou ukázkou přepnout repo `OKIUDLLA/Kudli.marketing` na soukromé.** Ve veřejném repu zůstane i smazaná ukázka dohledatelná v historii gitu, a stránka /ukazka-zdarma slibuje, že ji smažeme.
1. Firma o ukázku požádala (formulář na /ukazka-zdarma), nebo ji Ondra schválil. Do dat doplnit
   `"zverejneni": {"duvod": "zadost-firmy", "datum": "2026-10-15"}` (nebo `"duvod": "schvalil-ondra"`).
2. `python3 generator.py data/novak.json --qr` → `ukazky/novak/index.html` + QR kód v `nahled/` (QR jde vyrobit jen pro zveřejněnou ukázku).
3. Commit a push do `main` → za minutu běží na `https://www.kudlimarketing.cz/ukazky/novak/`.
   Ukázka má lištu „Nezávazná ukázka webu, nejde o oficiální stránky firmy“, titulek „Ukázka webu: …“ a zákaz indexování v HTML i v hlavičce (`netlify.toml`). Při tisku je upozornění nahoře na stránce.
4. Smazání: odstranit složku `ukazky/novak/` a pushnout.

### Ostrý web pro klienta
`python3 generator.py data/novak.json --ostry` → `ostre/novak/index.html` bez lišty a s povoleným indexováním. Potřebuje `"domena"`, `"rejstrik"` a `"sidlo"` (i u OSVČ). Nahrává se na doménu klienta.

### Pole v datech
| Pole | Povinné | Příklad / poznámka |
|---|---|---|
| `slug` | ano | `autoservis-novak` (adresa ukázky; malá písmena, číslice, pomlčky) |
| `nazev` | ano | `Autoservis Novák` (velký nadpis; bez s.r.o.) |
| `firma` | ano | `Autoservis Novák s.r.o.` (obchodní firma do patičky, přesně podle ARES) |
| `pravni_forma` | u skutečné firmy | `sro`, `as`, `osvc`, `jina` |
| `obor` | ne | `Autoservis` (výchozí); je v štítku nahoře a v titulku stránky |
| `lokalita` | ano | `Brno-Židenice` (1. pád) |
| `kde` | ano | `v Brně-Židenicích` (6. pád s předložkou, do úvodní věty) |
| `adresa` | ano | `{"ulice": "…", "psc": "615 00", "obec": "Brno"}`: provozovna, kam se jezdí |
| `sidlo` | u s.r.o. a a.s. | sídlo z ARES na jeden řádek, i když je stejné jako provozovna |
| `sidlo_zverejnit` | ne | `true` jen u OSVČ, která místo podnikání sama zveřejňuje |
| `telefon`, `email` | aspoň jedno | české číslo musí mít 9 číslic |
| `ico` | u skutečné firmy | kontroluje se součet |
| `rejstrik` | u ostrého webu | celá věta, např. „Zapsaná v obchodním rejstříku vedeném Krajským soudem v Brně, oddíl C, vložka 12345.“ |
| `od_roku` | ne | jen když to firma sama uvádí („od roku 1998“); rok vzniku z ARES nepoužívat |
| `hodiny` | ano | všech 7 dní `po`–`ne`, např. `["7:00-12:00", "12:30-16:00"]`, zavřeno `[]`, nonstop `["0:00-24:00"]` |
| `svatky` | ne | `"zavreno"` / `"otevreno"`; když to nevíme, vynechat (web pak o svátku napíše, že doba se může lišit) |
| `hodiny_pozn` | ne | krátká poznámka pod otevírací dobou |
| `sluzby` | ne | klíče z katalogu (níže) nebo `{"klic": "pneuservis", "popis": "vlastní popis"}`, případně úplně vlastní `{"nazev": "…", "popis": "…", "ikona": "wrench", "veta": "tvar do úvodní věty"}` |
| `znacky` | ne | jen když firma sama uvádí specializaci na značky |
| `barva` | ne | `#rrggbb`; odstíny s dostatečným kontrastem dopočítá generátor |
| `uvod` | ne | vlastní úvodní věta místo automatické („Servis, pneuservis a diagnostika v Brně-Židenicích.“) |
| `mapa_dotaz` | ne | když Google Mapy adresu provozovny nenajdou, např. název areálu |
| `kredit` | ne | `false` = bez řádku „Web: Kudli. marketing“ v patičce |
| `domena` | u ostrého webu | `www.autoservis-novak.cz` |
| `zdroje`, `overeno` | u skutečné firmy | seznam odkazů `https://…`, datum `RRRR-MM-DD` |
| `zverejneni` | pro zveřejnění | `{"duvod": "zadost-firmy" nebo "schvalil-ondra", "datum": "RRRR-MM-DD"}` |
| `poznamka` | ne | interní poznámka, na web se nedostane |
| `fiktivni` | ne | `true` jen u vzorové firmy `klic-a-kolo` |

Klíče služeb: `servis, opravy, brzdy, diagnostika, pneuservis, uskladneni, prodej_pneu, klimatizace, geometrie, stk, elektro, baterie, karoserie, lakovani, pojistne, autoskla, tazne, odtah, spojky, prevodovky, rozvody, vyfuky, uzitkova, lpg, olej, cisteni, ozon`.

### Co web umí
- Funguje bez externích souborů (žádná písma ani mapy z Googlu), takže projde bezpečnostní hlavičkou webu a nenačítá nic cizího.
- Podle času v Praze ukáže „Otevřeno do 16:30“ nebo „Zavřeno, otevíráme zítra v 7:00“, zvýrazní dnešní den a každou minutu se obnoví. Počítá se svátky podle zákona č. 245/2000 Sb. včetně Velikonoc.
- Barvy: z jedné barvy dopočítá odstíny tak, aby text měl kontrast aspoň 4,5 : 1 a tlačítka aspoň 3 : 1 (ověřeno na 5 832 barvách).
- Ikony: Lucide (licence ISC, text licence je v každé vyrobené stránce).
