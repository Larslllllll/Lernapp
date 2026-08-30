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

## Fertige Lernsets

Wer nicht bei null anfangen will, findet unter
[Lernapp-lernsets](https://github.com/Larslllllll/Lernapp-lernsets) fertige Sammlungen zum Herunterladen und
Importieren — aktuell 24 Sets aus Französisch, Englisch und Latein.
Eigene beisteuern geht per Pull Request.

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

Das App-Icon wird aus `packaging/icon-quelle.png` erzeugt, nicht von Hand
gepflegt — `packaging/icon_bauen.py` schneidet den Rand ab und legt alle
Größen ab, die Windows abfragt (16 bis 256 px).

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

## Regeln, die man dem Code nicht ansieht

Wer hier etwas ändert, sollte diese fünf Punkte kennen. Jeder davon ist einmal
schiefgegangen.

**Der Identitätsschlüssel.** `progress.json` indiziert den Fortschritt
historisch nach der **Fragezeichenkette**, nicht nach einer ID. Deshalb gilt
`card.key` == das alte `q`-Feld, und `parse_card()` → `legacy_item()` muss
verlustfrei bleiben. Wer `key` ändert, entwertet jeden gespeicherten
Fortschritt.

**Triple-Karten.** Ein Verbpaket (`go / went / gone`) liegt als *drei* Karten
auf der Platte. Getrennt wird an `___`, **nicht** an Leerzeichen — sonst
zerbrechen mehrwortige Formen wie `been able`, `had to` oder `was/were`. Genau
daran ist die Vorgängerversion gescheitert. Die Paketidentität ist ein
geordnetes Tupel, kein `frozenset`, sonst kollabiert `must / had to / had to`
zu einem Eintrag.

**Zählung.** Ein Triple-Paket ist **eine** Lerneinheit. `lerneinheiten()` ist
die einzige Quelle dafür — Seitenleiste, Fortschrittsbalken und Statistik
müssen alle dieselbe Zahl benutzen.

**Asymmetrie bei der Bewertung.** Richtig erhöht die Serie nur der beantworteten
Karte; falsch setzt das ganze Paket zurück. Das ist Absicht. `round_errors`
steuert Wiederholung und wird pro Runde geleert, `total_errors` ist die
Historie und bleibt. Eine gespeicherte Combo darf beim Laden **keinen**
Multiplikator mehr geben — das war ein Exploit.

**Schichten.** `core` importiert nie ein GUI-Toolkit, und `winsound`/`AppKit`
stehen nur in `platform_services`. QML stellt ausschließlich dar: keine
Schwellen, keine Formeln, keine Kartenlogik. `if (combo >= 7) multiplier = 3`
gehört in den Core. Farben, Radien und Zeiten kommen alle aus dem Singleton
`qml/theme/Theme.qml`, nie als Hex-Wert in eine View.

Die Kartenauswahl nutzt einen injizierten `rng`, damit Tests reproduzierbar
sind — nie global `random`. Und `storage` schreibt atomar (Temp-Datei plus
`os.replace`) und legt einmal je Sitzung ein Backup an; beschädigte Dateien
werden beiseitegelegt statt überschrieben.

## Mitmachen

Fehler und Wünsche gerne als [Issue](https://github.com/Larslllllll/Lernapp/issues).
Pull Requests sind willkommen — bitte mit Test, und die Tests sollten vorher
grün sein. Kommentare, Bezeichner und Commit-Messages sind auf Deutsch.

## Lizenz

[MIT](LICENSE) — mach damit, was du willst.
