# Sorgenti del sito hotelmaffeipinzolo.it

Il sito e' statico (GitHub Pages) ed e' generato da qui. Non si modificano a mano le pagine
nella radice del repo: si cambiano i sorgenti e si rigenera.

| File | Cosa contiene |
|---|---|
| `config.json` | dati fissi: dominio, indirizzi delle pagine nelle 3 lingue, contatti, societa' (REA!), camere, recensioni, link esterni, quali foto vanno in quale pagina, stagioni aperte per le date proposte alla prenotazione |
| `testi.json` | tutti i testi in italiano, inglese e polacco (pagine e interfaccia) |
| `foto.json` | le foto usate: numero, nome del file master, testi alternativi nelle 3 lingue |
| `dati.md` | i dati certi da cui sono stati scritti i testi |
| `logo-maffei.png` | il logo ufficiale (stemma, sfondo trasparente) |
| `genera.py` | genera pagine, foto per il web, logo e icone, sitemap, robots, 404, reindirizzi |
| `controlla.py` | controlli automatici dopo la generazione |
| `anteprima.py` | copia del sito con collegamenti relativi, per un'anteprima privata fuori dal dominio |

## Rigenerare
```
python3 _sorgenti/genera.py
python3 _sorgenti/controlla.py
```
Serve Python 3 con Pillow. Le foto master (2400 px, senza metadati) stanno nella cartella indicata
in `config.json` -> `cartella_master` (cartella del progetto sul Mac di Luca); le versioni web
in `img/foto/` si rifanno da sole solo se il master cambia.

## Cose da cambiare spesso
- **Stagioni aperte** (`config.json` -> `prenotazione.stagioni`): servono a proporre il primo sabato-sabato libero quando si clicca "Verifica prezzi". Aggiornarle a ogni stagione.
- **Foto di apertura della Home** (`foto_pagine.home_hero`): d'inverno 399 (sera con la neve), d'estate 132 (sera d'estate).
- **Recensioni** (`recensioni`): voto e numero, con il mese (testo `reviews_date` in `testi.json`).
- **REA** (`societa.rea`): TN-235607 (dato da Luca il 1/11/2026).

## Anteprima privata
```
python3 _sorgenti/anteprima.py CARTELLA_FUORI_DAL_REPO --leggera
```
Fa una copia con la striscia "ANTEPRIMA", robots noindex e collegamenti relativi: si apre da
qualunque cartella o pagina privata. `--leggera` tiene solo le foto da 800 e 1600 px.
