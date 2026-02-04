#!/usr/bin/env python3
"""
LLM PDF Pipeline - Public Workflow Wizard
============================================
Interactive setup for running the extraction pipeline.
"""

import os
import sys
import shutil
from pathlib import Path

# Dependency check
REQUIRED_PACKAGES = ["google.generativeai", "pandas", "openpyxl", "fitz"]
MISSING_PACKAGES = []

try:
    import google.generativeai as genai
except ImportError:
    MISSING_PACKAGES.append("google-generativeai")

try:
    import pandas as pd
except ImportError:
    MISSING_PACKAGES.append("pandas")

try:
    import openpyxl
except ImportError:
    MISSING_PACKAGES.append("openpyxl")

try:
    import fitz  # PyMuPDF
except ImportError:
    MISSING_PACKAGES.append("pymupdf")

if MISSING_PACKAGES:
    print("\n" + "!"*80)
    print("MISSING DEPENDENCIES")
    print("!"*80)
    print("Please install the required packages to run this pipeline:\n")
    print(f"  pip install {' '.join(MISSING_PACKAGES)}")
    print("\n" + "!"*80 + "\n")
    sys.exit(1)

try:
    from Data_collection_pipeline import PDFDataExtractionPipeline
except ImportError:
    # Handle the case where Python might have issues with hyphens in filenames
    try:
        import importlib
        module = importlib.import_module("Data-collection-pipeline")
        PDFDataExtractionPipeline = module.PDFDataExtractionPipeline
    except ImportError:
        print("Error: Data-collection-pipeline.py not found in current directory.")
        sys.exit(1)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_folder_path():
    """Ask user for the folder containing PDFs"""
    print("\n" + "="*60)
    print("STEP 1: SELECT INPUT FOLDER")
    print("="*60)
    print("Where are your PDF files located?")
    
    # Try using tkinter for file dialog
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()  # Hide main window
        # Check if we have a display
        if os.environ.get('DISPLAY','') or os.name == 'nt': 
            print("Opening folder selection dialog...")
            folder_selected = filedialog.askdirectory(title="Select Folder Containing PDFs")
            if folder_selected:
                print(f"Selected: {folder_selected}")
                return Path(folder_selected)
    except Exception:
        pass  # Fallback to CLI
    
    while True:
        path_str = input("\nEnter full path to folder(you may also drag and drop your folder here): ").strip()
        # Remove quotes if user dragged and dropped
        path_str = path_str.strip("'\"")
        
        path = Path(path_str)
        if path.exists() and path.is_dir():
            print(f"[OK] Valid folder found: {path}")
            return path
        else:
            print(f"[ERROR] Invalid folder. Please try again.")

def setup_api_key(target_folder: Path):
    """Setup API key (check env, check file, or ask user)"""
    print("\n" + "="*60)
    print("STEP 2: API KEY")
    print("="*60)
    
    api_key = None
    key_file = target_folder / "api_key.txt"
    # Backwards compatibility check
    old_key_file = target_folder / "Gemini-api.txt"
    
    # 1. Check environment variable
    if os.environ.get("LLM_API_KEY"):
        print("[OK] Found API key in environment variables.")
        return os.environ.get("LLM_API_KEY")
    elif os.environ.get("GEMINI_API_KEY"):  # Backwards compatibility
        print("[OK] Found API key in environment variables.")
        return os.environ.get("GEMINI_API_KEY")
    
    # 2. Check file in target folder
    if key_file.exists():
        try:
            with open(key_file, 'r') as f:
                api_key = f.read().strip()
            if api_key:
                print(f"[OK] Found api_key.txt in target folder.")
                return api_key
        except Exception:
            pass
            
    if old_key_file.exists():
        try:
            with open(old_key_file, 'r') as f:
                api_key = f.read().strip()
            if api_key:
                print(f"[OK] Found legacy key file (Gemini-api.txt).")
                return api_key
        except Exception:
            pass
            
    # 3. Check file in script directory (local dev)
    local_key_file = Path(__file__).parent / "api_key.txt"
    if local_key_file.exists():
         try:
            with open(local_key_file, 'r') as f:
                api_key = f.read().strip()
            if api_key:
                print(f"[OK] Found api_key.txt in script directory.")
                return api_key
         except Exception:
            pass

    # 4. Ask user
    print("No API key found.")
    
    while not api_key:
        api_key = input("\nEnter your LLM Provider API Key: ").strip()
    
    # Offer to save
    save = input("Save this key to api_key.txt in the data folder for next time? (y/n): ").lower()
    if save == 'y':
        try:
            with open(key_file, 'w') as f:
                f.write(api_key)
                print(f"[OK] Key saved.")
        except Exception as e:
            print(f"Warning: Could not save key file: {e}")
            
    return api_key

