# Generator — Kundenseiten-Bau (Python-CLI)

Baut aus einer Kunden-Config eine fertige Demo-Website. Teil des Blue-Ocean-Ökosystems
(siehe `../CLAUDE.md` → Schwester-Systeme).

## Status
- **Phase 0 (fertig):** Schnittstelle definiert (`../clients/_schema.json`), Verzeichnis-Gerüst.
- **Phase 1 (fertig):** Branchen-Templates als Astro-Komponenten mit Props + `astro:assets`.
- **Phase 2 (fertig):** `generate.py` — Config validieren + Bilder prüfen + Build.
- **Phase 3 (Code fertig, Bootstrap offen):** `deploy.py` + LeadBook-Caddyfile/Compose
  vorbereitet. Server-Bootstrap (einmalig) noch nicht ausgeführt — siehe Runbook unten.
- **Phase 4 (offen):** `leadbook_import.py` — Live-Anbindung an LeadBook.

## Nutzung (Phase 2)
```bash
pip install -r generator/requirements.txt   # einmalig (jsonschema)
python generator/generate.py <slug>          # z.B. beispielkunde
```
Der Generator: lädt `clients/<slug>.json` → prüft sie voll gegen `_schema.json`
→ prüft, dass alle referenzierten Bilder in `src/assets/clients/<slug>/` liegen
→ baut die Seite (`astro build`, Node 22) → `dist/kunde/<slug>/`.
Bei jedem Fehler bricht er mit **einer klaren Meldung** ab (kein Stacktrace).
`generate.py --deploy` ist als Flag da, tut aber nichts — Deploy läuft über `deploy.py`.

## Deploy & Bootstrap (Phase 3)

`deploy.py` synchronisiert `dist/` → `ubuntu@89.168.99.103:~/demo/` (eigenes Verzeichnis,
**getrennt** von `~/leadbook/`). Immer erst Dry-Run, dann Rückfrage:
```bash
python generator/deploy.py            # Dry-Run (zeigt nur)
python generator/deploy.py --apply    # echter Sync (fragt nochmal)
```

**Einmaliger Server-Bootstrap** (Caddy bedient `demo.` über DIESELBE Instanz wie
LeadBooks `leads.` — Reihenfolge ist sicherheitskritisch):

1. **Bcrypt-Hash erzeugen** (Klartext bleibt lokal):
   ```bash
   docker run --rm caddy:2-alpine caddy hash-password --plaintext 'DEIN_PASSWORT'
   ```
2. In `~/Documents/LeadBook/Caddyfile` `__BCRYPT_HASH__` durch den Hash ersetzen.
   ⚠️ **Niemals mit Platzhalter deployen** — ungültiger Hash = Caddy startet nicht =
   `leads.blue-ocean.marketing` (LeadBook) geht MIT offline.
3. Demo-Inhalt hochladen: `python generator/deploy.py --apply`
4. LeadBook deployen (bringt neue Caddyfile + Compose auf den Server — siehe
   LeadBook-Deploy-Befehl). Auf dem Server **vor** dem Caddy-Neustart prüfen:
   ```bash
   docker run --rm -v ~/leadbook/Caddyfile:/c:ro caddy:2-alpine caddy validate --config /c --adapter caddyfile
   ```
5. Caddy neu ziehen: `docker compose -f docker-compose.prod.yml up -d caddy`
   (holt automatisch das Let's-Encrypt-Zertifikat für `demo.`).
6. Prüfen: `demo.blue-ocean.marketing` → 401 ohne Login, Seite mit Login —
   **und** `leads.blue-ocean.marketing` weiterhin erreichbar.

## Die Schnittstelle (das Wichtigste)
Eine Datei pro Kunde: `../clients/<slug>.json`. **Einzige Wahrheit.**
Form ist verbindlich festgelegt in **`../clients/_schema.json`** (JSON-Schema, Draft 2020-12).
Validierungs-Lib: `jsonschema` (im System vorhanden, in Phase 2 in `requirements.txt` pinnen).

Geplanter Ablauf (Phase 2):

```
clients/<slug>.json
   │  generate.py: gegen _schema.json validieren
   ▼
src/assets/clients/<slug>/   ← Kundenbilder hierher kopieren
   │  astro build  (Template aus src/templates/<branche>/, Bilder via astro:assets → WebP/AVIF, responsive)
   ▼
dist/kunde/<slug>/   →  deploy.py (rsync) → demo.blue-ocean.marketing/kunde/<slug>/ (passwortgeschützt)
```

Geplanter Aufruf: `python generate.py <slug> [--deploy]`

## LeadBook-Naht (Phase 4 — jetzt nur dokumentiert, kein Code)
`leadbook_import.py` wird einen LeadBook-Lead über dessen API holen und **genau
`_schema.json` ausfüllen**. Dadurch ändert sich am Generator nichts — nur die Quelle
der JSON. `meta.quelle` wechselt dann von `"manuell"` auf `"leadbook"`.

Vorläufiges Feld-Mapping (LeadBook → Client-Config):

| Client-Config | LeadBook-Quelle (laut `../../LeadBook/CLAUDE.md`) |
|---|---|
| `marke.name` | Lead-Firmenname |
| `branche` | aus zugehöriger KeywordGroup ableiten (Mapping-Tabelle nötig) |
| `kontakt.adresse/telefon/email` | `contact_extractor` (Impressum + Hunter.io) |
| `meta.domain_ist` | Lead-Domain (bestehende schwache Website) |
| `meta.leadbook_lead_id` | Lead-ID |
| `meta.quelle` | fest `"leadbook"` |

> ⚠️ **Beim Bau von Phase 4 die exakten Spaltennamen aus `../../LeadBook/backend/models/`
> verifizieren — nicht raten.** LeadBook hat kein Git; die API/Modelle sind die einzige
> Vertragsgrundlage. Auth: JWT (LeadBook nutzt `lb_token`).

## Cyber-Sicherheit (gilt ab jetzt)
- Echte Kunden-Configs (`clients/*.json` ausser `_schema`/`beispielkunde`) und
  `src/assets/clients/*` sind in `../.gitignore` ausgeschlossen — **nie ins öffentliche Repo**.
- Zugangsdaten (Caddy-`basic_auth`, SSH-Key, LeadBook-Token) **nie** in Git/Code —
  kommen in Phase 2/3 aus einer lokalen, ignorierten `.env`.
- `demo.blue-ocean.marketing` läuft hinter `basic_auth` (bcrypt) + Security-Headern
  (übernommen aus Blue-Website), HTTPS via Caddy/Let's Encrypt.
