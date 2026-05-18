#!/usr/bin/env python3
"""Blue Ocean Demo-Generator (Phase 2).

Was es macht:
  1. clients/<slug>.json laden
  2. gegen clients/_schema.json prüfen (volle jsonschema-Validierung)
  3. prüfen, dass alle referenzierten Bilder wirklich da liegen
  4. Seite bauen (astro build → dist/kunde/<slug>/)

Deploy auf demo.blue-ocean.marketing kommt in Phase 3 (hier noch nicht).

Aufruf:  python generate.py <slug>
Beispiel: python generate.py beispielkunde
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# generator/ liegt direkt unter dem Projekt-Root
GENERATOR_DIR = Path(__file__).resolve().parent
ROOT = GENERATOR_DIR.parent
CLIENTS_DIR = ROOT / "clients"
SCHEMA_FILE = CLIENTS_DIR / "_schema.json"
ASSETS_DIR = ROOT / "src" / "assets" / "clients"
DIST_DIR = ROOT / "dist"


def fehler(msg: str) -> "None":
    """Sauber abbrechen mit klarer Meldung (kein Stacktrace)."""
    print(f"\n❌ {msg}\n", file=sys.stderr)
    sys.exit(1)


def schritt(msg: str) -> None:
    print(f"\n▶ {msg}")


def info(msg: str) -> None:
    print(f"   {msg}")


def lade_json(pfad: Path, was: str) -> dict:
    if not pfad.exists():
        fehler(f"{was} nicht gefunden: {pfad}")
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fehler(f"{was} ist kein gültiges JSON ({pfad.name}): Zeile {e.lineno}, {e.msg}")


def verfuegbare_kunden() -> list[str]:
    if not CLIENTS_DIR.exists():
        return []
    return sorted(
        p.stem for p in CLIENTS_DIR.glob("*.json") if p.name != "_schema.json"
    )


def validiere(config: dict, schema: dict) -> None:
    """Volle Schema-Prüfung. Sammelt ALLE Fehler, gibt sie lesbar aus."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        fehler(
            "Python-Paket 'jsonschema' fehlt. Installieren mit:\n"
            "   pip install -r generator/requirements.txt"
        )

    validator = Draft202012Validator(schema)
    probleme = sorted(validator.iter_errors(config), key=lambda e: list(e.absolute_path))
    if probleme:
        zeilen = []
        for e in probleme:
            stelle = "/".join(str(p) for p in e.absolute_path) or "(Wurzel)"
            zeilen.append(f"   • {stelle}: {e.message}")
        fehler(
            "Config passt nicht zum Schema (clients/_schema.json):\n"
            + "\n".join(zeilen)
        )


def sammle_bilder(config: dict) -> list[str]:
    """Alle in der Config referenzierten Bild-Dateinamen (ohne null)."""
    namen: list[str] = []
    logo = config.get("marke", {}).get("logo")
    if logo:
        namen.append(logo)
    hero = (config.get("hero") or {}).get("bild")
    if hero:
        namen.append(hero)
    for t in config.get("team") or []:
        if t.get("bild"):
            namen.append(t["bild"])
    for g in config.get("galerie") or []:
        if g.get("bild"):
            namen.append(g["bild"])
    return namen


def pruefe_bilder(config: dict, slug: str) -> None:
    namen = sammle_bilder(config)
    if not namen:
        info("keine Bilder referenziert — ok")
        return
    ordner = ASSETS_DIR / slug
    fehlend = [n for n in namen if not (ordner / n).is_file()]
    if fehlend:
        fehler(
            f"{len(fehlend)} referenzierte(s) Bild(er) fehlen in {ordner}/ :\n"
            + "\n".join(f"   • {n}" for n in fehlend)
            + f"\n\n   Bilder dort ablegen (werden beim Build automatisch optimiert)."
        )
    info(f"{len(namen)} Bild(er) gefunden — ok")


def baue(slug: str) -> None:
    """astro build über Node 22 (via nvm) anstoßen, Ausgabe live durchreichen."""
    befehl = (
        'export NVM_DIR="$HOME/.nvm"; '
        '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"; '
        "nvm use 22 >/dev/null 2>&1 || true; "
        "npm run build"
    )
    # eigene Schritt-Ausgaben zuerst rausschreiben, sonst mischt sich die
    # gepufferte Python-Ausgabe hinter die direkte Build-Ausgabe
    sys.stdout.flush()
    ergebnis = subprocess.run(["bash", "-lc", befehl], cwd=ROOT)
    if ergebnis.returncode != 0:
        fehler("Build fehlgeschlagen — siehe astro-Ausgabe oben.")

    ziel = DIST_DIR / "kunde" / slug / "index.html"
    if not ziel.is_file():
        fehler(
            f"Build lief durch, aber {ziel.relative_to(ROOT)} wurde nicht erzeugt.\n"
            "   Mögliche Ursache: Branche hat noch kein Template, oder der Slug "
            "wurde von der Validierung übersprungen — Build-Warnungen oben prüfen."
        )


def main() -> None:
    p = argparse.ArgumentParser(
        prog="generate.py",
        description="Baut aus clients/<slug>.json eine Demo-Kundenseite.",
    )
    p.add_argument("slug", help="Kunden-Slug = Dateiname ohne .json in clients/")
    p.add_argument(
        "--deploy",
        action="store_true",
        help="(Phase 3 — derzeit übersprungen, kein Effekt)",
    )
    args = p.parse_args()
    slug = args.slug.strip()

    schritt(f"Config laden: clients/{slug}.json")
    config_pfad = CLIENTS_DIR / f"{slug}.json"
    if not config_pfad.exists():
        kunden = verfuegbare_kunden()
        liste = "\n".join(f"   • {k}" for k in kunden) if kunden else "   (keine)"
        fehler(f"clients/{slug}.json gibt es nicht.\n\n   Verfügbare Kunden:\n{liste}")
    schema = lade_json(SCHEMA_FILE, "Schema")
    config = lade_json(config_pfad, "Config")
    info("geladen")

    schritt("Gegen Schema prüfen")
    validiere(config, schema)
    if config.get("slug") != slug:
        fehler(
            f"Slug-Konflikt: Datei heißt '{slug}.json', aber im Feld 'slug' steht "
            f"'{config.get('slug')}'. Beides muss gleich sein (sonst weicht die "
            f"gebaute URL /kunde/... vom Dateinamen ab)."
        )
    info("Config ist gültig")

    schritt("Bilder prüfen")
    pruefe_bilder(config, slug)

    schritt("Seite bauen (astro build, Node 22)")
    baue(slug)

    ausgabe = DIST_DIR / "kunde" / slug / "index.html"
    print(f"\n✅ Fertig. Seite gebaut:\n   {ausgabe}")
    print(f"   → wird in Phase 3 nach demo.blue-ocean.marketing/kunde/{slug}/ deployt.")
    if args.deploy:
        print(
            "\n⏭  --deploy ignoriert: Deploy kommt in Phase 3 "
            "(Caddy/rsync, Variante A)."
        )


if __name__ == "__main__":
    main()
