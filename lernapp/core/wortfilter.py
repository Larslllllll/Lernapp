"""Sperrliste für Lernsets, die veröffentlicht werden sollen.

Eine blosse Wortliste fängt nichts: `nigg3r`, `n i g g e r`, `N-I-G-G-E-R`,
`niiigger` und `nigger` mit kyrillischem `е` laufen alle daran vorbei. Deshalb
wird zuerst normalisiert und dann gegen ein Muster verglichen - die Liste
enthält nur Grundformen, die Schreibvarianten erledigt der Filter.

**Warum Muster und nicht "Doppelbuchstaben zusammenziehen":** Der naheliegende
Weg, `niiigger` zu fangen, ist es, Wiederholungen auf einen Buchstaben zu
kürzen. Dann wird aus `nigger` aber `niger` - und das steckt in `weniger` und
`einiger`. Ein deutscher Vokabeltrainer, der "weniger" sperrt, ist kaputt.
Stattdessen wird jede Grundform zu einem Muster wie `n+i+g+g+e+r+`: beliebig
oft wiederholte Buchstaben passen, aber die zwei `g` bleiben Pflicht.

Der Filter gilt für das **Veröffentlichen**, nicht für die eigenen Lernsets
auf der Platte. Was jemand privat lernt, geht das Programm nichts an; was er in
den gemeinsamen Marktplatz stellt, schon.

Kein Filter fängt alles, und jeder Filter fängt gelegentlich das Falsche.
Er ist die erste Hürde, nicht die einzige - der Marktplatz bleibt kuratiert.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

# Zeichen, mit denen Buchstaben ersetzt werden, um Filter zu umgehen.
# Zahlen und Satzzeichen (leetspeak) sowie Buchstaben aus fremden Alphabeten,
# die lateinischen zum Verwechseln ähnlich sehen (Homoglyphen). Letztere sind
# der unauffälligste Trick überhaupt: `niggеr` mit kyrillischem "е" sieht
# identisch aus und kommt durch jede naive Liste.
ERSETZUNGEN = {
    # leetspeak
    "0": "o", "1": "i", "!": "i", "|": "i", "3": "e", "4": "a", "@": "a",
    "5": "s", "$": "s", "7": "t", "+": "t", "8": "b", "9": "g", "6": "g",
    "2": "z", "€": "e", "£": "l", "*": "", "#": "", "^": "",
    # kyrillisch
    "а": "a", "в": "b", "с": "c", "е": "e", "н": "h", "к": "k", "м": "m",
    "о": "o", "р": "p", "т": "t", "у": "y", "х": "x", "і": "i", "ѕ": "s",
    "ԁ": "d", "ј": "j", "ԛ": "q", "ԝ": "w", "г": "r", "п": "n",
    # griechisch
    "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "ο": "o", "ρ": "p",
    "τ": "t", "υ": "y", "χ": "x", "ν": "v", "μ": "m",
}

# Grundformen, klein geschrieben. Schreibvarianten müssen hier NICHT stehen -
# Zahlen, Sonderzeichen, fremde Alphabete, Trennzeichen und in die Länge
# gezogene Buchstaben werden vor dem Vergleich zurückgeführt.
#
# Was hier dennoch dazugehört, sind **lautliche** Varianten: `niqqa` oder
# `nikka` sind keine Zeichenersetzung, sondern andere Buchstaben. Die kann
# kein Muster erraten.
#
# Bewusst nur schwere Beleidigungen, keine allgemeinen Schimpfwörter: ein
# Vokabelheft darf `damn` enthalten. Erweitern ist Absicht - eine Zeile
# dazuschreiben genügt.
GESPERRT = frozenset({
    # rassistisch
    "nigger", "nigga", "niqqa", "nikka", "nikker", "nigor", "nigra",
    "negro", "negroes", "negros", "neger", "negerin",
    "coon", "coons", "chink", "chinks", "gook", "gooks",
    "spic", "spics", "wetback", "wetbacks",
    "kanake", "kanaken", "zigeuner", "bimbo", "bimbos",
    # antisemitisch
    "kike", "kikes", "judensau", "judenschwein", "yid", "yids",
    # queerfeindlich
    "faggot", "faggots", "fagot", "tranny", "trannies", "schwuchtel",
    "schwuchteln", "kampflesbe",
    # behindertenfeindlich
    "spastiker", "spasti", "mongoloid", "krueppel",
    # nationalsozialistisch
    "sieghail", "heilhitler", "hakenkreuz", "judenvergasen", "gaskammer",
    "untermensch", "untermenschen",
})

# Wörter, die eine Grundform enthalten, aber harmlos sind. Ohne diese Liste
# stolpert der Filter über die eigenen Füsse - das ist der klassische
# Fehler, an dem Wortfilter scheitern.
AUSNAHMEN = frozenset({
    "snigger", "sniggers", "sniggering", "sniggered",
    "denigrate", "denigrates", "denigrating", "denigration",
    "raccoon", "raccoons", "cocoon", "cocoons", "tycoon", "tycoons",
    "coonhound", "cooney",
    "spice", "spices", "spicy", "spicier", "spiciest",
    "spick", "spicken", "spickzettel",
    "negroni",
})

# Der zweite Durchgang sucht über Wortgrenzen hinweg (gegen `n i g g e r`),
# aber NUR über Folgen sehr kurzer Bruchstücke. Ganze Wörter einfach
# aneinanderzuhängen war der erste Versuch und hat „eine grosse Wohnung"
# gesperrt: zusammengezogen steht darin `einegrossewohnung`, und das enthält
# `negros`. Wer Buchstaben auseinanderzieht, hinterlässt dagegen eine Folge
# von Bruchstücken mit ein bis zwei Zeichen - genau daran wird er erkannt.
MAXLAENGE_BRUCHSTUECK = 2
MINDESTANZAHL_BRUCHSTUECKE = 3

# Ab dieser Länge darf eine Grundform mitten im Wort gefunden werden, damit
# Beugungen wie `niggers` hängen bleiben. Kürzere müssen das ganze Wort
# ausfüllen, sonst sperrt `spic` das Wort `suspicion`.
MINDESTLAENGE_TEILWORT = 6

# Was als Wortgrenze gilt. Buchstaben aus fremden Alphabeten und die
# leetspeak-Zeichen gehören ausdrücklich NICHT dazu - sie sind Teil des
# Wortes, das jemand zu verstecken versucht.
TRENNER = r"[^0-9A-Za-zÀ-ÿА-Яа-яΑ-Ωα-ω@$!|+*#^€£]+"


@dataclass(frozen=True)
class Treffer:
    """Ein Fund, so beschrieben, dass man ihn dem Nutzer zeigen kann."""

    wort: str
    fundstelle: str


def normalisiere(text: str) -> str:
    """Text auf reine Kleinbuchstaben zurückführen.

    Akzente weg (`é` -> `e`), leetspeak und Homoglyphen zurückübersetzt,
    alles Übrige entfernt.
    """
    ersetzt = "".join(ERSETZUNGEN.get(z, z) for z in text.casefold())
    zerlegt = unicodedata.normalize("NFKD", ersetzt)
    ohne_akzente = "".join(z for z in zerlegt if not unicodedata.combining(z))
    # Zweiter Durchgang: NFKD kann aus einem Sonderzeichen erst ein Zeichen
    # machen, das in der Ersetzungstabelle steht (z. B. Ziffern in Kreisen).
    ersetzt = "".join(ERSETZUNGEN.get(z, z) for z in ohne_akzente)
    return re.sub(r"[^a-z]", "", ersetzt)


@lru_cache(maxsize=1)
def _muster() -> tuple[tuple[str, re.Pattern], ...]:
    """Je Grundform ein Muster, das gedehnte Buchstaben verträgt.

    `nigger` wird zu `n+i+g+g+e+r+`. Damit passt `niiigger`, aber `weniger`
    passt nicht: die zwei aufeinanderfolgenden `g` bleiben Pflicht.
    """
    gebaut = []
    for wort in sorted(GESPERRT):
        muster = "".join(f"{re.escape(z)}+" for z in normalisiere(wort))
        gebaut.append((wort, re.compile(muster)))
    return tuple(gebaut)


def _auseinandergezogen(text: str) -> list[str]:
    """Folgen sehr kurzer Bruchstücke wieder zusammensetzen.

    `n i g g e r` und `n-i-g-g-e-r` werden zu `nigger`. Ein normaler Satz
    liefert nichts, weil seine Wörter zu lang sind - und genau darum sperrt
    dieser Durchgang „eine grosse Wohnung" nicht mehr.

    Ausnahmen bleiben draussen: sonst baut `snigger` als Ganzes eine Kette,
    in der `nigger` steckt.
    """
    ketten: list[str] = []
    laufend: list[str] = []
    for roh in re.split(TRENNER, text):
        sauber = normalisiere(roh)
        if sauber and sauber not in AUSNAHMEN and len(sauber) <= MAXLAENGE_BRUCHSTUECK:
            laufend.append(sauber)
            continue
        if len(laufend) >= MINDESTANZAHL_BRUCHSTUECKE:
            ketten.append("".join(laufend))
        laufend = []
    if len(laufend) >= MINDESTANZAHL_BRUCHSTUECKE:
        ketten.append("".join(laufend))
    return ketten


def pruefe(text: str, fundstelle: str = "") -> list[Treffer]:
    """Alle Verstösse in einem Text. Leere Liste heisst: in Ordnung."""
    if not text:
        return []

    gefunden: dict[str, Treffer] = {}

    # 1. Wortweise. Ein Wort aus den Ausnahmen ist erledigt, sonst schlägt
    #    `denigrate` wegen seiner Mitte an.
    for roh in re.split(TRENNER, text):
        sauber = normalisiere(roh)
        if not sauber or sauber in AUSNAHMEN:
            continue
        for wort, muster in _muster():
            if wort in gefunden:
                continue
            treffer = (muster.search(sauber) if len(wort) >= MINDESTLAENGE_TEILWORT
                       else muster.fullmatch(sauber))
            if treffer:
                gefunden[wort] = Treffer(wort, fundstelle)

    # 2. Über Wortgrenzen hinweg, gegen `n i g g e r` und `n-i-g-g-e-r`.
    for kette in _auseinandergezogen(text):
        for wort, muster in _muster():
            if wort not in gefunden and muster.search(kette):
                gefunden[wort] = Treffer(wort, fundstelle)

    return list(gefunden.values())


def ist_sauber(text: str) -> bool:
    return not pruefe(text)


def pruefe_lernset(name: str, items: list[dict]) -> list[Treffer]:
    """Name und alle Karten eines Lernsets prüfen.

    Die Fundstelle nennt die Karte, damit der Nutzer sie wiederfindet, ohne
    dass die Meldung das gesperrte Wort wiederholen muss.
    """
    treffer = pruefe(name, "im Namen des Lernsets")
    gesehen = {t.wort for t in treffer}

    for nummer, karte in enumerate(items or [], start=1):
        for seite, feld in (("Frage", "q"), ("Antwort", "a")):
            for fund in pruefe(str(karte.get(feld, "")), f"Karte {nummer}, {seite}"):
                if fund.wort not in gesehen:
                    gesehen.add(fund.wort)
                    treffer.append(fund)
    return treffer


def meldung(treffer: list[Treffer]) -> str:
    """Ein Satz, den man einem Menschen zeigen kann.

    Nennt bewusst die Fundstelle, aber nicht das Wort: die Meldung landet
    sonst als Bildschirmfoto in einem Klassenchat.
    """
    if not treffer:
        return ""
    stellen = ", ".join(sorted({t.fundstelle for t in treffer if t.fundstelle}))
    anzahl = len(treffer)
    was = "Ein Wort" if anzahl == 1 else f"{anzahl} Wörter"
    return (f"{was} in diesem Lernset {'steht' if anzahl == 1 else 'stehen'} auf der "
            f"Sperrliste" + (f" ({stellen})" if stellen else "")
            + ". Veröffentlichen ist damit nicht möglich. "
              "Auf deinem eigenen Rechner bleibt das Lernset unverändert.")
