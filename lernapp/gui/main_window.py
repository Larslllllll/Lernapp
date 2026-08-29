"""Hauptfenster.

Die Oberflaeche haelt keinen Lernzustand mehr selbst. Sie fragt die
LearningSession nach der naechsten Frage, reicht Antworten hinein und stellt
das zurueckgegebene Ergebnis dar.
"""
from __future__ import annotations

import random
import threading
import tkinter as tk

import customtkinter as ctk

from ..core import rules
from ..core.cards import parse_items
from ..core.learning_engine import (
    GEMISCHT,
    RUECKWAERTS,
    VORWAERTS,
    LearningSession,
    SessionZustand,
)
from ..core.progress import SetProgress
from ..storage import local_storage as store
from .lernset_dialog import LernsetDialog

try:
    import winsound

    SOUND = True
except ImportError:
    SOUND = False

DRAG_THRESHOLD = 6
SPALTEN_TITEL = ["Infinitiv", "Past Simple", "Past Participle"]


def play_sound(ok: bool) -> None:
    """Akustisches Feedback. Darf niemals das Lernen blockieren."""
    if not SOUND:
        return

    def _p():
        try:
            if ok:
                winsound.Beep(880, 80)
                winsound.Beep(1100, 100)
            else:
                winsound.Beep(200, 350)
        except Exception:
            pass

    threading.Thread(target=_p, daemon=True).start()


