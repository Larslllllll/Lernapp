/**
 * LernApp-Vermittler: Vokabeln aus einem Text erkennen.
 *
 * Warum es diesen Server gibt: Der Schlüssel zum Sprachmodell darf nicht in
 * der App stecken. Sie ist quelloffen und wird als .exe verteilt - ein
 * Schlüssel darin wäre in Minuten ausgelesen. Also kennt die App nur diese
 * Adresse, und der Schlüssel liegt ausschliesslich hier als Cloudflare-Secret.
 *
 * Der Server ist bewusst KEIN allgemeiner Modell-Proxy. Er kann genau eine
 * Sache: aus einem Text Vokabelpaare herausziehen. Die Anweisung an das
 * Modell steht hier und nicht in der App. Wer die Adresse findet, kann damit
 * also keine Aufsätze schreiben lassen - nur Vokabellisten erkennen.
 *
 * Missbrauchsschutz, ehrlich benannt: Die Adresse steht im offenen
 * Quelltext. Geheimhaltung ist kein Schutz. Was schützt, sind die Deckel -
 * pro Gerät und pro Tag insgesamt - und die Möglichkeit, den Schlüssel
 * jederzeit zu wechseln.
 */

const MODELL = "inclusionai/ling-3.0-flash-fin:free";
const ANBIETER = "https://inference-api.nousresearch.com/v1/chat/completions";

// Deckel. Grosszügig genug für den Unterricht, eng genug, dass ein
// Einzelner nicht allen anderen den Tag verdirbt.
const PRO_GERAET_TAG = 20;
const INSGESAMT_TAG = 1500;

// Eine Buchseite hat keine 40 000 Zeichen. Alles darüber ist ein Versehen
// oder ein Versuch, das Kontingent zu verbrennen.
const MAX_ZEICHEN = 40000;

const SYSTEM =
  "Du hilfst beim Vokabellernen in der Schule. Du bekommst den rohen Text " +
  "einer Buch- oder Arbeitsblattseite und ziehst daraus die Vokabelpaare. " +
  "Du erfindest nichts dazu: was nicht im Text steht, kommt nicht vor.";

const AUFTRAG = (text) => `Ziehe aus dem folgenden Text alle Vokabelpaare heraus.

Regeln:
- Eine Zeile je Vokabel, im Format  fremdsprache;deutsch
- Bei unregelmässigen Verben mit drei Formen:  form1;form2;form3
- Überschriften, Seitenzahlen, Aufgabenstellungen, Grammatikerklärungen und
  Beispielsätze weglassen
- Artikel mitnehmen, wenn sie im Text stehen (la maison;das Haus)
- Nichts erfinden, nichts übersetzen, was nicht schon dasteht
- Keine Nummerierung, keine Aufzählungszeichen, keine Anführungszeichen
- Wenn du keine Vokabelpaare findest, gib genau NICHTS aus

Text:
---
${text}
---`;

const heute = () => new Date().toISOString().slice(0, 10);

function antwort(daten, status = 200) {
  return new Response(JSON.stringify(daten), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

/** Zähler hochsetzen und den neuen Stand zurückgeben. */
async function zaehle(kv, schluessel) {
  const stand = parseInt((await kv.get(schluessel)) || "0", 10) + 1;
  // Zwei Tage aufheben reicht - danach ist der Tag ohnehin vorbei.
  await kv.put(schluessel, String(stand), { expirationTtl: 60 * 60 * 48 });
  return stand;
}

export default {
  async fetch(anfrage, umgebung) {
    const adresse = new URL(anfrage.url);

    // Wer die Adresse im Quelltext findet und sie im Browser öffnet, soll
    // etwas Verständliches sehen statt eines Fehlers.
    if (anfrage.method === "GET" && adresse.pathname === "/") {
      return new Response(
        "LernApp - Vokabelerkennung.\n\n" +
          "Dieser Dienst gehoert zu https://github.com/Larslllllll/Lernapp\n" +
          "Er erkennt Vokabeln in einem eingesendeten Text. Mehr nicht.\n",
        { headers: { "content-type": "text/plain; charset=utf-8" } },
      );
    }

    if (adresse.pathname !== "/vokabeln" || anfrage.method !== "POST") {
      return antwort({ fehler: "Unbekannter Aufruf." }, 404);
    }

    let koerper;
    try {
      koerper = await anfrage.json();
    } catch {
      return antwort({ fehler: "Ungueltige Anfrage." }, 400);
    }

    const text = String(koerper.text || "").trim();
    const geraet = String(koerper.geraet || "").replace(/[^a-zA-Z0-9-]/g, "").slice(0, 64);

    if (!text) return antwort({ fehler: "Kein Text mitgeschickt." }, 400);
    if (text.length > MAX_ZEICHEN)
      return antwort({ fehler: "Der Text ist zu lang." }, 413);
    if (geraet.length < 8)
      return antwort({ fehler: "Keine Geraetekennung mitgeschickt." }, 400);

    const tag = heute();
    const kv = umgebung.ZAEHLER;

    const gesamt = parseInt((await kv.get(`alle:${tag}`)) || "0", 10);
    if (gesamt >= INSGESAMT_TAG) {
      return antwort(
        {
          fehler:
            "Heute wurde das Tageskontingent aufgebraucht. Morgen geht es " +
            "wieder - Vokabeln von Hand einfuegen geht jederzeit.",
        },
        429,
      );
    }

    const proGeraet = parseInt((await kv.get(`geraet:${geraet}:${tag}`)) || "0", 10);
    if (proGeraet >= PRO_GERAET_TAG) {
      return antwort(
        {
          fehler:
            `Du hast heute schon ${PRO_GERAET_TAG} Seiten eingelesen. ` +
            "Morgen gibt es wieder neue - Vokabeln von Hand einfuegen geht jederzeit.",
        },
        429,
      );
    }

    // Erst zählen, dann fragen. Andersherum liesse sich der Deckel durch
    // viele gleichzeitige Anfragen umgehen.
    await zaehle(kv, `geraet:${geraet}:${tag}`);
    await zaehle(kv, `alle:${tag}`);

    let modellAntwort;
    try {
      const ergebnis = await fetch(ANBIETER, {
        method: "POST",
        headers: {
          authorization: `Bearer ${umgebung.NOUS_API_KEY}`,
          "content-type": "application/json",
        },
        body: JSON.stringify({
          model: MODELL,
          temperature: 0.1,
          messages: [
            { role: "system", content: SYSTEM },
            { role: "user", content: AUFTRAG(text) },
          ],
        }),
      });
      if (!ergebnis.ok) {
        return antwort(
          { fehler: "Der Dienst antwortet gerade nicht. Bitte spaeter erneut." },
          502,
        );
      }
      const roh = await ergebnis.json();
      modellAntwort = roh?.choices?.[0]?.message?.content ?? "";
    } catch {
      return antwort({ fehler: "Der Dienst ist nicht erreichbar." }, 502);
    }

    return antwort({
      text: String(modellAntwort).trim(),
      verbleibend: Math.max(0, PRO_GERAET_TAG - proGeraet - 1),
    });
  },
};
