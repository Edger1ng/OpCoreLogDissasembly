import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import argparse


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
}


COLORS = {
    "error": "red",
    "warning": "orange",
    "info": "blue",
    "debug": "gray",
    "success": "green",
    "other": "black",
}

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
        self.filepath = path
        self.status_var.set(f"Loaded file: {os.path.basename(path)}")
        self.lines = analyze_log_file(path)
        self.display_lines()

        save_split_logs(self.lines, os.path.dirname(path))
        messagebox.showinfo("Done", "Log analysis complete and split files saved.")

    def display_lines(self):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        for line in self.lines:
            lvl = classify_line(line)
            color = COLORS.get(lvl, "black")
            self.text_area.insert(tk.END, line, lvl)
            self.text_area.tag_config(lvl, foreground=color)
        self.text_area.config(state=tk.DISABLED)

def cli_mode(filepath):
    if not os.path.isfile(filepath):
        print(f"Error: file not found: {filepath}")
        sys.exit(1)
    lines = analyze_log_file(filepath)
    output_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    save_split_logs(lines, output_dir)
    print(f"Analysis complete. Files saved in {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="OpenCore Log Analyzer")
    parser.add_argument("--file", help="Path to OpenCore log file for CLI analysis")
    args = parser.parse_args()

    if args.file:
        cli_mode(args.file)
    else:
        app = LogAnalyzerGUI()
        app.mainloop()

if __name__ == "__main__":
    main()