# LernApp

Ein Vokabeltrainer als native Windows-Desktop-App. Kein Konto, kein Server,
keine Werbung — alles, was du lernst, bleibt auf deinem Rechner.

Entstanden als Schulprojekt, weil die üblichen Vokabel-Apps entweder Geld
kosten, Daten sammeln oder unregelmäßige Verben nicht richtig abfragen können.

## Installieren

Windows-Taste drücken, `PowerShell` tippen, Enter, und diese Zeile einfügen:

```powershell
iex (irm https://raw.githubusercontent.com/Larslllllll/Lernapp/main/install.ps1)
```

Das lädt die aktuelle Version, prüft ihre SHA-256-Summe und installiert sie
ohne Adminrechte in deinen Benutzerordner. Derselbe Befehl aktualisiert später.

Wer lieber klickt, nimmt die Setup-Datei aus
[Releases](https://github.com/Larslllllll/Lernapp/releases/latest) — dann meldet
sich allerdings Windows SmartScreen, weil die Datei nicht signiert ist.
Ausführlich erklärt in [docs/INSTALLATION.md](docs/INSTALLATION.md).

macOS ist geplant, existiert aber noch nicht.

## Was die App kann

- **Unregelmäßige Verben richtig.** `go / went / gone` ist ein Paket aus drei
  Karten, das als *eine* Lerneinheit zählt. Eine richtige Antwort zählt nur für
  die beantwortete Form, ein Fehler setzt das ganze Paket zurück.
- **Vokabeln als Liste einfügen** — aus Word, Excel oder vom Handy, mit
  Semikolon, Tabulator oder Komma getrennt. Vor dem Speichern gibt es eine
  Vorschau mit den Zeilen, die nicht verstanden wurden.
- **Lernsets weitergeben** als `.lernset.json`. Die Datei enthält nur die
  Vokabeln, nie den Fortschritt — wer dein Set bekommt, fängt bei null an.
- **XP, Level, Serien und Combos**, weil es sonst niemand zweimal öffnet.
- **Hell und dunkel**, Tastenkürzel für alles Wichtige, Ton abschaltbar.

## Deine Daten

Alles liegt unter `%USERPROFILE%\.lernapp` — Lernsets, Fortschritt,
Einstellungen und automatische Sicherungskopien. Nichts wird ins Internet
geschickt; die App spricht ausschließlich beim Update-Check mit dem Netz.
Eine Deinstallation lässt diesen Ordner absichtlich stehen.

## Selbst bauen

Python 3.11 oder neuer, Windows.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt -r requirements-dev.txt

.venv/Scripts/python.exe LernApp.py                              # starten
.venv/Scripts/python.exe -m pytest tests/ -q                     # Tests
.venv/Scripts/python.exe packaging/build_windows.py --installer  # Bundle + Setup
```

`requirements.txt` verlangt bewusst `PySide6-Essentials` statt `PySide6` — das
Metapaket zöge 194 MB Qt WebEngine mit, die niemand braucht. Das Build-Skript
bricht ab, wenn doch `PySide6-Addons` installiert ist.

Für den Installer wird zusätzlich [Inno Setup](https://jrsoftware.org/isinfo.php)
gebraucht (`winget install JRSoftware.InnoSetup`).

## Aufbau

```
lernapp/core/               Lernregeln. Kennt weder Qt noch Dateien.
lernapp/storage/            JSON-Persistenz, Migrationen, Pfade.
lernapp/platform_services/  OS-Grenze (Ton, Meldungen).
lernapp/gui/                PySide6: bridge/ (ViewModels) + qml/ (Darstellung).
packaging/                  PyInstaller-Spec, Inno-Skript, install.ps1, Release.
```

Die harte Regel: **`core` importiert nie ein GUI-Toolkit.** Deshalb hat der
Wechsel von CustomTkinter zu PySide6 nur die GUI-Schicht gekostet.

Wer tiefer einsteigt: [notizen.md](notizen.md) ist der Fahrplan mit den
Invarianten, die man nicht aus dem Code ablesen kann — warum Triple-Karten an
`___` und nicht an Leerzeichen getrennt werden, warum der Identitätsschlüssel
einer Karte die Fragezeichenkette bleiben muss, und was eine gespeicherte Combo
beim Laden **nicht** mehr darf.

## Mitmachen

Fehler und Wünsche gerne als [Issue](https://github.com/Larslllllll/Lernapp/issues).
Pull Requests sind willkommen — bitte mit Test, und die Tests sollten vorher
grün sein. Kommentare, Bezeichner und Commit-Messages sind auf Deutsch.

## Lizenz

[MIT](LICENSE) — mach damit, was du willst.
