# OpenCore Log Analyzer

OpenCore Log Analyzer is a simple Python application designed to analyze OpenCore boot log files by classifying log lines according to their severity level (error, warning, info, debug, success, etc.). It provides both a graphical user interface (GUI) and a command-line interface (CLI) for convenient log inspection and splitting logs into categorized files.

## Features

- **GUI mode:**
  - Select and load OpenCore log files.
  - Display log contents with color-coded highlighting based on log severity.
  - Automatically split log lines into separate files by severity (error, warning, success, other).
  - Save these categorized log files in the same directory as the original log file.
  - User-friendly status bar and notifications.

- **CLI mode:**
  - Analyze a log file from the command line.
  - Split and save categorized log files in the current working directory or script directory.
  - Suitable for automation and integration into build or CI pipelines.

- **Output "artifacts":**
  - The split log files (`error.txt`, `warning.txt`, `success.txt`, `other.txt`) can be considered artifacts that summarize the log analysis and can be collected or archived for further inspection.

## Requirements

- Python 3.x
- Standard Python libraries (`tkinter`, `argparse`, etc.)

## Installation

Clone or download the repository. No special installation required.

```bash
git clone https://github.com/Edger1ng/OpCoreLogDissasembly.git
cd OpCoreLogDissasembly
```

Alternatively, you can obtain ready-to-use artifacts from the [GitHub Actions](https://github.com/Edger1ng/OpCoreLogDissasembly/actions) page, where the latest builds and outputs are available for download.

## Usage

### GUI Mode

Simply run the script without any arguments:

```bash
python main.py
```

- Click the **Select OpenCore Log File** button.
- Choose the log file to analyze.
- The log will be displayed with colored highlighting by severity.
- The categorized log files will be saved alongside the original log file.
- A message box will confirm completion.

### CLI Mode

Run the script with the `--file` argument to analyze a log file without GUI:

```bash
python main.py --file path/to/opencore.log
```

- The script will analyze and split the log file.
- Categorized log files will be saved in the script's directory (or current working directory).
- A completion message will be printed to the console.

## Log Levels Classification

| Abbreviation | Classification |
|--------------|----------------|
| FATAL        | error          |
| ERROR        | error          |
| ERR          | error          |
| WARN         | warning        |
| WARNING      | warning        |
| INFO         | info           |
| DBG          | debug          |
| DEBUG        | debug          |
| SUCCESS      | success        |
| OK           | success        |

Lines not matching any of the above will be classified as `other`.

## Output Files

Upon analysis, the program generates the following text files (by severity):

- `success.txt` — lines classified as success
- `warning.txt` — lines classified as warning
- `error.txt` — lines classified as error
- `other.txt` — lines that don't match any classification

These files serve as artifacts for post-processing, sharing, or archival.

## Example

After loading a log file named `opencore.log`, you will find:

```
opencore.log
success.txt
warning.txt
error.txt
other.txt
```

Each file contains only the lines relevant to its severity category.

## License

MIT License — feel free to use, modify, and distribute.
