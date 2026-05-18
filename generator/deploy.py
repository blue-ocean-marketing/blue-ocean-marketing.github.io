#!/usr/bin/env python3
"""Blue Ocean Demo-Deploy (Phase 3).

Schiebt das gebaute dist/ auf den Oracle-VPS in ein EIGENES Verzeichnis
(~/demo/ = /home/ubuntu/demo) — getrennt von ~/leadbook/, damit ein
LeadBook-Deploy die Demo-Seiten nicht überschreibt (und umgekehrt).

Sicherheits-Prinzipien:
  • Erst IMMER ein rsync --dry-run + Zusammenfassung, dann Rückfrage.
  • Zielpfad ist hart auf ~/demo/ — niemals ~/leadbook/.
  • Fasst NICHT docker/compose/Caddy an. Der Caddy-Block + Volume-Mount
    ist ein einmaliger, separat freigegebener Bootstrap (siehe README).

Aufruf:
  python generator/deploy.py            # Dry-Run, zeigt was sich ändern würde
  python generator/deploy.py --apply    # echter Sync (fragt vorher nochmal)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

SSH_KEY = "/home/systemdown/Desktop/leadbook/ssh-key-2026-05-05(1).key"
SERVER = "ubuntu@89.168.99.103"
REMOTE = "~/demo/"  # = /home/ubuntu/demo — NIEMALS ~/leadbook/


def fehler(msg: str) -> None:
    print(f"\n❌ {msg}\n", file=sys.stderr)
    sys.exit(1)


def vorab_checks() -> None:
    if not Path(SSH_KEY).is_file():
        fehler(f"SSH-Key nicht gefunden: {SSH_KEY}")
    if not DIST.is_dir() or not (DIST / "index.html").is_file():
        fehler(
            "dist/ fehlt oder ist leer. Erst bauen:\n"
            "   python generator/generate.py <slug>"
        )
    if "leadbook" in REMOTE:
        fehler("Sicherheits-Stop: REMOTE zeigt auf leadbook — abgebrochen.")


def rsync(dry: bool) -> int:
    ssh = f'ssh -i "{SSH_KEY}" -o StrictHostKeyChecking=accept-new'
    cmd = [
        "rsync",
        "-az",
        "--delete",
        "--exclude",
        ".DS_Store",
        "-e",
        ssh,
        f"{DIST}/",
        f"{SERVER}:{REMOTE}",
    ]
    if dry:
        cmd.insert(1, "--dry-run")
        cmd.insert(2, "-i")  # itemize: zeigt jede Änderung/Löschung
    print("   " + " ".join(cmd))
    return subprocess.run(cmd).returncode


def main() -> None:
    p = argparse.ArgumentParser(prog="deploy.py", description="dist/ → demo.blue-ocean.marketing (VPS)")
    p.add_argument("--apply", action="store_true", help="echten Sync ausführen (sonst nur Dry-Run)")
    p.add_argument("--yes", action="store_true", help="Rückfrage überspringen (für Automatisierung)")
    args = p.parse_args()

    vorab_checks()

    print(f"\n▶ Dry-Run: {DIST} → {SERVER}:{REMOTE}")
    if rsync(dry=True) != 0:
        fehler("Dry-Run fehlgeschlagen (SSH/rsync). Nichts geändert.")

    if not args.apply:
        print(
            "\nℹ  Nur Dry-Run. Für echten Sync:  python generator/deploy.py --apply"
            "\n   (Caddy-Block/Volume = einmaliger Bootstrap, siehe generator/README.md)"
        )
        return

    if not args.yes:
        antwort = input("\n⚠  Obige Änderungen wirklich auf den Server schreiben? [tippe 'ja']: ")
        if antwort.strip().lower() != "ja":
            print("Abgebrochen — nichts geändert.")
            return

    print(f"\n▶ Echter Sync → {SERVER}:{REMOTE}")
    if rsync(dry=False) != 0:
        fehler("Sync fehlgeschlagen.")
    print(
        "\n✅ Demo-Dateien synchronisiert."
        "\n   Erreichbar (nach erfolgtem Bootstrap) unter:"
        "\n   https://demo.blue-ocean.marketing/  (Login nötig)"
    )


if __name__ == "__main__":
    main()
