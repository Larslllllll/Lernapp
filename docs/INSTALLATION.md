# LernApp installieren

Diese Anleitung ist für Windows 11. Du brauchst keine Administratorrechte und
keine Vorkenntnisse — es reicht, der Reihe nach durchzugehen.

macOS gibt es noch nicht. Wenn du einen Mac hast: melde dich bei Lars, dann
weiß er, dass sich der Aufwand lohnt.

---

## 1. Der schnelle Weg: ein Befehl

Das ist der empfohlene Weg. Er dauert etwa eine Minute und du bekommst **keine**
Sicherheitswarnung.

1. Drück die **Windows-Taste**, tipp `PowerShell` und drück **Enter**.
2. Kopier diese Zeile ins schwarze Fenster und drück **Enter**:

```powershell
iex (irm https://raw.githubusercontent.com/Larslllllll/Lernapp/main/install.ps1)
```

Einfügen geht mit Rechtsklick oder `Strg` + `V`.

Das Fenster meldet dann der Reihe nach, was es tut: Version nachschlagen,
Setup-Datei laden, Prüfsumme vergleichen, installieren. Am Ende startet LernApp
von selbst. Das Fenster kannst du danach schließen.

**Warum kommt hier keine Warnung?** Die blaue SmartScreen-Meldung (siehe unten)
hängt an einer Markierung, die dein *Browser* an heruntergeladene Dateien
klebt. PowerShell lädt die Datei direkt und setzt diese Markierung nicht. Die
Datei ist dieselbe — nur der Weg ist ein anderer.

Damit du trotzdem nicht blind irgendetwas ausführst, prüft das Skript vor dem
Installieren die **SHA-256-Prüfsumme** der Setup-Datei. Stimmt sie nicht, wird
die Datei gelöscht und nichts installiert.

**Später aktualisieren:** derselbe Befehl. Er erkennt, ob schon eine neuere
Version da ist, und macht nichts, wenn du bereits aktuell bist. Dein
Fortschritt bleibt dabei erhalten. Wichtig: LernApp vorher schließen.

---

## 2. Der Weg mit Doppelklick

Falls PowerShell bei dir gesperrt ist oder du lieber klickst.

Lade die Setup-Datei von der Seite
<https://github.com/Larslllllll/Lernapp/releases/latest> herunter — sie
heißt so:

```
LernApp-Setup-0.9.0.exe
```

Mach einen Doppelklick darauf. Dann kommt die Warnung aus Abschnitt 3.

Der Installer fragt nur wenig:

- **Zielordner** — einfach so lassen. LernApp landet in deinem eigenen
  Benutzerordner:
  `C:\Benutzer\DeinName\AppData\Local\Programs\LernApp`
  Deshalb braucht die Installation auch kein Administratorpasswort und ändert
  nichts am restlichen Rechner.
- **Verknüpfung auf dem Desktop** — Häkchen setzen, wenn du ein Symbol auf dem
  Desktop willst. Im Startmenü liegt LernApp so oder so.

Am Ende kannst du **LernApp jetzt starten** ankreuzen. Fertig.

---

## 3. Die blaue Warnung von Windows

**Wahrscheinlich erscheint jetzt ein blaues Fenster:**

> **Der Computer wurde durch Windows geschützt**
> Von Microsoft Defender SmartScreen wurde der Start einer unbekannten App
> verhindert. Die Ausführung dieser App stellt u. U. ein Risiko für den PC dar.

Das betrifft nur den Weg mit Doppelklick aus Abschnitt 2. Es sieht schlimmer
aus, als es ist. Bitte nicht abbrechen — so kommst du weiter:

1. Klick auf **Weitere Informationen** (der kleine Link im Text).
2. Es erscheint eine neue Schaltfläche: **Trotzdem ausführen**. Klick darauf.

Danach läuft die Installation normal weiter.

### Warum kommt diese Warnung?

Windows zeigt sie bei jedem Programm, das nicht von einer Firma mit einem
gekauften Zertifikat unterschrieben wurde. So ein Zertifikat kostet jedes Jahr
Geld, und LernApp ist ein Schulprojekt ohne Budget. Aus demselben Grund steht
im Installationsfenster **„Unbekannter Herausgeber"** statt eines Namens.

Die Warnung sagt also nur: *Windows kennt diesen Herausgeber nicht.* Sie sagt
nicht, dass etwas mit der Datei nicht stimmt.

Wenn du unsicher bist, ob die Datei wirklich von Lars kommt: frag ihn kurz
nach, bevor du sie startest. Das ist bei jeder heruntergeladenen Datei eine
gute Angewohnheit.

---

## 4. Der erste Start

