"""Startdaten für eine frische Installation.

Inhaltlich identisch mit dem früheren LernApp._default_data(). Diese Datei
wurde aus dem Original generiert, damit das Erststart-Verhalten unverändert
bleibt.
"""
from __future__ import annotations

import uuid

FORM_LABELS: dict[str, str] = {
    'présent': 'présent (il/elle)',
    'participe': 'participe passé',
    'impératif': 'impératif (tu)',
}

VERBEN: dict[str, dict[str, str | None]] = {
    'être': {'participe': 'été', 'présent': 'est', 'impératif': 'sois'},
    'avoir': {'participe': 'eu', 'présent': 'a', 'impératif': 'aie'},
    'aller': {'participe': 'allé', 'présent': 'va', 'impératif': 'va'},
    'faire': {'participe': 'fait', 'présent': 'fait', 'impératif': 'fais'},
    'dire': {'participe': 'dit', 'présent': 'dit', 'impératif': 'dis'},
    'lire': {'participe': 'lu', 'présent': 'lit', 'impératif': 'lis'},
    'écrire': {'participe': 'écrit', 'présent': 'écrit', 'impératif': 'écris'},
    'prendre': {'participe': 'pris', 'présent': 'prend', 'impératif': 'prends'},
    'vouloir': {'participe': 'voulu', 'présent': 'veut', 'impératif': None},
    'pouvoir': {'participe': 'pu', 'présent': 'peut', 'impératif': None},
    'devoir': {'participe': 'dû', 'présent': 'doit', 'impératif': None},
    'savoir': {'participe': 'su', 'présent': 'sait', 'impératif': None},
    'voir': {'participe': 'vu', 'présent': 'voit', 'impératif': 'vois'},
    'boire': {'participe': 'bu', 'présent': 'boit', 'impératif': 'bois'},
    'mettre': {'participe': 'mis', 'présent': 'met', 'impératif': 'mets'},
    'venir': {'participe': 'venu', 'présent': 'vient', 'impératif': 'viens'},
    'ouvrir': {'participe': 'ouvert', 'présent': 'ouvre', 'impératif': 'ouvre'},
    'connaître': {'participe': 'connu', 'présent': 'connaît', 'impératif': None},
    'partir': {'participe': 'parti', 'présent': 'part', 'impératif': 'pars'},
    'choisir': {'participe': 'choisi', 'présent': 'choisit', 'impératif': 'choisis'},
    'répondre': {'participe': 'répondu', 'présent': 'répond', 'impératif': 'réponds'},
    'manger': {'participe': 'mangé', 'présent': 'mange', 'impératif': 'mange'},
    'travailler': {'participe': 'travaillé', 'présent': 'travaille', 'impératif': 'travaille'},
    'commencer': {'participe': 'commencé', 'présent': 'commence', 'impératif': 'commence'},
    'essayer': {'participe': 'essayé', 'présent': 'essaie', 'impératif': 'essaie'},
    'préférer': {'participe': 'préféré', 'présent': 'préfère', 'impératif': None},
    'acheter': {'participe': 'acheté', 'présent': 'achète', 'impératif': 'achète'},
}


def standard_items() -> list[dict]:
    """Alle Verbformen als flache Kartenliste."""
    items = []
    for verb, formen in VERBEN.items():
        for form, antwort in formen.items():
            if antwort is not None:
                items.append({"q": f"{verb} ({FORM_LABELS[form]})", "a": antwort})
    return items


def standard_data() -> dict:
    """Grundgerüst für eine frische Installation."""
    return {
        "folders": {
            "Verben": {
                "lernsets": [
                    {
                        "id": str(uuid.uuid4()),
                        "name": "Unregelmässige Verben",
                        "items": standard_items(),
                    }
                ]
            }
        }
    }
