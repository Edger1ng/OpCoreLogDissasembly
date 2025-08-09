# OpenCore Log Analyzer — Improved

**OpenCore Log Analyzer — Improved** is an enhanced Python tool for analyzing OpenCore boot logs. It classifies log lines by severity, cleans junk lines, splits logs into categories, and works in **GUI**, **CLI**, and **interactive pseudo-GUI** modes.

## 📌 Features

### 🔹 GUI Mode

* Open and view OpenCore logs.
* Color-coded highlighting by severity (`error`, `warning`, `info`, `debug`, `success`, `platform-info`, `other`).
* Filter visible levels via checkboxes.
* Search logs (Find).
* Clean empty/NUL lines before analysis.
* Export categorized logs into separate files.
* Progress bar for large file loading.

### 🔹 CLI Mode

* Analyze logs without GUI:

  * `--clean` — remove empty/NUL lines.
  * `--inplace` — clean the file in place.
  * `--outdir` — set output directory for split files.
  * `--tail` — follow appended lines (like `tail -f`).
* Automatically split into category-based `.log` files.

### 🔹 Pseudo-GUI Mode

* `--pseudo` — page-by-page log viewing in the terminal.
* Color-coded severity display.
* Filter output by levels (`--filter ERROR,INFO`).
* Controls: Enter — continue, `q` — quit.

---

## 📂 Log Level Classification

| Pattern Match                      | Category      |
| ---------------------------------- | ------------- |
| `FATAL`, `ERROR`, `ERR`, `INVALID` | error         |
| `WARN`, `WARNING`                  | warning       |
| `INFO`                             | info          |
| `DBG`, `DEBUG`                     | debug         |
| `SUCCESS`, `OK`                    | success       |
| `MAC`                              | platform-info |
| —                                  | other         |

---

## 📦 Installation

1. Install Python **3.8+**
2. Clone the repository:

```bash
git clone https://github.com/USERNAME/REPO.git
cd REPO
```

3. (Optional) Install `colorama` for colored CLI output:

```bash
pip install colorama
```

---

Alternatively, you can obtain ready-to-use artifacts from the [GitHub Actions](https://github.com/Edger1ng/OpCoreLogDissasembly/actions) page, where the latest builds and outputs are available for download.

## 🚀 Usage

### 1. **GUI Mode**

```bash
python main.py
```

* **Open Log** — choose a file.
* Search text (Find), filter levels, clean file, and export categories.

### 2. **CLI Mode**

```bash
python main.py --file path/to/opencore.log
```

Options:

* `--clean` — remove empty/NUL lines.
* `--inplace` — clean the file in place.
* `--outdir ./logs` — set output directory.
* `--tail` — follow file changes.

Example:

```bash
python main.py --file opencore.log --clean --outdir ./split
```

### 3. **Pseudo-GUI Mode**

```bash
python main.py --file opencore.log --pseudo --filter ERROR,WARNING
```

---

## 🗂 Output Files

After analysis, the following files are created:

* `<prefix>_error.log`
* `<prefix>_warning.log`
* `<prefix>_info.log`
* `<prefix>_debug.log`
* `<prefix>_success.log`
* `<prefix>_platform-info.log`
* `<prefix>_other.log`

---

## 🧹 Junk Line Cleaning

Removes lines that are:

* completely empty;
* containing more than 50% NUL characters;
* long but with very few visible characters.

---

## 📜 License

MIT License — free to use and modify.
