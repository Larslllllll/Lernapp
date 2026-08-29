"""Dialog zum Anlegen und Bearbeiten eines Lernsets.

Reine Oberflaeche. Die Kartenlogik liegt in lernapp.core.cards - hier wird nur
eingesammelt und beim Speichern zurueckgereicht.
"""
from __future__ import annotations

import uuid

import customtkinter as ctk

from ..core.cards import TripleCard


class LernsetDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save, existing=None):
        super().__init__(parent)
        self._on_save = on_save
        self._items = list(existing["items"]) if existing else []
        self._ls_id = existing["id"] if existing else str(uuid.uuid4())

        self.title("Lernset bearbeiten" if existing else "Neues Lernset")
        self.geometry("580x600")
        self.resizable(True, True)
        self.grab_set()
        self.lift()
        self.focus()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self.bind("<Escape>", lambda e: self.destroy())

        nrow = ctk.CTkFrame(self, fg_color="transparent")
        nrow.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 6))
        ctk.CTkLabel(nrow, text="Name:", font=("Arial", 13, "bold"), width=60).pack(side="left")
        self._name = ctk.CTkEntry(nrow, font=("Arial", 13), placeholder_text="Lernset-Name")
        self._name.pack(side="left", fill="x", expand=True, padx=8)
        if existing:
            self._name.insert(0, existing["name"])

        arow = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=8)
        arow.grid(row=1, column=0, sticky="ew", padx=20, pady=6)
        arow.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(arow, text="Frage", font=("Arial", 11), text_color="#888").grid(
            row=0, column=0, padx=(12, 4), pady=(8, 0), sticky="w")
        ctk.CTkLabel(arow, text="Antwort", font=("Arial", 11), text_color="#888").grid(
            row=0, column=1, padx=4, pady=(8, 0), sticky="w")
        self._q = ctk.CTkEntry(arow, font=("Arial", 12),
                               placeholder_text="z.B. être (présent il/elle)")
        self._q.grid(row=1, column=0, padx=(12, 4), pady=(2, 10), sticky="ew")
        self._a = ctk.CTkEntry(arow, font=("Arial", 12), placeholder_text="z.B. est")
        self._a.grid(row=1, column=1, padx=4, pady=(2, 10), sticky="ew")
        ctk.CTkButton(arow, text="+ Karte", width=88, height=34, font=("Arial", 12, "bold"),
                      command=self._add).grid(row=1, column=2, padx=(4, 12), pady=(2, 10))
        self._a.bind("<Return>", lambda e: self._add())

        trow = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=8)
        trow.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 6))
        trow.grid_columnconfigure((0, 1, 2), weight=1)
        for ci, lbl in enumerate(["Form 1", "Form 2", "Form 3"]):
            ctk.CTkLabel(trow, text=lbl, font=("Arial", 11), text_color="#888").grid(
                row=0, column=ci, padx=(12 if ci == 0 else 4, 4), pady=(8, 0), sticky="w")
        self._t1 = ctk.CTkEntry(trow, font=("Arial", 12), placeholder_text="z.B. go")
        self._t1.grid(row=1, column=0, padx=(12, 4), pady=(2, 10), sticky="ew")
        self._t2 = ctk.CTkEntry(trow, font=("Arial", 12), placeholder_text="z.B. went")
        self._t2.grid(row=1, column=1, padx=4, pady=(2, 10), sticky="ew")
        self._t3 = ctk.CTkEntry(trow, font=("Arial", 12), placeholder_text="z.B. gone")
        self._t3.grid(row=1, column=2, padx=4, pady=(2, 10), sticky="ew")
        ctk.CTkButton(trow, text="+ 3 Karten", width=96, height=34, font=("Arial", 12, "bold"),
                      fg_color="#2a4a7a", hover_color="#1f3a60",
                      command=self._add_triple).grid(row=1, column=3, padx=(4, 12), pady=(2, 10))
        self._t3.bind("<Return>", lambda e: self._add_triple())

        ctk.CTkLabel(self, text="Karten:", font=("Arial", 12, "bold"), anchor="w").grid(
            row=3, column=0, padx=22, pady=(4, 0), sticky="w")
        self._list = ctk.CTkScrollableFrame(self, fg_color="#141414")
        self._list.grid(row=4, column=0, sticky="nsew", padx=20, pady=4)
        ctk.CTkButton(self, text="Speichern", height=42, font=("Arial", 14, "bold"),
                      command=self._save).grid(row=5, column=0, pady=12)
        self._render()

    def _render(self):
        for w in self._list.winfo_children():
            w.destroy()
        if not self._items:
            ctk.CTkLabel(self._list, text="Noch keine Karten", text_color="#555",
                         font=("Arial", 12)).pack(pady=16)
            return
        for i, item in enumerate(self._items):
            row = ctk.CTkFrame(self._list, fg_color="#2a2a2a", corner_radius=4)
            row.pack(fill="x", pady=2, padx=2)
            ctk.CTkLabel(row, text=item["q"], font=("Arial", 12), anchor="w",
                         width=220).pack(side="left", padx=10, pady=6)
            ctk.CTkLabel(row, text="→", font=("Arial", 12), text_color="#666").pack(side="left")
            ctk.CTkLabel(row, text=item["a"], font=("Arial", 12, "bold"),
                         text_color="#5ba3e0", anchor="w", width=130).pack(side="left", padx=10)
            ctk.CTkButton(row, text="✕", width=28, height=26,
                          fg_color="#7a1a1a", hover_color="#5c1010",
                          command=lambda idx=i: self._remove(idx)).pack(side="right", padx=8)

    def _add(self):
        q = self._q.get().strip()
        a = self._a.get().strip().lower()
        if q and a:
            self._items.append({"q": q, "a": a})
            self._q.delete(0, "end")
            self._a.delete(0, "end")
            self._render()
            self._q.focus()

    def _add_triple(self):
        formen = (
            self._t1.get().strip().lower(),
            self._t2.get().strip().lower(),
            self._t3.get().strip().lower(),
        )
        if not all(formen):
            return
        # Ueber TripleCard erzeugen, damit Anzeige und Speicherformat garantiert
        # zueinander passen - auch bei mehrwortigen Formen wie "been able".
        for revealed in (0, 1, 2):
            self._items.append(TripleCard(forms=formen, revealed=revealed).legacy_item())
        for e in (self._t1, self._t2, self._t3):
            e.delete(0, "end")
        self._render()
        self._t1.focus()

    def _remove(self, idx):
        self._items.pop(idx)
        self._render()

    def _save(self):
        name = self._name.get().strip()
        if not name or not self._items:
            return
        self._on_save({"id": self._ls_id, "name": name, "items": self._items})
        self.destroy()
