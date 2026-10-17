# Dopisy s QR kódem na ukázku zdarma

Data firem (`firmy.json`) se do gitu neukládají, repo je veřejné. Seznam první vlny je v projektu GOD WEB, dokument `claude/dopis-autoservisy.md`.

```bash
cd _nastroje/dopisy
npm install --prefix fonty @fontsource/inter@5.2.8   # písmo Inter (TrueType), ať PDF nemá fonty Type 3
node shots.js        # obrázky vzorové ukázky Klíč a kolo
python3 sestav.py    # html/dopis-KÓD.html + vypíše odkazy z QR kódů
node pdf.js          # pdf/dopis-KÓD.pdf (A4, adresy podle vzoru PostServis pro obálku C5/6)
```

`firmy.json`: seznam `{kod, crm, firma, kratce, adresa: [ulice, "PSČ obec"], web, obor, veta}`. Datum je v `sestav.py` (DATUM).
Odesílá se přes Českou poštu, Dopis Online (online.postservis.cz): nahrát PDF, obyčejné psaní, obálka C5/6.
