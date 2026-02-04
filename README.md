# LLM-Powered Data Collection Pipeline

A streamlined pipeline for extracting structured data from scientific PDFs using Large Language Models (LLMs). This tool automates the process of reading PDFs, standardizing filenames, and processing content through an LLM to generate structured datasets (JSON/Excel).

## Features

- **Direct PDF Processing**: Uploads raw PDF files directly to the LLM context, avoiding lossy text conversion steps.
- **Automated Standardization**: Renames files to `DOI - Title.pdf` format using metadata analysis to ensure consistency and prevent duplicates.
- **State Management**: Tracks processed files via a JSON checkpoint system, allowing the pipeline to be stopped and resumed without redundant processing.
- **Structured Data Extraction**:
  - Generates individual JSON records for each document.
  - Compiles a master Excel database automatically.
- **Interactive Wizard**: A simple `main.py` script to handle configuration, API keys, and folder selection.

---

## Installation

### 1. Prerequisites
- **Python 3.8 or higher**: [Download here](https://www.python.org/downloads/).
- **LLM API Key**: A valid API key for your LLM provider (currently supports Google Gemini, with others planned).

### 2. Download the Code
- Clone this repository or click **"Code" > "Download ZIP"** on GitHub and extract the file.

### 3. Setup Dependencies

#### Windows Users:
1. Open **Command Prompt** or **PowerShell**.
2. Navigate to the folder where you extracted the code:
   ```cmd
   cd path\to\Data-collection
   ```
3. Install the required libraries:
   ```cmd
   pip install -r requirements.txt
   ```

#### Mac / Linux Users:
1. Open **Terminal**.
2. Navigate to the folder:
   ```bash
   cd /path/to/Data-collection
   ```
3. Install the required libraries:
   ```bash
   pip3 install -r requirements.txt
   ```

---

## Usage

### Interactive Wizard (Recommended)
The easiest way to run the pipeline is via the interactive wizard, which will guide you through folder selection and configuration.

**Windows:**
```cmd
python main.py
```

**Mac / Linux:**
```bash
python3 main.py
```

### Command Line Interface (Advanced)
For automated workflows or power users:

**Windows:**
```cmd
python Data-collection-pipeline.py "C:\Path\To\PDFs" --api-key YOUR_KEY
```

**Mac / Linux:**
```bash
python3 Data-collection-pipeline.py "/path/to/pdfs" --api-key YOUR_KEY
```

**Arguments:**
- `TARGET_DIR`: Path to the folder containing your PDFs (default: current directory).
- `--api-key`: Your LLM provider API key.
- `--provider`: The LLM back-end to use (default: `gemini`).
- `--no-rename`: Skip the filename standardization step.
- `--max N`: Process only the first N papers.

---

## Configuration

### Extraction Prompt
The tool uses a prompt file to guide the LLM's extraction logic. By default, it looks for `extraction_prompt.txt` in your target directory.
- **Action**: Edit this file to define exactly what data fields you need (e.g., "Extract material name, synthesis method, and bandgap").
- **Template**: A default template is created automatically if one does not exist.

### Output Structure
The pipeline organizes files within your target directory:

```
Target_Directory/
├── extraction_prompt.txt     # Instructions for the LLM
├── pipeline_checkpoint.json  # Processing log/state
├── output/                   # Extracted data
│   ├── combined_data.json
│   ├── dataset.xlsx          # Master database
│   └── [file_id].json
└── processed_pdfs/           # Successfully processed source files
```

---

## Troubleshooting

- **ModuleNotFoundError**: Run `pip install -r requirements.txt`.
- **API Errors**: Verify that your API key is valid and has access to the specified model (e.g., Gemini 2.5 Pro).
- **Renaming Issues**: If `pymupdf` is missing or the PDF metadata is corrupt, renaming will be skipped, but extraction will proceed.

---

## License
MIT License

## Citation
TBC