Beim ersten Start ist schon ein Beispiel-Lernset da (französische Verben aus
Lars' Unterricht). Du kannst es benutzen, ignorieren oder löschen — es ist nur
dazu da, dass die App nicht leer aussieht.

So legst du dein eigenes an:

1. Links unten auf **+ Ordner**, um zum Beispiel „Englisch" anzulegen.
2. Auf das kleine **+** neben dem Ordnernamen, um darin ein Lernset anzulegen.
3. Im Fenster, das aufgeht, kannst du Vokabeln eintippen — oder eine ganze
   Liste auf einmal einfügen (siehe unten).

### Vokabeln als Liste einfügen

Wenn du deine Vokabeln schon irgendwo stehen hast (Word, Excel, Handy), kannst
du sie am Stück einfügen. Eine Zeile pro Vokabel, Semikolon dazwischen:

```
to go;gehen
the house;das Haus
```

Für unregelmäßige Verben schreibst du drei Formen in eine Zeile:

```
go;went;gone
be;was/were;been
```

Daraus macht LernApp automatisch ein Verbpaket und fragt alle drei Formen ab.

Statt Semikolon geht auch ein Tabulator (das kommt raus, wenn du aus Excel
kopierst). Ein Komma versteht LernApp auch, benutzt es aber nur, wenn sonst
nichts passt — Antworten enthalten oft selbst Kommas.

Bevor etwas gespeichert wird, zeigt dir LernApp eine Vorschau: wie viele
Vokabeln erkannt wurden und welche Zeilen es nicht verstanden hat.

---

## 5. Ein Lernset von jemand anderem übernehmen

Lernsets kann man als Datei weitergeben. Die heißt zum Beispiel
`englisch-unit-4.lernset.json` und lässt sich ganz normal per Chat, Mail oder
USB-Stick verschicken.

**Fertige Lernsets gibt es hier:** https://github.com/Larslllllll/Lernapp-lernsets
Dort liegen Sammlungen für Französisch, Englisch und Latein. Auf
**herunterladen** klicken, dann wie unten beschrieben importieren.

**Bekommen und einlesen:**

1. Datei irgendwohin speichern, wo du sie wiederfindest (Downloads reicht).
2. In LernApp links unten auf **Import**.
3. Die Datei auswählen. Das Lernset erscheint danach in der Liste.

**Selbst weitergeben:**

1. Rechtsklick auf das Lernset in der Liste.
2. **Exportieren …** wählen und einen Ort zum Speichern angeben.
3. Die entstandene Datei verschicken.

Wichtig: Eine solche Datei enthält **nur die Vokabeln**, nie deinen
Fortschritt. Wer dein Lernset bekommt, fängt bei null an — und du bekommst
umgekehrt auch keine fremden Punkte.

---

## 6. Wo deine eigenen Daten liegen

Alles, was du lernst, bleibt auf deinem Rechner. Nichts wird ins Internet
geschickt.

Deine Dateien liegen hier:

```
C:\Benutzer\DeinName\.lernapp
```

Darin:

| Datei | Inhalt |
|---|---|
| `data.json` | deine Lernsets und Vokabeln |
| `progress.json` | Fortschritt, XP, Level, Serien |
| `settings.json` | Einstellungen (Design, Ton, Fenstergröße) |
| `backups\` | automatische Sicherungskopien |
| `logs\` | Fehlerprotokoll (siehe unten) |

**Eine Deinstallation löscht diesen Ordner nicht.** Wenn du LernApp entfernst
und später neu installierst, ist dein Fortschritt wieder da. Wer wirklich alles
loswerden will, löscht den Ordner `.lernapp` von Hand.

Sichern kannst du deine Daten, indem du den Ordner `.lernapp` irgendwohin
kopierst.

---

## 7. Wenn etwas nicht funktioniert

### Die App stürzt ab oder zeigt eine Fehlermeldung

LernApp schreibt jeden Fehler in eine Protokolldatei:

```
C:\Benutzer\DeinName\.lernapp\logs\lernapp.log
```

Wenn ein Fehlerfenster erscheint, steht dieser Pfad auch darin. **Schick Lars
diese Datei** — damit kann er den Fehler nachvollziehen. Am besten schreibst du
dazu, was du gerade gemacht hast.

Die Datei wird **nicht** automatisch verschickt. Sie bleibt auf deinem Rechner,
bis du sie selbst weitergibst. Sie enthält nur technische Angaben, keine
Vokabeln und keine Antworten.

### Der Befehl aus Abschnitt 1 wird abgewiesen

Wenn PowerShell etwas von *Ausführungsrichtlinie* oder *ExecutionPolicy*
schreibt, ist auf deinem Rechner das Ausführen von Skripten gesperrt. Nimm dann
den Weg mit Doppelklick aus Abschnitt 2 — der funktioniert immer.

### Der Befehl bricht mit „Die Pruefsumme stimmt nicht" ab

Meistens ein abgebrochener Download. Führ den Befehl einfach noch einmal aus.
Wenn es wieder passiert, schreib Lars — dann stimmt etwas mit der Datei auf dem
Server nicht, und du solltest sie **nicht** von Hand installieren.

### Die App startet gar nicht

Auch dann lohnt der Blick in `logs\lernapp.log` — wenn die Datei existiert,
schick sie. Wenn es sie nicht gibt, schreib Lars einfach, dass beim Doppelklick
nichts passiert.

### Schnellwege in der App

| Taste | Wirkung |
|---|---|
| `Strg` + `N` | neues Lernset |
| `Strg` + `E` | aktuelles Lernset bearbeiten |
| `Strg` + `D` | zwischen hell und dunkel wechseln |
| `Strg` + `M` | Ton an/aus |
| `Strg` + `R` | Runde neu starten |

---

## 8. LernApp wieder entfernen

Windows-Einstellungen → **Apps** → **Installierte Apps** → LernApp →
**Deinstallieren**.

Der Ordner `.lernapp` mit deinen Vokabeln und deinem Fortschritt bleibt dabei
bestehen — absichtlich.
