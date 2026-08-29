# pip install customtkinter
# python Lern.py

import json, os, random, threading, uuid
import tkinter as tk
import customtkinter as ctk

try:
    import winsound; SOUND = True
except ImportError:
    SOUND = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DATA_DIR  = os.path.join(os.path.expanduser("~"), ".lernapp")
DATA_FILE = os.path.join(DATA_DIR, "data.json")
PROG_FILE = os.path.join(DATA_DIR, "progress.json")
os.makedirs(DATA_DIR, exist_ok=True)

LEVEL_XP       = [0, 50, 150, 300, 500, 750, 1000, 1500, 2000, 3000]
DRAG_THRESHOLD = 6

_VERBS = {
    "être":       {"participe": "été",       "présent": "est",       "impératif": "sois"},
    "avoir":      {"participe": "eu",        "présent": "a",         "impératif": "aie"},
    "aller":      {"participe": "allé",      "présent": "va",        "impératif": "va"},
    "faire":      {"participe": "fait",      "présent": "fait",      "impératif": "fais"},
    "dire":       {"participe": "dit",       "présent": "dit",       "impératif": "dis"},
    "lire":       {"participe": "lu",        "présent": "lit",       "impératif": "lis"},
    "écrire":     {"participe": "écrit",     "présent": "écrit",     "impératif": "écris"},
    "prendre":    {"participe": "pris",      "présent": "prend",     "impératif": "prends"},
    "vouloir":    {"participe": "voulu",     "présent": "veut",      "impératif": None},
    "pouvoir":    {"participe": "pu",        "présent": "peut",      "impératif": None},
    "devoir":     {"participe": "dû",        "présent": "doit",      "impératif": None},
    "savoir":     {"participe": "su",        "présent": "sait",      "impératif": None},
    "voir":       {"participe": "vu",        "présent": "voit",      "impératif": "vois"},
    "boire":      {"participe": "bu",        "présent": "boit",      "impératif": "bois"},
    "mettre":     {"participe": "mis",       "présent": "met",       "impératif": "mets"},
    "venir":      {"participe": "venu",      "présent": "vient",     "impératif": "viens"},
    "ouvrir":     {"participe": "ouvert",    "présent": "ouvre",     "impératif": "ouvre"},
    "connaître":  {"participe": "connu",     "présent": "connaît",   "impératif": None},
    "partir":     {"participe": "parti",     "présent": "part",      "impératif": "pars"},
    "choisir":    {"participe": "choisi",    "présent": "choisit",   "impératif": "choisis"},
    "répondre":   {"participe": "répondu",   "présent": "répond",    "impératif": "réponds"},
    "manger":     {"participe": "mangé",     "présent": "mange",     "impératif": "mange"},
    "travailler": {"participe": "travaillé", "présent": "travaille", "impératif": "travaille"},
    "commencer":  {"participe": "commencé",  "présent": "commence",  "impératif": "commence"},
    "essayer":    {"participe": "essayé",    "présent": "essaie",    "impératif": "essaie"},
    "préférer":   {"participe": "préféré",   "présent": "préfère",   "impératif": None},
    "acheter":    {"participe": "acheté",    "présent": "achète",    "impératif": "achète"},
}
_FORM_LABELS = {
    "présent":   "présent (il/elle)",
    "participe": "participe passé",
    "impératif": "impératif (tu)",
}


def _default_data():
    items = []
    for verb, forms in _VERBS.items():
        for form, ans in forms.items():
            if ans is not None:
                items.append({"q": f"{verb} ({_FORM_LABELS[form]})", "a": ans})
    return {"folders": {"Verben": {"lernsets": [
        {"id": str(uuid.uuid4()), "name": "Unregelmäßige Verben", "items": items}
    ]}}}


# ── Persistenz ────────────────────────────────────────────────────────────────

def load_data():
    if not os.path.exists(DATA_FILE):
        d = _default_data(); _save_data(d); return d
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