def run_gui() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app_data = store.load_data()
    all_prog = store.load_prog()

    # Einziger veraenderlicher Zustand der Oberflaeche: welches Set laeuft.
    aktuell: dict = {"id": None, "name": "", "session": None}

    dnd = {
        "active": False, "dragging": False,
        "ls": None, "src_folder": None,
        "start_x": 0, "start_y": 0,
        "ghost": None, "target_folder": None,
        "drop_zones": {},
    }

    app = ctk.CTk()
    app.title("LernApp")
    app.geometry("980x700")
    app.minsize(740, 540)
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)

    # -- Sidebar --------------------------------------------------------------
    sb = ctk.CTkFrame(app, width=250, corner_radius=0, fg_color="#161616")
    sb.grid(row=0, column=0, sticky="nsew")
    sb.grid_propagate(False)
    sb.grid_rowconfigure(1, weight=1)
    sb.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(sb, text="Lernsets", font=("Arial", 17, "bold")).grid(
        row=0, column=0, sticky="w", padx=14, pady=(16, 6))

    fs = ctk.CTkScrollableFrame(sb, fg_color="transparent")
    fs.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 8))

    # -- Rechter Bereich ------------------------------------------------------
    rp = ctk.CTkFrame(app, fg_color="transparent")
    rp.grid(row=0, column=1, sticky="nsew", padx=28, pady=24)
    rp.grid_columnconfigure(0, weight=1)

    hrow = ctk.CTkFrame(rp, fg_color="transparent")
    hrow.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    hrow.grid_columnconfigure(0, weight=1)
    ls_title = ctk.CTkLabel(hrow, text="← Lernset wählen", font=("Arial", 20, "bold"), anchor="w")
    ls_title.grid(row=0, column=0, sticky="w")

    def _richtung_geaendert(_wert=None):
        sess = aktuell["session"]
        if sess is not None:
            sess.richtung = dir_seg.get()

    dir_seg = ctk.CTkSegmentedButton(
        hrow, values=[VORWAERTS, RUECKWAERTS, GEMISCHT],
        font=("Arial", 14), width=120, height=30,
        command=_richtung_geaendert,
    )
    dir_seg.set(GEMISCHT)
    dir_seg.grid(row=0, column=1, padx=12)
    flame_lbl = ctk.CTkLabel(hrow, text="🔥 0", font=("Arial", 20, "bold"), text_color="#555")
    flame_lbl.grid(row=0, column=2, sticky="e")

    xr = ctk.CTkFrame(rp, fg_color="transparent")
    xr.grid(row=1, column=0, sticky="ew", pady=(0, 16))
    xr.grid_columnconfigure(1, weight=1)
    lv_lbl = ctk.CTkLabel(xr, text="Level 1", font=("Arial", 14, "bold"), width=74, anchor="w")
    lv_lbl.grid(row=0, column=0)
    xp_bar = ctk.CTkProgressBar(xr, height=14)
    xp_bar.grid(row=0, column=1, sticky="ew", padx=8)
    xp_bar.set(0)
    xp_lbl = ctk.CTkLabel(xr, text=f"0 / {rules.LEVEL_XP[1]} XP",
                          font=("Arial", 12), width=110, anchor="e")
    xp_lbl.grid(row=0, column=2)

    q_lbl = ctk.CTkLabel(rp, text="", font=("Arial", 28))
    q_lbl.grid(row=2, column=0, pady=20)

    ans_entry = ctk.CTkEntry(rp, width=320, height=54, font=("Arial", 24), justify="center")
    ans_entry.grid(row=3, column=0, pady=8)
    ans_entry.bind("<Return>", lambda e: _check())

    triple_frame = ctk.CTkFrame(rp, fg_color="transparent")
    triple_entries: list = []

    fb_lbl = ctk.CTkLabel(rp, text="", font=("Arial", 18), wraplength=580, justify="center")
    fb_lbl.grid(row=4, column=0, pady=8)
    pb = ctk.CTkProgressBar(rp, width=420)
    pb.grid(row=5, column=0, pady=10)
    pb.set(0)
    pb_txt = ctk.CTkLabel(rp, text="")
    pb_txt.grid(row=6, column=0)

    btn_row = ctk.CTkFrame(rp, fg_color="transparent")
    btn_row.grid(row=7, column=0, pady=14)
    submit_btn = ctk.CTkButton(btn_row, text="Prüfen", width=180, height=48,
                               font=("Arial", 18), command=lambda: _check())
    submit_btn.pack(side="left", padx=6)
    restart_btn = ctk.CTkButton(btn_row, text="Neustart", width=140, height=40,
                                font=("Arial", 15), fg_color="#2a7a2a", hover_color="#1f5c1f",
                                command=lambda: _restart())
    ctk.CTkButton(rp, text="Fortschritt löschen", width=170, height=30,
                  font=("Arial", 12), fg_color="#7a1a1a", hover_color="#5c1010",
                  command=lambda: _del_prog()).grid(row=8, column=0, pady=(0, 4))

    # -- Anzeige der Eingabefelder -------------------------------------------

    def _build_triple(card):
        for w in triple_frame.winfo_children():
            w.destroy()
        triple_entries.clear()
        triple_frame.grid_columnconfigure((0, 1, 2), weight=1)
        for spalte, (_i, text) in enumerate(card.slots()):
            slot = ctk.CTkFrame(triple_frame, fg_color="transparent")
            slot.grid(row=0, column=spalte, padx=10)
            ctk.CTkLabel(slot, text=SPALTEN_TITEL[spalte], font=("Arial", 11),
                         text_color="#888").pack(pady=(0, 4))
            if text is None:
                e = ctk.CTkEntry(slot, width=150, height=50,
                                 font=("Arial", 20), justify="center")
                e.pack()
                idx = len(triple_entries)

                def _on_enter(event, i=idx):
                    if i < len(triple_entries) - 1:
                        triple_entries[i + 1].focus()
                    else:
                        _check()

                e.bind("<Return>", _on_enter)
                triple_entries.append(e)
            else:
                ctk.CTkLabel(slot, text=text, font=("Arial", 22, "bold"),
                             fg_color="#2a2a2a", corner_radius=8,
                             width=150, height=50, text_color="white").pack()

    def _show_normal_mode():
        triple_frame.grid_remove()
        q_lbl.grid(row=2, column=0, pady=20)
        ans_entry.grid(row=3, column=0, pady=8)

    def _show_triple_mode():
        q_lbl.grid_remove()
        ans_entry.grid_remove()
        triple_frame.grid(row=2, column=0, pady=24)

    def _triple_disabled():
        return bool(triple_entries) and triple_entries[0].cget("state") == "disabled"

    def _set_triple_state(state):
        for e in triple_entries:
            e.configure(state=state)

    # -- Anzeige aktualisieren ------------------------------------------------

    def _refresh_xp():
        sess = aktuell["session"]
        xp = sess.fortschritt.xp if sess else 0
        level, seit, spanne = rules.level_fortschritt(xp)
        lv_lbl.configure(text=f"Level {level}")
        if spanne is None:
            xp_bar.set(1.0)
            xp_lbl.configure(text=f"{xp} XP MAX")
        else:
            xp_bar.set(seit / spanne)
            xp_lbl.configure(text=f"{xp} / {rules.LEVEL_XP[level]} XP")

    def _refresh_flame():
        sess = aktuell["session"]
        c = sess.fortschritt.current_combo if sess else 0
        farbe = "gold" if c >= 7 else "#ff4500" if c >= 4 else "#ff8c00" if c >= 2 else "#555"
        flame_lbl.configure(text=f"🔥 {c}", text_color=farbe)

    def _refresh_balken():
        sess = aktuell["session"]
        if sess is None:
            return
        done, tot = sess.fortschritt_zaehler()
        anteil = done / max(1, tot)
        pb.set(anteil)
        pb_txt.configure(text=f"{done} / {tot} gelernt  ({int(anteil * 100)}%)")

    def _persist():
        sess = aktuell["session"]
        if sess is None or not aktuell["id"]:
            return
        all_prog[aktuell["id"]] = sess.fortschritt.to_legacy()
        store.save_prog(all_prog)

    # -- Lernablauf -----------------------------------------------------------

    def _next():
        sess = aktuell["session"]
        if sess is None:
            return
        frage = sess.naechste_frage()
        if frage is None:
            _runde_beenden()
            return

        ans_entry.configure(state="normal")
        fb_lbl.configure(text="")
        _refresh_balken()

        if frage.ist_triple:
            _build_triple(frage.card)
            _show_triple_mode()
            if triple_entries:
                triple_entries[0].focus()
        else:
            _show_normal_mode()
            q_lbl.configure(text=f"{frage.anzeige}  →  ?")
            ans_entry.delete(0, "end")
            ans_entry.focus()

    def _runde_beenden():
        sess = aktuell["session"]
        if sess.naechste_runde():
            offen = len(sess.offene_keys)
            fb_lbl.configure(
                text=f"🔄  Runde {sess.runde}  —  {offen} schwache Karte"
                     f"{'n' if offen != 1 else ''}",
                text_color="#aaaaaa")
            _persist()
            _render_sidebar()
            app.after(1800, _next)
        else:
            _show_stats()

    def _check():
        sess = aktuell["session"]
        if sess is None or sess.aktuelle_frage is None:
            return
        frage = sess.aktuelle_frage

        if frage.ist_triple:
            if _triple_disabled():
                return
            eingabe = [e.get() for e in triple_entries]
        else:
            if ans_entry.cget("state") == "disabled":
                return
            eingabe = ans_entry.get()

        ergebnis = sess.antworte(eingabe)
        _refresh_flame()
        play_sound(ergebnis.richtig)
        _persist()

        if ergebnis.richtig:
            _refresh_xp()
            if frage.ist_triple:
                _set_triple_state("disabled")
            else:
                ans_entry.configure(state="disabled")
            mt = f"  ×{ergebnis.multiplikator:g}" if ergebnis.multiplikator > 1 else ""
            auch = f"\n auch: {', '.join(ergebnis.weitere)}" if ergebnis.weitere else ""
            verzoegerung = 1500 if ergebnis.level_up or auch else 700
            if ergebnis.level_up:
                fb_lbl.configure(
                    text=f"✔ Richtig  +{ergebnis.xp} XP{mt}\n"
                         f"🏆 Level Up!  Jetzt Level {sess.fortschritt.level}!{auch}",
                    text_color="gold")
            else:
                fb_lbl.configure(text=f"✔ Richtig  +{ergebnis.xp} XP{mt}{auch}",
                                 text_color="lightgreen")
            app.after(verzoegerung, _next)
        else:
            fb_lbl.configure(text=f"✘  Richtig:  {ergebnis.loesung}", text_color="#ff6b6b")
            app.after(1800, _next)

    def _show_stats():
        sess = aktuell["session"]
        ans_entry.configure(state="disabled")
        _set_triple_state("disabled")
        submit_btn.configure(state="disabled")
        q_lbl.configure(text="🏁 Alles gelernt!")
        s = sess.statistik()
        zeilen = [
            f"📊  Accuracy:  {s['accuracy'] * 100:.0f}%    "
            f"({s['richtig']} richtig · {s['falsch']} falsch)",
            f"🏆  Level {s['level']}  ·  {s['xp']} XP  ·  beste Combo {s['best_combo']}",
        ]
        if s["schwerste_karten"]:
            zeilen += ["", "Schwierigste Karten:"]
            for frage, anzahl in s["schwerste_karten"]:
                zeilen.append(f"  {frage}  —  {anzahl}× falsch")
        fb_lbl.configure(text="\n".join(zeilen), text_color="white")
        pb.set(1)
        pb_txt.configure(text="100%  ·  Fertig!")
        restart_btn.pack(side="left", padx=6)
        _render_sidebar()

    def _reaktivieren():
        ans_entry.configure(state="normal")
        _set_triple_state("normal")
        submit_btn.configure(state="normal")
        restart_btn.pack_forget()

    def _restart():
        sess = aktuell["session"]
        if sess is None:
            return
        sess.neustart()
        _persist()
        _reaktivieren()
        _refresh_xp()
        _refresh_flame()
        _next()

    def _del_prog():
        sess = aktuell["session"]
        if sess is None:
            fb_lbl.configure(text="🗑 Kein Lernset ausgewählt", text_color="gray")
            return
        sess.neustart()
        _persist()
        _reaktivieren()
        fb_lbl.configure(text="🗑 Fortschritt gelöscht", text_color="gray")
        _refresh_xp()
        _refresh_flame()
        _render_sidebar()
        _next()

    # -- Lernset waehlen ------------------------------------------------------

    def _select_ls(folder_name, ls):
        fortschritt = SetProgress.from_legacy(all_prog.get(ls["id"], {}))
        aktuell["id"] = ls["id"]
        aktuell["name"] = ls["name"]
        aktuell["session"] = LearningSession(
            parse_items(ls["items"]),
            fortschritt=fortschritt,
            rng=random.Random(),
            richtung=dir_seg.get(),
        )
        ls_title.configure(text=f"📝 {ls['name']}")
        _reaktivieren()
        _refresh_xp()
        _refresh_flame()
        _render_sidebar()
        _next()

    def _fortschritt_prozent(ls) -> int:
        """Sidebar-Prozent aus derselben Quelle wie der Fortschrittsbalken.

        Frueher zaehlte die Sidebar Triple-Teilkarten einzeln (351) und der
        Balken Pakete (117) - zwei verschiedene Zahlen fuer dasselbe Lernset.
        """
        if aktuell["id"] == ls["id"] and aktuell["session"] is not None:
            done, tot = aktuell["session"].fortschritt_zaehler()
        else:
            sitzung = LearningSession(
                parse_items(ls["items"]),
                fortschritt=SetProgress.from_legacy(all_prog.get(ls["id"], {})),
            )
            done, tot = sitzung.fortschritt_zaehler()
        return int(done / max(1, tot) * 100)

    # -- Lernsets verwalten ---------------------------------------------------

    def _move_ls(src, dst, ls_id):
        quelle = app_data["folders"][src]["lernsets"]
        ls_obj = next((l for l in quelle if l["id"] == ls_id), None)
        if not ls_obj:
            return
        app_data["folders"][src]["lernsets"] = [l for l in quelle if l["id"] != ls_id]
        app_data["folders"][dst]["lernsets"].append(ls_obj)
        store.save_data(app_data)
        _render_sidebar()

    def _delete_ls(folder_name, ls_id):
        app_data["folders"][folder_name]["lernsets"] = [
            l for l in app_data["folders"][folder_name]["lernsets"] if l["id"] != ls_id]
        if aktuell["id"] == ls_id:
            aktuell.update(id=None, name="", session=None)
            ls_title.configure(text="← Lernset wählen")
            q_lbl.configure(text="")
            fb_lbl.configure(text="")
        store.save_data(app_data)
        _render_sidebar()

    def _open_add_ls(folder_name):
        def on_save(ls):
            app_data["folders"][folder_name]["lernsets"].append(ls)
            store.save_data(app_data)
            _render_sidebar()

        LernsetDialog(app, on_save)

    def _open_edit_ls(folder_name, ls):
        def on_save(updated):
            lernsets = app_data["folders"][folder_name]["lernsets"]
            for i, l in enumerate(lernsets):
                if l["id"] == updated["id"]:
                    lernsets[i] = updated
                    break
            store.save_data(app_data)
            if aktuell["id"] == updated["id"]:
                _select_ls(folder_name, updated)
            else:
                _render_sidebar()

        LernsetDialog(app, on_save, existing=ls)

    def _add_folder():
        d = ctk.CTkInputDialog(text="Ordner Name:", title="Neuer Ordner")
        name = d.get_input()
        if name and name.strip():
            name = name.strip()
            if name not in app_data["folders"]:
                app_data["folders"][name] = {"lernsets": []}
                store.save_data(app_data)
                _render_sidebar()

    def _show_ctx_menu(event, folder_name, ls):
        menu = tk.Menu(app, tearoff=0, bg="#1e1e1e", fg="white",
                       activebackground="#1f538d", activeforeground="white",
                       relief="flat", bd=0, font=("Arial", 12))
        andere = [f for f in app_data["folders"] if f != folder_name]
        if andere:
            sub = tk.Menu(menu, tearoff=0, bg="#1e1e1e", fg="white",
                          activebackground="#1f538d", activeforeground="white",
                          relief="flat", bd=0, font=("Arial", 12))
            for fn in andere:
                sub.add_command(label=f"📁  {fn}",
                                command=lambda dst=fn: _move_ls(folder_name, dst, ls["id"]))
            menu.add_cascade(label="Verschieben nach  →", menu=sub)
            menu.add_separator()
        menu.add_command(label="✏️  Bearbeiten", command=lambda: _open_edit_ls(folder_name, ls))
        menu.add_command(label="🗑  Löschen", command=lambda: _delete_ls(folder_name, ls["id"]))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _render_sidebar():
        for w in fs.winfo_children():
            w.destroy()
        dnd["drop_zones"].clear()

        for fname, fdata in app_data["folders"].items():
            fblock = ctk.CTkFrame(fs, fg_color="#222222", corner_radius=8)
            fblock.pack(fill="x", pady=3, padx=2)
            dnd["drop_zones"][fname] = fblock

            hr = ctk.CTkFrame(fblock, fg_color="transparent")
            hr.pack(fill="x")
            ctk.CTkLabel(hr, text=f"📁  {fname}", font=("Arial", 13, "bold"),
                         anchor="w").pack(side="left", padx=10, pady=7, fill="x", expand=True)
            ctk.CTkButton(hr, text="+ Neu", width=56, height=26, font=("Arial", 11, "bold"),
                          fg_color="#1f538d", hover_color="#174070",
                          command=lambda fn=fname: _open_add_ls(fn)).pack(side="right", padx=5, pady=4)

            for ls in fdata.get("lernsets", []):
                pct = _fortschritt_prozent(ls)
                aktiv = ls["id"] == aktuell["id"]

                lsf = ctk.CTkFrame(fblock, fg_color="#1f538d" if aktiv else "#2d2d2d",
                                   corner_radius=5, cursor="hand2")
                lsf.pack(fill="x", padx=6, pady=2)
                lsl = ctk.CTkLabel(lsf, text=f"  📝  {ls['name']}  ({pct}%)",
                                   font=("Arial", 12), anchor="w")
                lsl.pack(fill="x", padx=4, pady=6, side="left", expand=True)

                normal_col = "#1f538d" if aktiv else "#2d2d2d"
                for w in (lsf, lsl):
                    w.bind("<Enter>", lambda e, f=lsf: (
                        f.configure(fg_color="#2a6aad") if not dnd["dragging"] else None))
                    w.bind("<Leave>", lambda e, f=lsf, c=normal_col: (
                        f.configure(fg_color=c) if not dnd["dragging"] else None))

                def _press(e, fn=fname, l=ls):
                    dnd.update(active=True, dragging=False, ls=l, src_folder=fn,
                               start_x=e.x_root, start_y=e.y_root)

                for w in (lsf, lsl):
                    w.bind("<ButtonPress-1>", _press)
                    w.bind("<Button-3>", lambda e, fn=fname, l=ls: _show_ctx_menu(e, fn, l))

        ctk.CTkButton(fs, text="+ Ordner hinzufügen", height=32, font=("Arial", 12),
                      fg_color="transparent", hover_color="#2a2a2a",
                      border_width=1, border_color="#444",
                      command=_add_folder).pack(fill="x", padx=4, pady=(10, 4))

    # -- Drag and Drop --------------------------------------------------------

    def _on_motion(event):
        if not dnd["active"]:
            return
        dx = abs(event.x_root - dnd["start_x"])
        dy = abs(event.y_root - dnd["start_y"])

        if not dnd["dragging"] and (dx > DRAG_THRESHOLD or dy > DRAG_THRESHOLD):
            dnd["dragging"] = True
            ghost = ctk.CTkLabel(app, text=f"  📝  {dnd['ls']['name']}  ",
                                 fg_color="#1f538d", corner_radius=6,
                                 font=("Arial", 12), text_color="white")
            ghost.lift()
            dnd["ghost"] = ghost

        if dnd["dragging"] and dnd["ghost"]:
            wx = event.x_root - app.winfo_rootx() + 12
            wy = event.y_root - app.winfo_rooty() + 12
            dnd["ghost"].place(x=wx, y=wy)
            dnd["ghost"].lift()

            dnd["target_folder"] = None
            for fname, fblock in dnd["drop_zones"].items():
                try:
                    fx, fy = fblock.winfo_rootx(), fblock.winfo_rooty()
                    fw, fh = fblock.winfo_width(), fblock.winfo_height()
                    if fx <= event.x_root <= fx + fw and fy <= event.y_root <= fy + fh:
                        dnd["target_folder"] = fname
                except Exception:
                    pass

            for fname, fblock in dnd["drop_zones"].items():
                ist_ziel = fname == dnd["target_folder"] and fname != dnd["src_folder"]
                fblock.configure(fg_color="#1a3d66" if ist_ziel else "#222222")

    def _on_release(event):
        if not dnd["active"]:
            return
        if dnd["ghost"]:
            dnd["ghost"].destroy()
            dnd["ghost"] = None
        for fblock in dnd["drop_zones"].values():
            fblock.configure(fg_color="#222222")

        if dnd["dragging"]:
            src, dst = dnd["src_folder"], dnd["target_folder"]
            if dst and dst != src:
                _move_ls(src, dst, dnd["ls"]["id"])
            else:
                _render_sidebar()
        elif dnd["ls"] and dnd["src_folder"]:
            _select_ls(dnd["src_folder"], dnd["ls"])

        dnd.update(active=False, dragging=False, ls=None, src_folder=None, target_folder=None)

    app.bind("<B1-Motion>", _on_motion, add="+")
    app.bind("<ButtonRelease-1>", _on_release, add="+")

    _render_sidebar()
    app.mainloop()
