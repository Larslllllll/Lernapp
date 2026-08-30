# LernApp — Vokabelerkennung

Ein kleiner Dienst auf Cloudflare Workers. Er nimmt den Text einer Buchseite
entgegen und gibt die erkannten Vokabelpaare zurück.

## Wozu

Der Schlüssel zum Sprachmodell darf nicht in der App stecken: sie ist
quelloffen und wird als `.exe` verteilt — ein Schlüssel darin wäre in Minuten
ausgelesen. Also kennt die App nur diese Adresse, und der Schlüssel liegt
ausschliesslich hier.

Der Dienst ist **kein allgemeiner Modell-Proxy**. Er kann genau eine Sache:
aus einem Text Vokabelpaare herausziehen. Die Anweisung an das Modell steht
im Worker, nicht in der App. Wer die Adresse findet, kann damit also keine
Aufsätze schreiben lassen.

## Grenzen, ehrlich benannt

Die Adresse steht im offenen Quelltext der App. Geheimhaltung ist kein
Schutz. Was schützt:

| | |
|---|---|
| 20 Seiten pro Gerät und Tag | ein Einzelner verdirbt nicht allen den Tag |
| 1500 Anfragen pro Tag insgesamt | das Kontingent läuft nie ganz leer |
| höchstens 40 000 Zeichen | eine Buchseite hat keine 40 000 |
| nur ein einziger Endpunkt | kein freier Zugang zum Modell |

Wird es doch missbraucht: Schlüssel wechseln, Deckel senken, oder den Worker
kurz abschalten. Die App fällt dann auf „Vokabeln von Hand einfügen" zurück
und funktioniert weiter.

## Einrichten

```bash
npm install -g wrangler
wrangler login

# Zähler-Speicher anlegen und die ausgegebene id in wrangler.toml eintragen
wrangler kv namespace create ZAEHLER

# Schlüssel hinterlegen (wird nie in eine Datei geschrieben)
wrangler secret put NOUS_API_KEY

wrangler deploy
```

Danach steht die Adresse in der Ausgabe, etwa
`https://lernapp-vokabeln.<konto>.workers.dev`. Diese Adresse gehört in
`lernapp/netz/vokabel_dienst.py` als `DIENST_URL`.

## Prüfen, ob er läuft

```bash
curl -s -X POST https://lernapp-vokabeln.<konto>.workers.dev/vokabeln \
  -H "content-type: application/json" \
  -d '{"geraet":"testgeraet-1234","text":"la maison   das Haus\nle chien   der Hund"}'
```
