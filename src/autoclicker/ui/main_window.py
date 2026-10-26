from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Any, Optional

import customtkinter as ctk
from pynput import keyboard as kb
from pynput import mouse as ms
from pynput.mouse import Controller as MouseControllerImpl

from ..config import (
    ClickConfig,
    HotkeyBindings,
    Profile,
    Schedule,
    default_data_dir,
    ensure_data_dir,
)
from ..engine import ClickEngine
from ..hotkeys import HotkeyManager
from ..config import Macro
from ..macro import MacroPlayer, MacroRecorder
from ..multiclicker import MultiClicker
from ..profiles import ProfileStore
from ..scheduler import Scheduler
from ..scripts import ScriptRunner


class MainWindow(ctk.CTk):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__()
        self.title("pro-autocliker")
        self.geometry("760x620")
        ensure_data_dir()

        self.mouse = MouseControllerImpl()
        self.kb_controller = kb.Controller()
        self.profile_store = ProfileStore()
        self.engine: Optional[ClickEngine] = None
        self.macro_recorder: Optional[MacroRecorder] = None
        self.macro_player: Optional[MacroPlayer] = None
        self.recording = False
        self.script_runner = ScriptRunner(self.mouse, on_status=self._status)
        self.multiclicker = MultiClicker(on_status=self._status)
        self.scheduler = Scheduler(on_trigger=self._on_schedule_trigger, base_dir=default_data_dir(), on_error=lambda e: self._status(f"scheduler error: {e}"))
        self.scheduler.start()

        self.hotkeys = HotkeyManager(HotkeyBindings())
        self.hotkeys.register("start_stop", lambda: self.after(0, self._toggle_engine))
        self.hotkeys.register("record_macro", lambda: self.after(0, self._toggle_record_macro))
        self.hotkeys.register("emergency_stop", lambda: self.after(0, self._emergency_stop))
        try:
            self.hotkeys.start()
        except Exception as exc:
            self._status(f"hotkeys unavailable: {exc}")

        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        for name in ("Clicker", "Profiles", "Macros", "Scheduler", "Scripts", "Multi"):
            self.tabview.add(name)

        self._build_clicker_tab(self.tabview.tab("Clicker"))
        self._build_profiles_tab(self.tabview.tab("Profiles"))
        self._build_macros_tab(self.tabview.tab("Macros"))
        self._build_scheduler_tab(self.tabview.tab("Scheduler"))
        self._build_scripts_tab(self.tabview.tab("Scripts"))
        self._build_multi_tab(self.tabview.tab("Multi"))

        self.status_label = ctk.CTkLabel(self, text="ready", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=(0, 8))

    def _build_clicker_tab(self, tab: Any) -> None:
        frm = ctk.CTkFrame(tab)
        frm.pack(fill="both", expand=True, padx=8, pady=8)

        r = 0
        ctk.CTkLabel(frm, text="Button").grid(row=r, column=0, sticky="w", pady=2)
        self.button_var = ctk.StringVar(value="left")
        ctk.CTkOptionMenu(frm, values=["left", "right", "middle"], variable=self.button_var).grid(row=r, column=1, pady=2)
        r += 1

        ctk.CTkLabel(frm, text="Mode").grid(row=r, column=0, sticky="w", pady=2)
        self.mode_var = ctk.StringVar(value="cursor")
        ctk.CTkOptionMenu(frm, values=["cursor", "fixed"], variable=self.mode_var).grid(row=r, column=1, pady=2)
        r += 1

        ctk.CTkLabel(frm, text="X").grid(row=r, column=0, sticky="w", pady=2)
        self.x_entry = ctk.CTkEntry(frm)
        self.x_entry.insert(0, "0")
        self.x_entry.grid(row=r, column=1, pady=2)
        r += 1
        ctk.CTkLabel(frm, text="Y").grid(row=r, column=0, sticky="w", pady=2)
        self.y_entry = ctk.CTkEntry(frm)
        self.y_entry.insert(0, "0")
        self.y_entry.grid(row=r, column=1, pady=2)
        r += 1

        self.restore_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frm, text="Restore cursor after fixed click", variable=self.restore_var).grid(row=r, column=0, columnspan=2, sticky="w", pady=2)
        r += 1

        ctk.CTkLabel(frm, text="Interval ms").grid(row=r, column=0, sticky="w", pady=2)
        self.interval_entry = ctk.CTkEntry(frm)
        self.interval_entry.insert(0, "100")
        self.interval_entry.grid(row=r, column=1, pady=2)
        r += 1

        ctk.CTkLabel(frm, text="Jitter ms").grid(row=r, column=0, sticky="w", pady=2)
        self.jitter_entry = ctk.CTkEntry(frm)
        self.jitter_entry.insert(0, "0")
        self.jitter_entry.grid(row=r, column=1, pady=2)
        r += 1

        ctk.CTkLabel(frm, text="Count (0=infinite)").grid(row=r, column=0, sticky="w", pady=2)
        self.count_entry = ctk.CTkEntry(frm)
        self.count_entry.insert(0, "0")
        self.count_entry.grid(row=r, column=1, pady=2)
        r += 1

        ctk.CTkLabel(frm, text="Click type").grid(row=r, column=0, sticky="w", pady=2)
        self.clicktype_var = ctk.StringVar(value="single")
        ctk.CTkOptionMenu(frm, values=["single", "double", "hold"], variable=self.clicktype_var).grid(row=r, column=1, pady=2)
        r += 1

        ctk.CTkLabel(frm, text="Hold duration ms").grid(row=r, column=0, sticky="w", pady=2)
        self.hold_entry = ctk.CTkEntry(frm)
        self.hold_entry.insert(0, "50")
        self.hold_entry.grid(row=r, column=1, pady=2)
        r += 1

        btns = ctk.CTkFrame(frm)
        btns.grid(row=r, column=0, columnspan=2, pady=10)
        ctk.CTkButton(btns, text="Start (F6)", command=self._start_engine).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Stop (F6)", command=self._stop_engine).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="EMERGENCY STOP (F12)", fg_color="#c0392b", hover_color="#e74c3c", command=self._emergency_stop).pack(side="left", padx=4)

        ctk.CTkLabel(frm, text="Hotkeys: F6 start/stop, F7 record macro, F12 emergency stop").grid(row=r + 1, column=0, columnspan=2, pady=4)

    def _build_profiles_tab(self, tab: Any) -> None:
        frm = ctk.CTkFrame(tab)
        frm.pack(fill="both", expand=True, padx=8, pady=8)
        self.profile_name_entry = ctk.CTkEntry(frm, placeholder_text="profile name")
        self.profile_name_entry.pack(fill="x", pady=4)
        row = ctk.CTkFrame(frm)
        row.pack(fill="x", pady=4)
        ctk.CTkButton(row, text="Save current", command=self._save_profile).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Load", command=self._load_profile).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Delete", command=self._delete_profile).pack(side="left", padx=4)
        self.profile_list = ctk.CTkTextbox(frm, height=200)
        self.profile_list.pack(fill="both", expand=True, pady=4)
        self._refresh_profile_list()

    def _build_macros_tab(self, tab: Any) -> None:
        frm = ctk.CTkFrame(tab)
        frm.pack(fill="both", expand=True, padx=8, pady=8)
        self.macro_name_entry = ctk.CTkEntry(frm, placeholder_text="macro name")
        self.macro_name_entry.pack(fill="x", pady=4)
        self.macro_speed_entry = ctk.CTkEntry(frm)
        self.macro_speed_entry.insert(0, "1.0")
        self.macro_speed_entry.pack(fill="x", pady=4)
        self.record_kb_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frm, text="Record keyboard (warning: captures keystrokes)", variable=self.record_kb_var).pack(anchor="w", pady=4)
        row = ctk.CTkFrame(frm)
        row.pack(fill="x", pady=4)
        ctk.CTkButton(row, text="Record/Stop (F7)", command=self._toggle_record_macro).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Play", command=self._play_macro).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Stop", command=self._stop_macro).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Save", command=self._save_macro).pack(side="left", padx=4)
        self.macro_status = ctk.CTkLabel(frm, text="no macro loaded")
        self.macro_status.pack(anchor="w", pady=4)
        self._current_macro: Optional[Macro] = None

    def _build_scheduler_tab(self, tab: Any) -> None:
        frm = ctk.CTkFrame(tab)
        frm.pack(fill="both", expand=True, padx=8, pady=8)
        self.sched_profile_entry = ctk.CTkEntry(frm, placeholder_text="profile name")
        self.sched_profile_entry.pack(fill="x", pady=4)
        self.sched_time_entry = ctk.CTkEntry(frm, placeholder_text="YYYY-MM-DD HH:MM:SS")
        self.sched_time_entry.pack(fill="x", pady=4)
        self.sched_repeat_var = ctk.StringVar(value="once")
        ctk.CTkOptionMenu(frm, values=["once", "daily"], variable=self.sched_repeat_var).pack(anchor="w", pady=4)
        row = ctk.CTkFrame(frm)
        row.pack(fill="x", pady=4)
        ctk.CTkButton(row, text="Add schedule", command=self._add_schedule).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Refresh", command=self._refresh_schedule_list).pack(side="left", padx=4)
        self.sched_list = ctk.CTkTextbox(frm, height=200)
        self.sched_list.pack(fill="both", expand=True, pady=4)
        self._refresh_schedule_list()

    def _build_scripts_tab(self, tab: Any) -> None:
        frm = ctk.CTkFrame(tab)
        frm.pack(fill="both", expand=True, padx=8, pady=8)
        self.script_box = ctk.CTkTextbox(frm, height=300)
        self.script_box.pack(fill="both", expand=True, pady=4)
        self.script_box.insert("1.0", "click left at 100,200\nwait 500\nmove 300,400\n")
        row = ctk.CTkFrame(frm)
        row.pack(fill="x", pady=4)
        ctk.CTkButton(row, text="Run", command=self._run_script).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Stop", command=self._stop_script).pack(side="left", padx=4)

    def _build_multi_tab(self, tab: Any) -> None:
        frm = ctk.CTkFrame(tab)
        frm.pack(fill="both", expand=True, padx=8, pady=8)
        row = ctk.CTkFrame(frm)
        row.pack(fill="x", pady=4)
        ctk.CTkButton(row, text="Add stream (current config)", command=self._add_stream).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Start all", command=self._multi_start_all).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Stop all", command=self._multi_stop_all).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Clear", command=self._multi_clear).pack(side="left", padx=4)
        self.multi_info = ctk.CTkLabel(frm, text="streams: 0")
        self.multi_info.pack(anchor="w", pady=4)
        self._update_multi_info()

    # ---------- helpers ----------
    def _status(self, msg: str) -> None:
        def _do() -> None:
            self.status_label.configure(text=str(msg))
        self.after(0, _do)

    def _read_config(self) -> ClickConfig:
        return ClickConfig(
            button=self.button_var.get(),
            mode=self.mode_var.get(),
            x=int(self.x_entry.get() or 0),
            y=int(self.y_entry.get() or 0),
            restore_cursor=bool(self.restore_var.get()),
            interval_ms=int(self.interval_entry.get() or 100),
            interval_jitter_ms=int(self.jitter_entry.get() or 0),
            count=int(self.count_entry.get() or 0),
            click_type=self.clicktype_var.get(),
            hold_duration_ms=int(self.hold_entry.get() or 50),
        )

    def _start_engine(self) -> None:
        if self.engine is not None and self.engine.is_running:
            return
        try:
            cfg = self._read_config()
        except ValueError as exc:
            self._status(f"invalid config: {exc}")
            return
        self.engine = ClickEngine(cfg, self.mouse, on_status=self._status)
        self.engine.start()

    def _stop_engine(self) -> None:
        if self.engine is not None:
            self.engine.stop()

    def _toggle_engine(self) -> None:
        if self.engine is not None and self.engine.is_running:
            self._stop_engine()
        else:
            self._start_engine()

    def _emergency_stop(self) -> None:
        self._stop_engine()
        if self.macro_player is not None:
            self.macro_player.stop()
        if self.recording and self.macro_recorder is not None:
            self.macro_recorder.stop()
            self.recording = False
        self.script_runner.stop()
        self.multiclicker.stop_all()
        self._status("EMERGENCY STOP")

    def _save_profile(self) -> None:
        name = self.profile_name_entry.get().strip() or "default"
        try:
            cfg = self._read_config()
        except ValueError as exc:
            self._status(f"invalid config: {exc}")
            return
        profile = Profile(name=name, config=cfg)
        self.profile_store.upsert(profile)
        self._refresh_profile_list()
        self._status(f"profile saved: {name}")

    def _load_profile(self) -> None:
        name = self.profile_name_entry.get().strip()
        profile = self.profile_store.get(name)
        if profile is None:
            self._status("profile not found")
            return
        c = profile.config
        self.button_var.set(c.button)
        self.mode_var.set(c.mode)
        self.x_entry.delete(0, "end")
        self.x_entry.insert(0, str(c.x))
        self.y_entry.delete(0, "end")
        self.y_entry.insert(0, str(c.y))
        self.restore_var.set(c.restore_cursor)
        self.interval_entry.delete(0, "end")
        self.interval_entry.insert(0, str(c.interval_ms))
        self.jitter_entry.delete(0, "end")
        self.jitter_entry.insert(0, str(c.interval_jitter_ms))
        self.count_entry.delete(0, "end")
        self.count_entry.insert(0, str(c.count))
        self.clicktype_var.set(c.click_type)
        self.hold_entry.delete(0, "end")
        self.hold_entry.insert(0, str(c.hold_duration_ms))
        self._status(f"profile loaded: {name}")

    def _delete_profile(self) -> None:
        name = self.profile_name_entry.get().strip()
        self.profile_store.delete(name)
        self._refresh_profile_list()
        self._status(f"profile deleted: {name}")

    def _refresh_profile_list(self) -> None:
        self.profile_list.delete("1.0", "end")
        for p in self.profile_store.load_all():
            self.profile_list.insert("end", p.name + "\n")

    # ---------- macros ----------
    def _toggle_record_macro(self) -> None:
        if not self.recording:
            self.macro_recorder = MacroRecorder(record_keyboard=bool(self.record_kb_var.get()))
            self.macro_recorder.start()
            self.recording = True
            self.macro_status.configure(text="recording...")
            self._status("macro recording started")
        else:
            assert self.macro_recorder is not None
            events = self.macro_recorder.stop()
            self.recording = False
            name = self.macro_name_entry.get().strip() or "macro"
            try:
                speed = float(self.macro_speed_entry.get() or 1.0)
            except ValueError:
                speed = 1.0
            try:
                self._current_macro = Macro(name=name, events=events, speed=speed, record_keyboard=bool(self.record_kb_var.get()))
            except ValueError as exc:
                self.macro_status.configure(text="macro invalid")
                self._status(f"invalid macro speed: {exc}")
                return
            self.macro_status.configure(text=f"recorded {len(events)} events")
            self._status("macro recording stopped")

    def _play_macro(self) -> None:
        if self._current_macro is None:
            self._status("no macro loaded")
            return
        if self.macro_player is not None and self.macro_player.is_running:
            self._status("macro already playing")
            return
        self.macro_player = MacroPlayer(self._current_macro, self.mouse, self.kb_controller)
        self.macro_player.start(on_status=self._status)

    def _stop_macro(self) -> None:
        if self.macro_player is not None:
            self.macro_player.stop()

    def _save_macro(self) -> None:
        if self._current_macro is None:
            self._status("no macro to save")
            return
        import json
        from pathlib import Path

        d = default_data_dir() / "macros.json"
        data: list[dict[str, Any]] = []
        try:
            loaded = json.loads(d.read_text(encoding="utf-8")) if d.exists() else []
            if isinstance(loaded, list):
                data = [m for m in loaded if isinstance(m, dict)]
        except Exception:
            data = []
        # upsert by name
        data = [m for m in data if m.get("name") != self._current_macro.name]
        data.append(self._current_macro.model_dump(mode="json"))
        from ..config import atomic_write_json

        atomic_write_json(d, data)
        self._status(f"macro saved: {self._current_macro.name}")

    # ---------- scheduler ----------
    def _add_schedule(self) -> None:
        name = f"sched_{len(self.scheduler.load()) + 1}"
        profile_name = self.sched_profile_entry.get().strip()
        when_str = self.sched_time_entry.get().strip()
        try:
            when = datetime.strptime(when_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self._status("bad datetime format")
            return
        sched = Schedule(name=name, profile_name=profile_name, run_at=when, repeat=self.sched_repeat_var.get())
        self.scheduler.add(sched)
        self._refresh_schedule_list()
        self._status(f"schedule added: {name}")

    def _refresh_schedule_list(self) -> None:
        self.sched_list.delete("1.0", "end")
        for s in self.scheduler.load():
            self.sched_list.insert("end", f"{s.name}: {s.profile_name} @ {s.run_at} ({s.repeat}) enabled={s.enabled}\n")

    def _on_schedule_trigger(self, sched: Schedule) -> None:
        self.after(0, lambda: self._run_scheduled(sched))

    def _run_scheduled(self, sched: Schedule) -> None:
        profile = self.profile_store.get(sched.profile_name)
        if profile is None:
            self._status(f"schedule profile missing: {sched.profile_name}")
            return
        if self.engine is not None and self.engine.is_running:
            self.engine.stop()
        cfg = profile.config
        eng = ClickEngine(cfg, self.mouse, on_status=self._status)
        eng.start()
        self.engine = eng
        self._status(f"scheduled run: {sched.name}")

    # ---------- scripts ----------
    def _run_script(self) -> None:
        src = self.script_box.get("1.0", "end")
        self.script_runner.run(src)

    def _stop_script(self) -> None:
        self.script_runner.stop()

    # ---------- multi ----------
    def _add_stream(self) -> None:
        try:
            cfg = self._read_config()
        except ValueError as exc:
            self._status(f"invalid config: {exc}")
            return
        self.multiclicker.add(cfg)
        self._update_multi_info()

    def _multi_start_all(self) -> None:
        self.multiclicker.start_all()
        self._update_multi_info()

    def _multi_stop_all(self) -> None:
        self.multiclicker.stop_all()
        self._update_multi_info()

    def _multi_clear(self) -> None:
        self.multiclicker.clear()
        self._update_multi_info()

    def _update_multi_info(self) -> None:
        self.multi_info.configure(text=f"streams: {len(self.multiclicker.engines)}")

    def destroy(self) -> None:
        try:
            self._stop_engine()
        except Exception:
            pass
        try:
            if self.recording and self.macro_recorder is not None:
                self.macro_recorder.stop()
                self.recording = False
        except Exception:
            pass
        try:
            if self.macro_player is not None:
                self.macro_player.stop()
        except Exception:
            pass
        try:
            self.script_runner.stop()
        except Exception:
            pass
        try:
            self.multiclicker.stop_all()
        except Exception:
            pass
        try:
            self.scheduler.stop()
        except Exception:
            pass
        try:
            self.hotkeys.stop()
        except Exception:
            pass
        super().destroy()