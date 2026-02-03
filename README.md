# Gemini PDF Extraction Pipeline 🚀

**The easiest way to extract structured data from scientific PDFs using Gemini 2.5 Pro.**

Zero configuration required. Just point it to a folder of PDFs, and it handles the rest!

## ✨ Features

- **Direct PDF Processing**: Sends the original PDF to Gemini (no messy text conversion).
- **Auto-Renaming**: Standardizes filenames to `DOI - Title.pdf` to prevent duplicates.
- **Smart Resume**: Remembers which files were processed (safe to stop and restart).
- **Structured Output**: 
  - Individual JSON files per paper.
  - **Auto-generated Excel database**.
- **User Friendly**: Interactive wizard guides you through setup.

---

## ⚡ Quick Start

### 1. Install Requirements
Make sure you have Python installed. Then run:
```bash
pip install -r requirements.txt
```

### 2. Run the Wizard
```bash
python main.py
```

### 3. Follow the Prompts
1. **Select Folder**: Choose the folder containing your PDF files.
2. **API Key**: Enter your Gemini API key (it will ask to save it securely in your folder).
   - Get a key here: [Google AI Studio](https://aistudio.google.com/app/apikey)
3. **Prompt**: The tool creates a default `extraction_prompt.txt` in your folder. **Edit this file** to tell the AI exactly what you want to extract!

---

## 📂 Output Structure

Inside your selected PDF folder, the tool creates:

```
Your_PDF_Folder/
├── extraction_prompt.txt    ← The instructions you gave the AI
├── Gemini-api.txt           ← Your saved key
├── pipeline_checkpoint.json ← Tracks progress
├── output/
│   ├── combined_extraction.json
│   ├── materials_database.xlsx  ← ✨ YOUR DATA
│   └── [individual_json_files]...
└── processed_pdfs/          ← PDFs are moved here after processing
```

---

## 📝 Customizing extraction

When you run the tool, it creates `extraction_prompt.txt`. Open this file and describe what you want in plain English.

**Example:**
```text
EXTRACT:
- Material Name
- Synthesis Method (temperature, time, precursors)
- Bandgap (in eV)
- Crystal Structure

OUTPUT FORMAT:
Return a JSON array of materials.
```

The default template provided is optimized for **Materials Science Synthesis**, but you can change it for *any* domain (Biology, Law, Finance, etc.).

---

## 🔧 Troubleshooting

- **"Module not found"**: Run `pip install -r requirements.txt` again.
- **"API Key Error"**: Check your key is valid and has access to Gemini 2.5 Pro (preview).
- **Renaming fails**: Ensure `pymupdf` is installed. The tool will skip renaming if it can't read the metadata.

---

**Author**: Advanced Agentic Coding Team
**License**: MIT