def setup_prompt(target_folder: Path):
    """Setup extraction prompt"""
    print("\n" + "="*60)
    print("STEP 3: EXTRACTION PROMPT")
    print("="*60)
    
    default_prompt_name = "extraction_prompt.txt"
    prompt_file = target_folder / default_prompt_name
    template_file = Path(__file__).parent / "extraction_prompt_template.txt"
    
    # 1. Check if prompt already exists in target folder
    if prompt_file.exists():
        print(f"[OK] Found existing prompt file: {prompt_file.name}")
        use_existing = input("Use this prompt? (y/n): ").lower()
        if use_existing == 'y':
            return prompt_file
    
    # 2. Create from template
    print(f"\nCreating new prompt file in your folder...")
    
    if template_file.exists():
        try:
            shutil.copy(template_file, prompt_file)
            print(f"[OK] Created {default_prompt_name} from template.")
        except Exception as e:
            print(f"Error copying template: {e}")
            # Fallback creation
            with open(prompt_file, 'w') as f:
                f.write("EXTRACT: Material Name, Synthesis Method, Bandgap")
    else:
        # Fallback if template missing
        with open(prompt_file, 'w') as f:
            f.write("EXTRACT: Material Name, Synthesis Method, Bandgap")
            print("Created basic prompt file.")
            
    print(f"\n[ACTION REQUIRED]")
    print(f"Please open '{prompt_file}' and edit it to define EXACTLY what you want to extract.")
    print("The default template is for general material synthesis.")
    
    input("\nPress Enter once you have reviewed/edited the prompt file...")
    return prompt_file

def main():
    clear_screen()
    print("="*80)
    print("="*80)
    print(" LLM DATA EXTRACTION PIPELINE")
    print("="*80)
    print("This tool will extract structured data from scientific PDFs using Local/Cloud LLMs.\n")
    
    # 1. Get Folder
    target_folder = get_folder_path()
    
    # 2. Get API Key
    api_key = setup_api_key(target_folder)
    
    # 3. Get Prompt
    prompt_file = setup_prompt(target_folder)
    
    # 4. Confirm
    pdf_count = len(list(target_folder.glob("*.pdf")))
    print("\n" + "="*60)
    print("READY TO START")
    print("="*60)
    print(f"Target:     {target_folder}")
    print(f"PDFs found: {pdf_count}")
    print(f"Prompt:     {prompt_file.name}")
    print(f"Output:     {target_folder}/output/")
    print("="*60)
    
    if pdf_count == 0:
        print("\nWARNING: No PDFs found in the selected folder.")
    
    confirm = input("\nStart extraction? (y/n): ").lower()
    if confirm != 'y':
        print("Cancelled.")
        sys.exit(0)
        
    # 5. Run Pipeline
    print("\nInitializing pipeline...")
    
    pipeline = PDFDataExtractionPipeline(
        target_dir=str(target_folder),
        api_key=api_key,
        provider="gemini",
        prompt_file=str(prompt_file),
        rename_pdfs=True,
        debug_mode=False
    )
    
    pipeline.run()
    
    print("\nDone! Press Enter to exit.")
    input()

if __name__ == "__main__":
    main()
