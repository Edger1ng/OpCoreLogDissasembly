from __future__ import annotations

import argparse
import logging
import os
import queue
import re
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk
except Exception:
    tk = None  # GUI not available


try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except Exception:
    class _NoColor:
        RED = YELLOW = GREEN = CYAN = MAGENTA = RESET = ''
    Fore = Style = _NoColor()



LEVEL_MAP = {
    r"\bFATAL\b": "error",
    r"\bERROR\b": "error",
    r"\bERR\b": "error",
    r"\bINVALID\b": "error",
    r"\bWARN(?:ING)?\b": "warning",
    r"\bWARNING\b": "warning",
    r"\bINFO\b": "info",
    r"\bDBG\b": "debug",
    r"\bDEBUG\b": "debug",
    r"\bSUCCESS\b": "success",
    r"\bOK\b": "success",
    r"\bMAC\b": "platform-info",
}

LEVEL_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(pat, re.IGNORECASE), lvl) for pat, lvl in sorted(LEVEL_MAP.items(), key=lambda x: -len(x[0]))
]

COLOR_TAGS = {
    "error": "red",
    "warning": "orange",
    "info": "blue",
    "debug": "gray",
    "success": "green",
    "platform-info": "purple",
    "other": "black",
}


STREAM_READ_THRESHOLD = 10 * 1024 * 1024  

logger = logging.getLogger("oc_log_analyzer")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(handler)




def classify_line(line: str) -> str:
    if not line:
        return "other"
    for pat, lvl in LEVEL_PATTERNS:
        if pat.search(line):
            return lvl
    return "other"


def is_junk_line(line: str) -> bool:
    if not line:
        return True
    raw = line.rstrip("\n\r")
    if raw.strip() == "":
        return True
    nul_count = raw.count("\x00")
    if len(raw) > 0 and (nul_count / len(raw)) > 0.5:
        return True
    visible = ''.join(ch for ch in raw if ch not in ('\x00', '\n', '\r') and not ch.isspace())
    if len(visible) < 5 and len(raw) > 80:
        return True
    return False


def iter_lines(path: Path, encoding: str = 'utf-8', errors: str = 'ignore') -> Iterator[str]:
    with path.open('r', encoding=encoding, errors=errors) as fh:
        for line in fh:
            yield line


def read_all_lines(path: Path) -> List[str]:
    return list(iter_lines(path))


def make_unique_path(p: Path) -> Path:
    if not p.exists():
        return p
    base = p.stem
    ext = p.suffix
    for i in range(1, 1000):
        candidate = p.with_name(f"{base}_{i}{ext}")
        if not candidate.exists():
            return candidate
    return p.with_name(f"{base}_{int(time.time())}{ext}")



def clean_whitespace_lines(path: Path, inplace: bool = False) -> Path:
    logger.info("Cleaning file: %s (inplace=%s)", path, inplace)
    if not path.exists():
        raise FileNotFoundError(path)

    out_path = path if inplace else make_unique_path(path.with_name(path.stem + "_cleaned" + path.suffix))

    removed = 0
    total = 0
    with path.open('r', encoding='utf-8', errors='ignore') as inf, out_path.open('w', encoding='utf-8') as outf:
        for line in inf:
            total += 1
            if is_junk_line(line):
                removed += 1
                continue
            outf.write(line)

    logger.info("Cleaning finished. %d removed out of %d lines. Output: %s", removed, total, out_path)
    return out_path


