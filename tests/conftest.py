"""Gemeinsame Test-Vorbereitung.

Qt-Tests laufen headless (offscreen) und nie gegen die echten Nutzerdaten.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