def load_prog():
    if not os.path.exists(PROG_FILE): return {}
    with open(PROG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_prog(p):
    with open(PROG_FILE, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2, ensure_ascii=False)


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def pkg_key(q, a):
    """Frozenset of all 3 forms for a triple card, None for normal cards."""
    if "___" not in q:
        return None
    known  = next(t for t in q.split() if t != "___")
    others = [p.strip() for p in a.split(", ")]
    return frozenset([known] + others)

def get_level(xp):
    lvl = 1
    for i, t in enumerate(LEVEL_XP):
        if xp >= t: lvl = i + 1
    return min(lvl, len(LEVEL_XP))

def combo_mul(combo):
    if combo >= 7: return 3.0
    if combo >= 4: return 2.0
    if combo >= 2: return 1.5
    return 1.0

def play_sound(ok):
    if not SOUND: return
    def _p():
        try:
            if ok: winsound.Beep(880, 80); winsound.Beep(1100, 100)
            else:  winsound.Beep(200, 350)
        except Exception: pass
    threading.Thread(target=_p, daemon=True).start()


# ── Lernset-Dialog ────────────────────────────────────────────────────────────

class LernsetDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save, existing=None):
        super().__init__(parent)
        self._on_save = on_save
        self._items   = list(existing["items"]) if existing else []
        self._ls_id   = existing["id"] if existing else str(uuid.uuid4())

        self.title("Lernset bearbeiten" if existing else "Neues Lernset")
        self.geometry("580x600")
        self.resizable(True, True)
        self.grab_set(); self.lift(); self.focus()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        nrow = ctk.CTkFrame(self, fg_color="transparent")
        nrow.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 6))
        ctk.CTkLabel(nrow, text="Name:", font=("Arial", 13, "bold"), width=60).pack(side="left")
        self._name = ctk.CTkEntry(nrow, font=("Arial", 13), placeholder_text="Lernset-Name")
        self._name.pack(side="left", fill="x", expand=True, padx=8)
        if existing: self._name.insert(0, existing["name"])

        arow = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=8)
        arow.grid(row=1, column=0, sticky="ew", padx=20, pady=6)
        arow.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(arow, text="Frage", font=("Arial", 11), text_color="#888").grid(
            row=0, column=0, padx=(12, 4), pady=(8, 0), sticky="w")
        ctk.CTkLabel(arow, text="Antwort", font=("Arial", 11), text_color="#888").grid(
            row=0, column=1, padx=4, pady=(8, 0), sticky="w")
        self._q = ctk.CTkEntry(arow, font=("Arial", 12), placeholder_text="z.B. être (présent il/elle)")
        self._q.grid(row=1, column=0, padx=(12, 4), pady=(2, 10), sticky="ew")
        self._a = ctk.CTkEntry(arow, font=("Arial", 12), placeholder_text="z.B. est")
        self._a.grid(row=1, column=1, padx=4, pady=(2, 10), sticky="ew")
        ctk.CTkButton(arow, text="+ Karte", width=88, height=34, font=("Arial", 12, "bold"),
                      command=self._add).grid(row=1, column=2, padx=(4, 12), pady=(2, 10))
        self._a.bind("<Return>", lambda e: self._add())

        # ── 3-Felder-Zeile ────────────────────────────────────────────────────
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
        for w in self._list.winfo_children(): w.destroy()
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
        q = self._q.get().strip(); a = self._a.get().strip().lower()
        if q and a:
            self._items.append({"q": q, "a": a})
            self._q.delete(0, "end"); self._a.delete(0, "end")
            self._render(); self._q.focus()

    def _add_triple(self):
        f1 = self._t1.get().strip().lower()
        f2 = self._t2.get().strip().lower()
        f3 = self._t3.get().strip().lower()
        if not (f1 and f2 and f3): return
        self._items += [
            {"q": f"{f1} ___ ___", "a": f"{f2}, {f3}"},
            {"q": f"___ {f2} ___", "a": f"{f1}, {f3}"},
            {"q": f"___ ___ {f3}", "a": f"{f1}, {f2}"},
        ]
        self._t1.delete(0, "end"); self._t2.delete(0, "end"); self._t3.delete(0, "end")
        self._render(); self._t1.focus()

    def _remove(self, idx):
        self._items.pop(idx); self._render()

    def _save(self):
        name = self._name.get().strip()
        if not name or not self._items: return
        self._on_save({"id": self._ls_id, "name": name, "items": self._items})
        self.destroy()


# ── Haupt-GUI ─────────────────────────────────────────────────────────────────