def save_split_logs(lines: Iterable[str], output_dir: Path, prefix: Optional[str] = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    handles = {}
    paths = {}
    try:
        for lvl in set(COLOR_TAGS.keys()):
            if lvl == 'other':
                continue
            fn = f"{prefix + '_' if prefix else ''}{lvl}.log"
            p = output_dir / fn
            p = make_unique_path(p)
            handles[lvl] = p.open('w', encoding='utf-8')
            paths[lvl] = p
        handles['other'] = (output_dir / f"{prefix + '_' if prefix else ''}other.log").open('w', encoding='utf-8')

        for line in lines:
            lvl = classify_line(line)
            if lvl not in handles:
                lvl = 'other'
            handles[lvl].write(line)
    finally:
        for h in handles.values():
            try:
                h.close()
            except Exception:
                pass
    logger.info("Split logs written to: %s", output_dir)
    return paths



def pseudo_gui_mode(path: Path, page_size: int = 25, filter_levels: Optional[List[str]] = None):
    if not path.exists():
        print("File not found:", path)
        return
    size = path.stat().st_size
    lines_iter = iter_lines(path)

    def match_level(line: str) -> bool:
        if not filter_levels:
            return True
        return classify_line(line) in filter_levels

    page = []
    printed = 0
    for line in lines_iter:
        if not match_level(line):
            continue
        page.append(line)
        if len(page) >= page_size:
            for ln in page:
                lvl = classify_line(ln)
                print(f"{ln.rstrip()}")
            printed += len(page)
            page.clear()
            inp = input(f"-- More ({printed}) -- Press Enter to continue or 'q' to quit: ")
            if inp.strip().lower() == 'q':
                return
    for ln in page:
        print(ln.rstrip())
    print("End of file.")



class LogLoaderThread(threading.Thread):
    def __init__(self, path: Path, out_queue: "queue.Queue[Tuple[int, str]]", chunk: int = 500):
        super().__init__(daemon=True)
        self.path = path
        self.out_queue = out_queue
        self.chunk = chunk
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        try:
            total = self.path.stat().st_size
        except Exception:
            total = 0
        read_bytes = 0
        count = 0
        try:
            with self.path.open('r', encoding='utf-8', errors='ignore') as fh:
                batch = []
                for line in fh:
                    if self._stop.is_set():
                        break
                    batch.append(line)
                    read_bytes += len(line.encode('utf-8', 'ignore'))
                    count += 1
                    if len(batch) >= self.chunk:
                        self.out_queue.put((count, ''.join(batch)))
                        batch = []
                if batch:
                    self.out_queue.put((count, ''.join(batch)))
        except Exception as e:
            self.out_queue.put((0, f"__ERROR__:{e}"))
        finally:
            self.out_queue.put((-1, "__DONE__"))


class LogAnalyzerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenCore Log Analyzer — 1.1.0")
        self.geometry("1050x650")

        frm = tk.Frame(self)
        frm.pack(fill=tk.X, padx=6, pady=6)

        btn_open = tk.Button(frm, text="Open Log", command=self.open_file)
        btn_open.pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        tk.Entry(frm, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=6)
        tk.Button(frm, text="Find", command=self.find_next).pack(side=tk.LEFT)

        self.chk_vars = {lvl: tk.IntVar(value=1) for lvl in COLOR_TAGS.keys()}
        for lvl in ["error", "warning", "info", "debug", "success", "platform-info"]:
            cb = tk.Checkbutton(frm, text=lvl, variable=self.chk_vars[lvl])
            cb.pack(side=tk.LEFT)

        btn_clean = tk.Button(frm, text="Clean file", command=self.clean_current_file)
        btn_clean.pack(side=tk.RIGHT)
        btn_export = tk.Button(frm, text="Export split", command=self.export_split)
        btn_export.pack(side=tk.RIGHT, padx=6)

        self.text = scrolledtext.ScrolledText(self, font=("Consolas", 10))
        self.text.pack(fill=tk.BOTH, expand=True)
        self.text.tag_configure("error", foreground="red")
        self.text.tag_configure("warning", foreground="orange")
        self.text.tag_configure("info", foreground="blue")
        self.text.tag_configure("debug", foreground="gray")
        self.text.tag_configure("success", foreground="green")
        self.text.tag_configure("platform-info", foreground="purple")
        self.text.tag_configure("other", foreground="black")

        self.status = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self.status, relief=tk.SUNKEN, anchor='w').pack(fill=tk.X)

        self.progress = ttk.Progressbar(self, mode='indeterminate')
        self.progress.pack(fill=tk.X)

        self.path: Optional[Path] = None
        self.load_thread: Optional[LogLoaderThread] = None
        self.queue: "queue.Queue[Tuple[int, str]]" = queue.Queue()
        self.after(250, self._poll_queue)

    def open_file(self):
        p = filedialog.askopenfilename(filetypes=[("Log files", "*.log *.txt"), ("All files", "*")])
        if not p:
            return
        self.load_path(Path(p))

    def load_path(self, path: Path):
        self.path = path
        self.text.config(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)
        self.status.set(f"Loading {path}...")
        self.progress.start(10)
        self.load_thread = LogLoaderThread(path, self.queue, chunk=500)
        self.load_thread.start()

    def _poll_queue(self):
        try:
            while True:
                count, payload = self.queue.get_nowait()
                if count == -1 and payload == "__DONE__":
                    self.status.set(f"Loaded: {self.path.name}")
                    self.progress.stop()
                    self.highlight_filters()
                    break
                if payload.startswith("__ERROR__:"):
                    self.status.set(payload)
                    self.progress.stop()
                    break
                # insert payload
                self._insert_chunk(payload)
        except queue.Empty:
            pass
        finally:
            self.after(250, self._poll_queue)

    def _insert_chunk(self, payload: str):
        self.text.config(state=tk.NORMAL)
        start_index = self.text.index(tk.END)
        self.text.insert(tk.END, payload)
        end_index = self.text.index(tk.END)
        for line in payload.splitlines(True):
            lvl = classify_line(line)
            try:
                self.text.insert(tk.END, "", lvl)  # ensure tag exists
            except Exception:
                pass
        self.text.config(state=tk.DISABLED)

    def highlight_filters(self):
        self.text.config(state=tk.NORMAL)
        content = self.text.get('1.0', tk.END)
        self.text.delete('1.0', tk.END)
        allowed = {lvl for lvl, var in self.chk_vars.items() if var.get()}
        for line in content.splitlines(True):
            lvl = classify_line(line)
            if lvl in allowed or lvl == 'other' and 'other' in allowed:
                self.text.insert(tk.END, line, lvl)
        self.text.config(state=tk.DISABLED)

    def find_next(self):
        term = self.search_var.get().strip()
        if not term:
            return
        idx = self.text.search(term, '1.0', tk.END)
        if not idx:
            messagebox.showinfo("Find", f"'{term}' not found")
            return
        self.text.tag_remove('search', '1.0', tk.END)
        last = f"{idx}+{len(term)}c"
        self.text.tag_add('search', idx, last)
        self.text.tag_config('search', background='yellow')
        self.text.see(idx)

    def clean_current_file(self):
        if not self.path:
            messagebox.showwarning("No file", "Open a file first")
            return
        ans = messagebox.askyesno("Clean file", "Create cleaned copy without junk lines?")
        if not ans:
            return
        out = clean_whitespace_lines(self.path, inplace=False)
        messagebox.showinfo("Cleaned", f"Cleaned file created: {out}")

    def export_split(self):
        if not self.path:
            messagebox.showwarning("No file", "Open a file first")
            return
        outdir = filedialog.askdirectory(title="Select output folder for split logs")
        if not outdir:
            return
        content = self.text.get('1.0', tk.END).splitlines(True)
        saved = save_split_logs(content, Path(outdir), prefix=self.path.stem)
        messagebox.showinfo("Exported", f"Split files: {', '.join(str(p) for p in saved.values())}")



