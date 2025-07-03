import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import argparse
import time

try:
    import colorama
    from colorama import Fore, Style
    colorama.init()
except ImportError:
    Fore = Style = lambda x: ""
    print("Install 'colorama' for color support in CLI: pip install colorama")


LOG_LEVELS = {
    "FATAL": "error",
    "ERROR": "error",
    "ERR": "error",
    "WARN": "warning",
    "WARNING": "warning",
    "INFO": "info",
    "DBG": "debug",
    "DEBUG": "debug",
    "SUCCESS": "success",
    "OK": "success",
    "MAC": "platform-info",
    "INVALID":  "error"
    
}


COLORS = {
    "error": "red",
    "warning": "orange",
    "info": "blue",
    "debug": "gray",
    "success": "green",
    "other": "black",
}

def pseudo_gui_mode(filepath, clean=False, inplace=False, page_size=25):
    if not os.path.isfile(filepath):
        print(f"File not found: {filepath}")
        return

    if clean:
        filepath = clean_whitespace_lines(filepath, inplace=inplace)

    lines = analyze_log_file(filepath)

    levels_color = {
        "error": Fore.RED,
        "warning": Fore.YELLOW,
        "info": Fore.CYAN,
        "debug": Fore.LIGHTBLACK_EX,
        "success": Fore.GREEN,
        "platform-info": Fore.MAGENTA,
        "other": Fore.WHITE
    }

    def clear():
        os.system("cls" if os.name == "nt" else "clear")

    idx = 0
    total = len(lines)
    while idx < total:
        clear()
        print(f"{Fore.BLUE}{'='*40}")
        print(f"PSEUDO-GUI MODE – Viewing: {os.path.basename(filepath)}")
        print(f"{'='*40}{Style.RESET_ALL}\n")

        end = min(idx + page_size, total)
        for i in range(idx, end):
            line = lines[i]
            level = classify_line(line)
            color = levels_color.get(level, Fore.WHITE)
            print(f"{color}{line.strip()}{Style.RESET_ALL}")
        idx += page_size

        if idx < total:
            input(f"\n{Fore.YELLOW}-- More ({idx}/{total}) -- Press Enter to continue...{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.GREEN}End of log. {total} lines shown.{Style.RESET_ALL}")
            break


def classify_line(line):
    upper_line = line.upper()
    for abbr, level in LOG_LEVELS.items():
        if abbr in upper_line:
            return level
    return "other"

def save_split_logs(lines, output_dir):
    files = {
        "success": open(os.path.join(output_dir, "success.txt"), "w", encoding="utf-8"),
        "warning": open(os.path.join(output_dir, "warning.txt"), "w", encoding="utf-8"),
        "error": open(os.path.join(output_dir, "error.txt"), "w", encoding="utf-8"),
        "other": open(os.path.join(output_dir, "other.txt"), "w", encoding="utf-8"),
    }
    try:
        for line in lines:
            lvl = classify_line(line)
            if lvl not in files:
                lvl = "other"
            files[lvl].write(line)
    finally:
        for f in files.values():
            f.close()

def analyze_log_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    return lines

class LogAnalyzerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenCore Log Analyzer")
        self.geometry("800x600")

        self.btn_open = tk.Button(self, text="Select OpenCore Log File", command=self.open_file)
        self.btn_open.pack(pady=5)

        self.text_area = scrolledtext.ScrolledText(self, font=("Consolas", 10))
        self.text_area.pack(fill=tk.BOTH, expand=True)

        for level, color in COLORS.items():
            self.text_area.tag_config(level, foreground=color)

        self.status_var = tk.StringVar()
        self.status_bar = tk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(fill=tk.X)

        self.lines = []
        self.filepath = None

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Select OpenCore Log File",
            filetypes=[("Log files", "*.log *.txt"), ("All files", "*.*")]
        )
        if not path:
            return

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()


        def has_junk_lines(lines):
            for line in lines:
                raw = line.rstrip("\n\r")
                if raw == "":
                    return True
                if all(ch == '\x00' or ch.isspace() for ch in raw):
                    return True
                if len(raw) > 100 and raw.count('\x00') / len(raw) > 0.9:
                    return True
            return False

        if has_junk_lines(lines):
            answer = messagebox.askyesno(
                "Whitespace/NUL lines detected",
                "The file contains lines made mostly of whitespace or NUL characters.\n"
                "It may affect user experience, such as High CPU Usage, etc."
                "Would you like to clean the file before loading?"
            )
            if answer:
                path = clean_whitespace_lines(path, inplace=False)

        self.filepath = path
        self.lines = analyze_log_file(path)
        self.status_var.set(f"Loaded file: {os.path.basename(path)}")
        self.display_lines()

        save_split_logs(self.lines, os.path.dirname(path))
        messagebox.showinfo("Done", "Log analysis complete and split files saved.")




    def display_lines(self):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)


        i = len(self.lines) - 1
        while i >= 0:
            line = self.lines[i]

            if line.strip() == "" or classify_line(line) == "other" and line.strip().count(" ") > 50:
                i -= 1
            else:
                break
        trimmed_lines = self.lines[:i + 1]

        for line in trimmed_lines:
            lvl = classify_line(line)
            self.text_area.insert(tk.END, line, lvl)

        self.text_area.config(state=tk.DISABLED)

def is_junk_line(line: str) -> bool:
    raw = line.rstrip("\n\r")

    if raw == "":
        return True


    if all(ch == '\x00' or ch.isspace() for ch in raw):
        return True

    nul_ratio = raw.count('\x00') / len(raw)
    if nul_ratio > 0.9:
        return True


    visible = ''.join(ch for ch in raw if ch not in ('\x00', '\n', '\r') and not ch.isspace())
    if len(visible) < 5 and len(raw) > 50:
        return True

    return False


def clean_whitespace_lines(filepath, inplace=False):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    cleaned = []
    removed_count = 0

    for line in lines:
        if is_junk_line(line):
            print("[Removed]:", repr(line[:100]))
            removed_count += 1
            continue
        cleaned.append(line)

    if removed_count == 0:
        return filepath 

    if inplace:
        output_path = filepath
    else:
        base, ext = os.path.splitext(filepath)
        output_path = base + "_cleaned" + ext

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(cleaned)

    print(f"[Cleaned] Removed {removed_count} junk lines (NUL/space-only).")
    return output_path

def cli_mode(filepath, clean=False, inplace=False):
    print(
        "========================\n"
        "OpCoreLogDissasembly\n\n"
        "Your arguments:\n\n"
        f"FIle: {filepath}\n"
        f"Clean NUL Lines: {clean}\n"
        f"Inplace: {inplace}\n"
        "======================="
    )
    if not os.path.isfile(filepath):
        print(f"Error: file not found: {filepath}")
        sys.exit(1)

    if clean:
        filepath = clean_whitespace_lines(filepath, inplace=inplace)

    lines = analyze_log_file(filepath)
    output_dir = os.path.dirname(os.path.abspath(filepath))
    save_split_logs(lines, output_dir)
    print(f"Analysis complete. Files saved in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="OpenCore Log Analyzer")
    parser.add_argument("--file", help="Path to OpenCore log file for CLI analysis")
    parser.add_argument("--clean", action="store_true", help="Clean whitespace-only lines before processing")
    parser.add_argument("--inplace", action="store_true", help="Modify file in-place when cleaning")
    parser.add_argument("--pseudo", action="store_true", help="Display log in pseudo-GUI CLI mode")
    args = parser.parse_args()

    if args.file:
        if args.pseudo:
            pseudo_gui_mode(args.file, clean=args.clean, inplace=args.inplace)
        else:
            cli_mode(args.file, clean=args.clean, inplace=args.inplace)
    else:
        app = LogAnalyzerGUI()
        app.mainloop()


if __name__ == "__main__":
    main()