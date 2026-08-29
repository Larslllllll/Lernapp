"""LernApp - Einstiegspunkt.

Die Lernlogik liegt in lernapp/core (GUI-frei und getestet), die Oberflaeche in
lernapp/gui, die Persistenz in lernapp/storage.

Start:  python LernApp.py
"""
from lernapp.gui.main_window import run_gui

if __name__ == "__main__":
    run_gui()