def cli_main():
    parser = argparse.ArgumentParser(description="OpenCore Log Analyzer — improved")
    parser.add_argument('--file', '-f', type=Path, help='Log file to process')
    parser.add_argument('--clean', action='store_true', help='Create cleaned file (remove NUL/whitespace junk lines)')
    parser.add_argument('--inplace', action='store_true', help='When cleaning, overwrite original')
    parser.add_argument('--outdir', type=Path, default=None, help='Output directory for split files')
    parser.add_argument('--filter', type=str, default=None, help='Comma-separated levels to keep in pseudo viewer (e.g. INFO,ERROR)')
    parser.add_argument('--pseudo', action='store_true', help='Run simple paged CLI viewer')
    parser.add_argument('--tail', action='store_true', help='Follow appended lines (tail -f like)')
    args = parser.parse_args()

    if args.file:
        path = args.file
        if not path.exists():
            logger.error("File not found: %s", path)
            sys.exit(1)
        if args.clean:
            path = clean_whitespace_lines(path, inplace=args.inplace)
        if args.pseudo:
            fl = None
            if args.filter:
                fl = [s.strip().lower() for s in args.filter.split(',')]
            pseudo_gui_mode(path, page_size=25, filter_levels=fl)
            return
        outdir = args.outdir or path.parent
        lines = iter_lines(path)
        saved = save_split_logs(lines, outdir, prefix=path.stem)
        logger.info("Saved split logs: %s", saved)
        if args.tail:
            logger.info("Entering tail mode. Press Ctrl+C to exit.")
            try:
                with path.open('r', encoding='utf-8', errors='ignore') as fh:
                    fh.seek(0, os.SEEK_END)
                    while True:
                        line = fh.readline()
                        if not line:
                            time.sleep(0.5)
                            continue
                        print(line, end='')
            except KeyboardInterrupt:
                logger.info("Tail stopped by user")
    else:
        if tk is None:
            logger.error("Tkinter not available and no --file provided. Run with --file for CLI mode.")
            sys.exit(1)
        app = LogAnalyzerGUI()
        app.mainloop()


if __name__ == '__main__':
    cli_main()