def run_gui():
    app_data = load_data()
    all_prog = load_prog()

    cur          = {"id": None, "items": [], "name": "", "q": "", "a": "", "dir": "→"}
    streaks: dict = {}
    pkg_map: dict = {}   # frozenset(forms) -> [q1, q2, q3]
    shuffle_bias  = [random.uniform(0.75, 0.85)]  # % chance of → in ⇄ mode
    round_num     = [1]
    st      = {"xp": 0, "total_correct": 0, "total_wrong": 0,
               "errors": {}, "combo_streak": 0}

    # Drag-and-drop state
    dnd = {
        "active": False, "dragging": False,
        "ls": None, "src_folder": None,
        "start_x": 0, "start_y": 0,
        "ghost": None, "target_folder": None,
        "drop_zones": {},   # fname -> fblock widget
    }

    app = ctk.CTk()
    app.title("LernApp")
    app.geometry("980x700")
    app.minsize(740, 540)
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    sb = ctk.CTkFrame(app, width=250, corner_radius=0, fg_color="#161616")
    sb.grid(row=0, column=0, sticky="nsew")
    sb.grid_propagate(False)
    sb.grid_rowconfigure(1, weight=1)
    sb.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(sb, text="Lernsets", font=("Arial", 17, "bold")).grid(
        row=0, column=0, sticky="w", padx=14, pady=(16, 6))

    fs = ctk.CTkScrollableFrame(sb, fg_color="transparent")
    fs.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 8))

    # ── Rechter Bereich ───────────────────────────────────────────────────────
    rp = ctk.CTkFrame(app, fg_color="transparent")
    rp.grid(row=0, column=1, sticky="nsew", padx=28, pady=24)
    rp.grid_columnconfigure(0, weight=1)

    hrow = ctk.CTkFrame(rp, fg_color="transparent")
    hrow.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    hrow.grid_columnconfigure(0, weight=1)
    ls_title  = ctk.CTkLabel(hrow, text="← Lernset wählen", font=("Arial", 20, "bold"), anchor="w")
    ls_title.grid(row=0, column=0, sticky="w")
    dir_seg = ctk.CTkSegmentedButton(
        hrow, values=["→", "←", "⇄"],
        font=("Arial", 14), width=120, height=30,
        command=lambda _: None,
    )
    dir_seg.set("⇄")
    dir_seg.grid(row=0, column=1, padx=12)
    flame_lbl = ctk.CTkLabel(hrow, text="🔥 0", font=("Arial", 20, "bold"), text_color="#555")
    flame_lbl.grid(row=0, column=2, sticky="e")

    xr = ctk.CTkFrame(rp, fg_color="transparent")
    xr.grid(row=1, column=0, sticky="ew", pady=(0, 16))
    xr.grid_columnconfigure(1, weight=1)
    lv_lbl = ctk.CTkLabel(xr, text="Level 1", font=("Arial", 14, "bold"), width=74, anchor="w")
    lv_lbl.grid(row=0, column=0)
    xp_bar = ctk.CTkProgressBar(xr, height=14)
    xp_bar.grid(row=0, column=1, sticky="ew", padx=8); xp_bar.set(0)
    xp_lbl = ctk.CTkLabel(xr, text=f"0 / {LEVEL_XP[1]} XP", font=("Arial", 12), width=110, anchor="e")
    xp_lbl.grid(row=0, column=2)

    q_lbl     = ctk.CTkLabel(rp, text="", font=("Arial", 28))
    q_lbl.grid(row=2, column=0, pady=20)

    # normal single-answer entry
    ans_entry = ctk.CTkEntry(rp, width=320, height=54, font=("Arial", 24), justify="center")
    ans_entry.grid(row=3, column=0, pady=8)
    ans_entry.bind("<Return>", lambda e: _check())

    # 3-box entry row (for ___ questions), hidden initially
    triple_frame   = ctk.CTkFrame(rp, fg_color="transparent")
    triple_entries = []   # filled by _build_triple()

    COL_LABELS = ["Infinitiv", "Past Simple", "Past Participle"]

    def _is_triple(q):
        return "___" in q

    def _build_triple(q):
        for w in triple_frame.winfo_children():
            w.destroy()
        triple_entries.clear()
        triple_frame.grid_columnconfigure((0, 1, 2), weight=1)
        tokens = q.split()
        blanks = [i for i, t in enumerate(tokens) if t == "___"]
        for col, (token, header) in enumerate(zip(tokens, COL_LABELS)):
            slot = ctk.CTkFrame(triple_frame, fg_color="transparent")
            slot.grid(row=0, column=col, padx=10)
            ctk.CTkLabel(slot, text=header, font=("Arial", 11),
                         text_color="#888").pack(pady=(0, 4))
            if token == "___":
                e = ctk.CTkEntry(slot, width=150, height=50,
                                 font=("Arial", 20), justify="center")
                e.pack()
                idx = len(triple_entries)
                # Enter on last blank → check; otherwise → next blank
                def _on_enter(event, i=idx):
                    if i < len(triple_entries) - 1:
                        triple_entries[i + 1].focus()
                    else:
                        _check()
                e.bind("<Return>", _on_enter)
                triple_entries.append(e)
            else:
                ctk.CTkLabel(slot, text=token, font=("Arial", 22, "bold"),
                             fg_color="#2a2a2a", corner_radius=8,
                             width=150, height=50,
                             text_color="white").pack()

    def _show_normal_mode():
        triple_frame.grid_remove()
        q_lbl.grid(row=2, column=0, pady=20)
        ans_entry.grid(row=3, column=0, pady=8)

    def _show_triple_mode():
        q_lbl.grid_remove()
        ans_entry.grid_remove()
        triple_frame.grid(row=2, column=0, columnspan=1, pady=24)

    def _triple_disabled():
        return bool(triple_entries) and triple_entries[0].cget("state") == "disabled"

    def _set_triple_state(state):
        for e in triple_entries:
            e.configure(state=state)

    fb_lbl    = ctk.CTkLabel(rp, text="", font=("Arial", 18), wraplength=580, justify="center")
    fb_lbl.grid(row=4, column=0, pady=8)
    pb        = ctk.CTkProgressBar(rp, width=420)
    pb.grid(row=5, column=0, pady=10); pb.set(0)
    pb_txt    = ctk.CTkLabel(rp, text="")
    pb_txt.grid(row=6, column=0)

    btn_row     = ctk.CTkFrame(rp, fg_color="transparent")
    btn_row.grid(row=7, column=0, pady=14)
    submit_btn  = ctk.CTkButton(btn_row, text="Prüfen", width=180, height=48,
                                 font=("Arial", 18), command=lambda: _check())
    submit_btn.pack(side="left", padx=6)
    restart_btn = ctk.CTkButton(btn_row, text="Neustart", width=140, height=40,
                                 font=("Arial", 15), fg_color="#2a7a2a", hover_color="#1f5c1f",
                                 command=lambda: _restart())
    ctk.CTkButton(rp, text="Fortschritt löschen", width=170, height=30,
                  font=("Arial", 12), fg_color="#7a1a1a", hover_color="#5c1010",
                  command=lambda: _del_prog()).grid(row=8, column=0, pady=(0, 4))

    # ── Lern-Logik ────────────────────────────────────────────────────────────

    def _build_pkg_map(items):
        pkg_map.clear()
        for it in items:
            k = pkg_key(it["q"], it["a"])
            if k is not None:
                pkg_map.setdefault(k, []).append(it["q"])

    def _count_progress():
        done = total = 0
        seen = set()
        for it in cur["items"]:
            k = pkg_key(it["q"], it["a"])
            if k is not None:
                if k in seen: continue
                seen.add(k)
                total += 1
                if all(streaks.get(m, 0) >= 1 for m in pkg_map.get(k, [it["q"]])):
                    done += 1
            else:
                total += 1
                if streaks.get(it["q"], 0) >= 1:
                    done += 1
        return done, total

    def _refresh_xp():
        lvl = get_level(st["xp"]); lv_lbl.configure(text=f"Level {lvl}")
        if lvl >= len(LEVEL_XP):
            xp_bar.set(1.0); xp_lbl.configure(text=f"{st['xp']} XP MAX")
        else:
            prev, nxt = LEVEL_XP[lvl - 1], LEVEL_XP[lvl]
            xp_bar.set((st["xp"] - prev) / (nxt - prev))
            xp_lbl.configure(text=f"{st['xp']} / {nxt} XP")

    def _award_xp(gain):
        old = get_level(st["xp"]); st["xp"] += gain; _refresh_xp()
        return get_level(st["xp"]) > old

    def _refresh_flame():
        c = st["combo_streak"]
        color = "gold" if c >= 7 else "#ff4500" if c >= 4 else "#ff8c00" if c >= 2 else "#555"
        flame_lbl.configure(text=f"🔥 {c}", text_color=color)

    def _persist():
        if not cur["id"]: return
        all_prog[cur["id"]] = {
            "xp": st["xp"], "correct": st["total_correct"], "wrong": st["total_wrong"],
            "errors": dict(st["errors"]), "combo": st["combo_streak"], "streaks": dict(streaks),
        }
        _save_prog(all_prog)

    def _start_next_round():
        # Collect items that had errors this round
        error_qs = {q for q in st["errors"] if st["errors"][q] > 0 and q in streaks}
        if not error_qs:
            _show_stats(); return

        # Reset streaks for error cards (full package reset for triple cards)
        for it in cur["items"]:
            if it["q"] in error_qs:
                k = pkg_key(it["q"], it["a"])
                if k:
                    for m in pkg_map.get(k, [it["q"]]): streaks[m] = 0
                else:
                    streaks[it["q"]] = 0

        # Reset errors for the new round
        st["errors"].clear(); st["combo_streak"] = 0
        round_num[0] += 1
        n = sum(1 for s in streaks.values() if s < 1)
        fb_lbl.configure(
            text=f"🔄  Runde {round_num[0]}  —  {n} schwache Karte{'n' if n != 1 else ''}",
            text_color="#aaaaaa")
        _persist(); _render_sidebar()
        app.after(1800, _next)

    def _next():
        remaining = [q for q, s in streaks.items() if s < 1]
        if not remaining:
            _start_next_round(); return
        ans_entry.configure(state="normal")
        weights  = [max(1, st["errors"].get(q, 0) * 3 + 1) for q in remaining]
        cur["q"] = random.choices(remaining, weights=weights, k=1)[0]
        cur["a"] = next(it["a"] for it in cur["items"] if it["q"] == cur["q"])
        fb_lbl.configure(text="")
        done, tot = _count_progress()
        pct = done / max(1, tot)
        pb.set(pct); pb_txt.configure(text=f"{done} / {tot} gelernt  ({int(pct * 100)}%)")
        if _is_triple(cur["q"]):
            cur["dir"] = "→"
            _build_triple(cur["q"])
            _show_triple_mode()
            if triple_entries: triple_entries[0].focus()
        else:
            d = dir_seg.get()
            if d == "⇄":
                cur["dir"] = "→" if random.random() < shuffle_bias[0] else "←"
            else:
                cur["dir"] = d
            _show_normal_mode()
            shown_q = cur["a"] if cur["dir"] == "←" else cur["q"]
            q_lbl.configure(text=f"{shown_q}  →  ?")
            ans_entry.delete(0, "end"); ans_entry.focus()

    def _check():
        if not cur["id"]: return
        q = cur["q"]
        if _is_triple(q):
            if _triple_disabled(): return
            expected = [p.strip() for p in cur["a"].split(", ")]
            user     = [e.get().strip().lower() for e in triple_entries]
            is_ok    = (user == expected)
            # build full display string for feedback
            tokens = q.split()
            exp_iter = iter(expected)
            full_ans = " · ".join(next(exp_iter) if t == "___" else t for t in tokens)
            ans_str  = ", ".join(user)
        else:
            if ans_entry.cget("state") == "disabled": return
            ans_str  = ans_entry.get().strip().lower()
            expected = cur["q"] if cur["dir"] == "←" else cur["a"]
            parts    = [p.strip().lower() for p in expected.replace(";", ",").split(",") if p.strip()]
            is_ok    = ans_str in parts
            others   = [p for p in parts if p != ans_str]
            full_ans = expected

        if is_ok:
            streaks[q] += 1; st["total_correct"] += 1; st["combo_streak"] += 1
            mul  = combo_mul(st["combo_streak"])
            gain = round((10 + (streaks[q] - 1) * 5) * mul)
            up   = _award_xp(gain); _refresh_flame(); play_sound(True); _persist()
            if _is_triple(q): _set_triple_state("disabled")
            else: ans_entry.configure(state="disabled")
            mt    = f"  ×{mul:g}" if mul > 1 else ""
            also  = f"\n auch: {', '.join(others)}" if not _is_triple(q) and others else ""
            delay = 1500 if up or also else 700
            if up:
                fb_lbl.configure(
                    text=f"✔ Richtig  +{gain} XP{mt}\n🏆 Level Up!  Jetzt Level {get_level(st['xp'])}!{also}",
                    text_color="gold")
            else:
                fb_lbl.configure(text=f"✔ Richtig  +{gain} XP{mt}{also}", text_color="lightgreen")
            app.after(delay, _next)
        else:
            # reset entire package on wrong triple answer
            if _is_triple(q):
                k = pkg_key(q, cur["a"])
                for m in pkg_map.get(k, [q]):
                    streaks[m] = 0
            else:
                streaks[q] = 0
            st["total_wrong"] += 1; st["combo_streak"] = 0
            st["errors"][q] = st["errors"].get(q, 0) + 1
            fb_lbl.configure(text=f"✘  Richtig:  {full_ans}", text_color="#ff6b6b")
            _refresh_flame(); play_sound(False); _persist()
            app.after(1800, _next)

    def _show_stats():
        ans_entry.configure(state="disabled"); _set_triple_state("disabled")
        submit_btn.configure(state="disabled")
        q_lbl.configure(text="🏁 Alles gelernt!")
        tot = st["total_correct"] + st["total_wrong"]; acc = st["total_correct"] / max(1, tot) * 100
        lines = [
            f"📊  Accuracy:  {acc:.0f}%    ({st['total_correct']} richtig · {st['total_wrong']} falsch)",
            f"🏆  Level {get_level(st['xp'])}  ·  {st['xp']} XP",
        ]
        if st["errors"]:
            worst = sorted(st["errors"].items(), key=lambda x: x[1], reverse=True)[:4]
            lines += ["", "Schwierigste Karten:"]
            for q, cnt in worst: lines.append(f"  {q}  —  {cnt}× falsch")
        fb_lbl.configure(text="\n".join(lines), text_color="white")
        pb.set(1); pb_txt.configure(text="100%  ·  Fertig!")
        restart_btn.pack(side="left", padx=6); _render_sidebar()

    def _restart():
        st.update(xp=0, total_correct=0, total_wrong=0, errors={}, combo_streak=0)
        for k in streaks: streaks[k] = 0
        _persist(); restart_btn.pack_forget()
        ans_entry.configure(state="normal"); _set_triple_state("normal")
        submit_btn.configure(state="normal")
        _refresh_xp(); _refresh_flame(); _next()

    def _del_prog():
        st.update(xp=0, total_correct=0, total_wrong=0, errors={}, combo_streak=0)
        if cur["id"]:
            for k in streaks: streaks[k] = 0
        _persist(); fb_lbl.configure(text="🗑 Fortschritt gelöscht", text_color="gray")
        if ans_entry.cget("state") == "disabled" or _triple_disabled():
            ans_entry.configure(state="normal"); _set_triple_state("normal")
            submit_btn.configure(state="normal"); restart_btn.pack_forget()
        _refresh_xp(); _refresh_flame(); _render_sidebar()
        if cur["id"]: _next()

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _select_ls(folder_name, ls):
        cur.update(id=ls["id"], items=ls["items"], name=ls["name"])
        p = all_prog.get(ls["id"], {})
        st.update(xp=p.get("xp", 0), total_correct=p.get("correct", 0),
                  total_wrong=p.get("wrong", 0), errors=dict(p.get("errors", {})),
                  combo_streak=p.get("combo", 0))
        round_num[0] = 1
        raw = p.get("streaks", {})
        streaks.clear()
        for item in ls["items"]: streaks[item["q"]] = raw.get(item["q"], 0)
        _build_pkg_map(ls["items"])
        shuffle_bias[0] = random.uniform(0.75, 0.85)

        ls_title.configure(text=f"📝 {ls['name']}")
        ans_entry.configure(state="normal"); submit_btn.configure(state="normal")
        restart_btn.pack_forget()
        _refresh_xp(); _refresh_flame(); _render_sidebar(); _next()

    def _move_ls(src, dst, ls_id):
        ls_obj = next((l for l in app_data["folders"][src]["lernsets"] if l["id"] == ls_id), None)
        if not ls_obj: return
        app_data["folders"][src]["lernsets"] = [
            l for l in app_data["folders"][src]["lernsets"] if l["id"] != ls_id]
        app_data["folders"][dst]["lernsets"].append(ls_obj)
        _save_data(app_data); _render_sidebar()

    def _delete_ls(folder_name, ls_id):
        app_data["folders"][folder_name]["lernsets"] = [
            l for l in app_data["folders"][folder_name]["lernsets"] if l["id"] != ls_id]
        if cur["id"] == ls_id:
            cur["id"] = None; ls_title.configure(text="← Lernset wählen")
            q_lbl.configure(text=""); fb_lbl.configure(text="")
        _save_data(app_data); _render_sidebar()

    def _open_add_ls(folder_name):
        def on_save(ls):
            app_data["folders"][folder_name]["lernsets"].append(ls)
            _save_data(app_data); _render_sidebar()
        LernsetDialog(app, on_save)

    def _open_edit_ls(folder_name, ls):
        def on_save(updated):
            lernsets = app_data["folders"][folder_name]["lernsets"]
            for i, l in enumerate(lernsets):
                if l["id"] == updated["id"]: lernsets[i] = updated; break
            _save_data(app_data)
            if cur["id"] == updated["id"]:
                cur["items"] = updated["items"]; cur["name"] = updated["name"]
                ls_title.configure(text=f"📝 {updated['name']}")
                raw = all_prog.get(cur["id"], {}).get("streaks", {})
                streaks.clear()
                for item in cur["items"]: streaks[item["q"]] = raw.get(item["q"], 0)
                _build_pkg_map(cur["items"])
            _render_sidebar()
        LernsetDialog(app, on_save, existing=ls)

    def _add_folder():
        d    = ctk.CTkInputDialog(text="Ordner Name:", title="Neuer Ordner")
        name = d.get_input()
        if name and name.strip():
            name = name.strip()
            if name not in app_data["folders"]:
                app_data["folders"][name] = {"lernsets": []}
                _save_data(app_data); _render_sidebar()

    def _show_ctx_menu(event, folder_name, ls):
        menu = tk.Menu(app, tearoff=0, bg="#1e1e1e", fg="white",
                       activebackground="#1f538d", activeforeground="white",
                       relief="flat", bd=0, font=("Arial", 12))
        others = [f for f in app_data["folders"] if f != folder_name]
        if others:
            sub = tk.Menu(menu, tearoff=0, bg="#1e1e1e", fg="white",
                          activebackground="#1f538d", activeforeground="white",
                          relief="flat", bd=0, font=("Arial", 12))
            for fn in others:
                sub.add_command(label=f"📁  {fn}",
                                command=lambda dst=fn: _move_ls(folder_name, dst, ls["id"]))
            menu.add_cascade(label="Verschieben nach  →", menu=sub)
            menu.add_separator()
        menu.add_command(label="✏️  Bearbeiten",
                         command=lambda: _open_edit_ls(folder_name, ls))
        menu.add_command(label="🗑  Löschen",
                         command=lambda: _delete_ls(folder_name, ls["id"]))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _render_sidebar():
        for w in fs.winfo_children(): w.destroy()
        dnd["drop_zones"].clear()

        for fname, fdata in app_data["folders"].items():
            fblock = ctk.CTkFrame(fs, fg_color="#222222", corner_radius=8)
            fblock.pack(fill="x", pady=3, padx=2)
            dnd["drop_zones"][fname] = fblock

            # Folder header
            hr = ctk.CTkFrame(fblock, fg_color="transparent")
            hr.pack(fill="x")
            ctk.CTkLabel(hr, text=f"📁  {fname}", font=("Arial", 13, "bold"),
                         anchor="w").pack(side="left", padx=10, pady=7, fill="x", expand=True)
            ctk.CTkButton(hr, text="+ Neu", width=56, height=26, font=("Arial", 11, "bold"),
                          fg_color="#1f538d", hover_color="#174070",
                          command=lambda fn=fname: _open_add_ls(fn)).pack(side="right", padx=5, pady=4)

            # Lernset items
            for ls in fdata.get("lernsets", []):
                p    = all_prog.get(ls["id"], {})
                tot  = len(ls["items"])
                done = sum(1 for v in p.get("streaks", {}).values() if v >= 1)
                pct  = int(done / max(1, tot) * 100)
                active = ls["id"] == cur["id"]

                lsf = ctk.CTkFrame(
                    fblock,
                    fg_color="#1f538d" if active else "#2d2d2d",
                    corner_radius=5, cursor="hand2"
                )
                lsf.pack(fill="x", padx=6, pady=2)

                lsl = ctk.CTkLabel(
                    lsf, text=f"  📝  {ls['name']}  ({pct}%)",
                    font=("Arial", 12), anchor="w"
                )
                lsl.pack(fill="x", padx=4, pady=6, side="left", expand=True)

                # Hover effect
                normal_col = "#1f538d" if active else "#2d2d2d"
                for w in (lsf, lsl):
                    w.bind("<Enter>", lambda e, f=lsf: (
                        f.configure(fg_color="#2a6aad") if not dnd["dragging"] else None))
                    w.bind("<Leave>", lambda e, f=lsf, c=normal_col: (
                        f.configure(fg_color=c) if not dnd["dragging"] else None))

                # Press: start potential drag or click
                def _press(e, fn=fname, l=ls):
                    dnd.update(active=True, dragging=False, ls=l, src_folder=fn,
                               start_x=e.x_root, start_y=e.y_root)
                for w in (lsf, lsl):
                    w.bind("<ButtonPress-1>", _press)
                    w.bind("<Button-3>", lambda e, fn=fname, l=ls: _show_ctx_menu(e, fn, l))

        # Add-folder button at the bottom
        ctk.CTkButton(
            fs, text="+ Ordner hinzufügen", height=32,
            font=("Arial", 12), fg_color="transparent",
            hover_color="#2a2a2a", border_width=1, border_color="#444",
            command=_add_folder
        ).pack(fill="x", padx=4, pady=(10, 4))

    # ── Drag-and-Drop ─────────────────────────────────────────────────────────

    def _on_motion(event):
        if not dnd["active"]: return
        dx = abs(event.x_root - dnd["start_x"])
        dy = abs(event.y_root - dnd["start_y"])

        if not dnd["dragging"] and (dx > DRAG_THRESHOLD or dy > DRAG_THRESHOLD):
            dnd["dragging"] = True
            ghost = ctk.CTkLabel(
                app, text=f"  📝  {dnd['ls']['name']}  ",
                fg_color="#1f538d", corner_radius=6,
                font=("Arial", 12), text_color="white"
            )
            ghost.lift(); dnd["ghost"] = ghost

        if dnd["dragging"] and dnd["ghost"]:
            wx = event.x_root - app.winfo_rootx() + 12
            wy = event.y_root - app.winfo_rooty() + 12
            dnd["ghost"].place(x=wx, y=wy); dnd["ghost"].lift()

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
                is_target = fname == dnd["target_folder"] and fname != dnd["src_folder"]
                fblock.configure(fg_color="#1a3d66" if is_target else "#222222")

    def _on_release(event):
        if not dnd["active"]: return

        if dnd["ghost"]:
            dnd["ghost"].destroy(); dnd["ghost"] = None

        for fblock in dnd["drop_zones"].values():
            fblock.configure(fg_color="#222222")

        if dnd["dragging"]:
            src = dnd["src_folder"]; dst = dnd["target_folder"]
            if dst and dst != src:
                _move_ls(src, dst, dnd["ls"]["id"])
            else:
                _render_sidebar()
        else:
            # regular click → select
            if dnd["ls"] and dnd["src_folder"]:
                _select_ls(dnd["src_folder"], dnd["ls"])

        dnd.update(active=False, dragging=False, ls=None, src_folder=None, target_folder=None)

    app.bind("<B1-Motion>",      _on_motion,  add="+")
    app.bind("<ButtonRelease-1>", _on_release, add="+")

    _render_sidebar()
    app.mainloop()


run_gui()
