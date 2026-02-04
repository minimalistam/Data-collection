#!/usr/bin/env python3

import os
import sys
import json
import time
import re
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd

# Gemini imports
try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed!")
    print("Install: pip install google-generativeai")
    sys.exit(1)

# PyMuPDF for PDF renaming
try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    print("WARNING: PyMuPDF not installed - PDF renaming disabled")
    print("Install with: pip install PyMuPDF")


# ═══════════════════════════════════════════════════════════════════════════════
# PDF RENAMING UTILITIES (Integrated from pdf_renamer.py)
# ═══════════════════════════════════════════════════════════════════════════════

def clean_filename(text: str, max_len: int = 100) -> str:
    """Clean text for Windows-safe filename"""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    invalid_chars = r'<>:"/\|?*'
    for char in invalid_chars:
        text = text.replace(char, "")
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(". ")
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0]
    return text or "Untitled"


def extract_doi_from_metadata(pdf_path: Path) -> Optional[str]:
    """Extract DOI from PDF metadata"""
    if not HAS_PYMUPDF:
        return None
    try:
        with fitz.open(pdf_path) as doc:
            metadata = doc.metadata or {}
            for key in ["subject", "keywords", "doi", "DOI"]:
                value = metadata.get(key, "")
                if value:
                    doi_match = re.search(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", value, re.I)
                    if doi_match:
                        return doi_match.group(1).rstrip(" .,;")
    except Exception:
        pass
    return None


def extract_doi_from_text(pdf_path: Path) -> Optional[str]:
    """Extract DOI from PDF text content"""
    if not HAS_PYMUPDF:
        return None
    try:
        with fitz.open(pdf_path) as doc:
            pages_to_check = min(3, len(doc))
            for page_num in range(pages_to_check):
                text = doc[page_num].get_text()
                patterns = [
                    r"(?:doi|DOI)[\s:]*\s*(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
                    r"(?:dx\.doi\.org|doi\.org)/\s*(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
                    r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b",
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.I)
                    if match:
                        doi = match.group(1).rstrip(" .,;)")
                        if "/" in doi and len(doi) > 7:
                            return doi
    except Exception:
        pass
    return None


def extract_title_from_metadata(pdf_path: Path) -> Optional[str]:
    """Extract title from PDF metadata"""
    if not HAS_PYMUPDF:
        return None
    try:
        with fitz.open(pdf_path) as doc:
            title = doc.metadata.get("title", "").strip()
            if title and len(title) > 10:
                return title
    except Exception:
        pass
    return None


def extract_title_from_text(pdf_path: Path) -> str:
    """Extract title from PDF text content using heuristics"""
    if not HAS_PYMUPDF:
        return "Untitled"
    try:
        with fitz.open(pdf_path) as doc:
            if len(doc) == 0:
                return "Untitled"
            text = doc[0].get_text()
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if not lines:
                return "Untitled"
            
            exclude_patterns = [
                r"(?i)doi[\s:]",
                r"(?i)published|received|accepted",
                r"(?i)volume|issue|page",
                r"(?i)copyright|©|\(c\)",
                r"^\d+$",
                r"^[A-Z\s]{3,}$",
            ]
            
            for line in lines[:10]:
                if 15 <= len(line) <= 200:
                    if not any(re.search(pat, line) for pat in exclude_patterns):
                        return line
            
            for line in lines[:5]:
                if len(line) > 10:
                    return line
    except Exception:
        pass
    return "Untitled"


def extract_doi_and_title(pdf_path: Path) -> Tuple[Optional[str], str]:
    """Extract DOI and title from PDF"""
    doi = extract_doi_from_metadata(pdf_path) or extract_doi_from_text(pdf_path)
    title = extract_title_from_metadata(pdf_path) or extract_title_from_text(pdf_path)
    return doi, title


def get_unique_path(path: Path) -> Path:
    """Return non-colliding file path by appending (n) if needed"""
    if not path.exists():
        return path
    base_name = path.stem
    extension = path.suffix
    parent = path.parent
    counter = 2
    while True:
        new_path = parent / f"{base_name} ({counter}){extension}"
        if not new_path.exists():
            return new_path
        counter += 1

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class PDFDataExtractionPipeline:
    """
    Generic pipeline for extracting structured data from PDFs using LLMs.
    Currently supports: Google Gemini
    """
    
    def __init__(self, 
                 target_dir: str,
                 api_key: str,
                 provider: str = "gemini",
                 prompt_file: str = None,
                 rename_pdfs: bool = True,
                 debug_mode: bool = False):
        """
        Initialize PDF Extraction Pipeline
        
        Args:
            target_dir: The folder containing PDF files to process.
            api_key: API Key for the LLM provider.
            provider: LLM provider ("gemini" supported).
            prompt_file: Path to custom prompt file (optional). 
                         Defaults to 'extraction_prompt.txt' in target_dir.
            rename_pdfs: Standardize filenames (True/False).
            debug_mode: Save raw API responses for debugging.
        """
        
        self.workspace_dir = Path(__file__).parent.absolute()
        self.provider = provider.lower()
        self.target_dir = Path(target_dir)
        
        # 1. Setup Organized Folder Structure
        self.input_dir = self.target_dir  # We scan root of target_dir
        self.output_dir = self.target_dir / "output"
        self.processed_dir = self.target_dir / "processed_pdfs"
        self.checkpoint_file = self.target_dir / "pipeline_checkpoint.json"
        
        # 2. Setup Logs & Configs
        self.renamed_log = self.target_dir / "renamed_files.json"
        if prompt_file:
            self.prompt_file = Path(prompt_file)
        else:
            self.prompt_file = self.target_dir / "extraction_prompt.txt"
        
        self.rename_pdfs = rename_pdfs
        self.debug_mode = debug_mode
        
        # 3. Create necessary subfolders
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        print("-" * 60)
        print(f"PDF EXTRACTION PIPELINE ({self.provider.upper()})")
        print("-" * 60)
        print(f"Target Folder: {self.target_dir}")
        print(f" • Output:     {self.output_dir.name}/")
        print(f" • Processed:  {self.processed_dir.name}/")
        print(f" • Prompt:     {self.prompt_file.name}")
        print("-" * 60)
        
        # Load prompt
        self.extraction_prompt = self._load_prompt()
        
        # Initialize Backend
        if self.provider == "gemini":
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.5-pro-preview-03-25')
            except Exception as e:
                print(f"Error initializing Gemini: {e}")
                sys.exit(1)
        else:
            print(f"Provider '{self.provider}' not yet implemented.")
            sys.exit(1)
        
        # Load checkpoint
        self.checkpoint = self._load_checkpoint()
        
        print("-" * 60)
        print(f"PDF EXTRACTION PIPELINE ({self.provider.upper()})")
        print("-" * 60)
        print(f"Input:    {self.input_dir}")
        print(f"Output:   {self.output_dir}")
        print(f"Prompt:   {self.prompt_file.name}")
        print("-" * 60)
    
    def _load_prompt(self) -> str:
        if not self.prompt_file.exists():
            print(f"Error: Prompt file not found: {self.prompt_file}")
            sys.exit(1)
        
        with open(self.prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
        
        if not prompt:
            print(f"Error: Prompt file is empty.")
            sys.exit(1)
        return prompt
    
    def _load_checkpoint(self) -> Dict:
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {'processed': [], 'failed': [], 'stats': {}}
    
    def _save_checkpoint(self):
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)
    
    def _is_processed(self, pdf_name: str) -> bool:
        return pdf_name in self.checkpoint['processed']
    
    def _mark_processed(self, pdf_name: str, num_records: int):
        if pdf_name not in self.checkpoint['processed']:
            self.checkpoint['processed'].append(pdf_name)
        
        self.checkpoint['stats'][pdf_name] = {
            'num_records': num_records,
            'processed_at': datetime.now().isoformat()
        }
        self._save_checkpoint()
    
    def _mark_failed(self, pdf_name: str, error: str):
        self.checkpoint['failed'].append({
            'pdf': pdf_name,
            'error': str(error),
            'failed_at': datetime.now().isoformat()
        })
        self._save_checkpoint()
    
    def _load_rename_log(self) -> dict:
        if self.renamed_log.exists():
            try:
                with open(self.renamed_log, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_rename_log(self, log: dict):
        try:
            with open(self.renamed_log, 'w', encoding='utf-8') as f:
                json.dump(log, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save rename log: {e}")
    
    def rename_input_pdfs(self) -> int:
        if not self.rename_pdfs:
            return 0
        
        if not HAS_PYMUPDF:
            print("PyMuPDF not installed - skipping PDF renaming")
            return 0
        
        pdf_files = list(self.input_dir.glob("*.pdf"))
        if not pdf_files:
            return 0
        
        print(f"\nStandardizing filenames for {len(pdf_files)} files...")
        
        rename_log = self._load_rename_log()
        renamed_count = 0
        
        for idx, pdf_path in enumerate(pdf_files, 1):
            original_name = pdf_path.name
            
            # Skip if already standardized (DOI format)
            if re.match(r"^10\.\d{4,9}", original_name):
                continue
                
            try:
                doi, title = extract_doi_and_title(pdf_path)
                
                if doi:
                    doi_clean = clean_filename(doi, max_len=50)
                    title_clean = clean_filename(title, max_len=100)
                    new_name = f"{doi_clean} - {title_clean}.pdf"
                else:
                    title_clean = clean_filename(title, max_len=150)
                    new_name = f"NO_DOI - {title_clean}.pdf"
                
                new_path = get_unique_path(self.input_dir / new_name)
                pdf_path.rename(new_path)
                
                rename_log[new_path.name] = {
                    "original_name": original_name,
                    "doi": doi,
                    "title": title,
                    "renamed_at": datetime.now().isoformat()
                }
                renamed_count += 1
                
            except Exception:
                pass
        
        if renamed_count > 0:
            self._save_rename_log(rename_log)
            print(f"Renamed {renamed_count} files.")
            
        return renamed_count
    
    def _process_with_gemini(self, pdf_path: Path) -> Optional[str]:
        """Internal handler for Gemini API"""
        # Upload
        print(f"  > Uploading...")
        uploaded_file = genai.upload_file(path=str(pdf_path))
        
        # Wait
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(1)
            uploaded_file = genai.get_file(uploaded_file.name)
        
        if uploaded_file.state.name == "FAILED":
            raise Exception("Gemini processing failed state")
            
        # Generate
        print(f"  > Extracting...")
        response = self.model.generate_content(
            [self.extraction_prompt, uploaded_file],
            request_options={"timeout": 300}
        )
        
        # Cleanup
        genai.delete_file(uploaded_file.name)
        
        return response.text

    def process_pdf(self, pdf_path: Path) -> Optional[List[Dict]]:
        print(f"Processing: {pdf_path.name}")
        
        if not pdf_path.exists():
            return None
        
        try:
            # Delegate to provider handler
            if self.provider == "gemini":
                response_text = self._process_with_gemini(pdf_path)
            else:
                raise NotImplementedError("Provider not supported")
            
            if not response_text:
                raise Exception("Empty response from API")

            # Save debug
            if self.debug_mode:
                debug_file = self.output_dir / f"DEBUG_{pdf_path.stem}.txt"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(response_text)
            
            # Extract JSON
            cleaned_text = response_text.strip()
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()
            
            materials = json.loads(cleaned_text)
            
            if not isinstance(materials, list):
                materials = [materials] if isinstance(materials, dict) else []
                if not materials:
                     raise ValueError("Output is not a valid JSON list")
            
            # Add metadata
            for item in materials:
                metadata = {
                    'source_pdf': pdf_path.name,
                    'extracted_at': datetime.now().isoformat(),
                    'provider': self.provider
                }
                # Prepend metadata
                item_with_meta = {**metadata, **item}
                item.clear()
                item.update(item_with_meta)
            
            return materials
        
        except Exception as e:
            print(f"  Failed: {e}")
            self._mark_failed(pdf_path.name, str(e))
            return None
    
    def run(self, max_papers: Optional[int] = None):
        """Run the pipeline"""
        if self.rename_pdfs:
            self.rename_input_pdfs()
        
        if not self.input_dir.exists():
            print(f"Input directory not found: {self.input_dir}")
            return
        
        all_pdfs = sorted(list(self.input_dir.glob("*.pdf")))
        to_process = [p for p in all_pdfs if not self._is_processed(p.name)]
        
        if not to_process:
            print("No new PDFs to process.")
            return
        
        print(f"Processing {len(to_process)} new files (Total: {len(all_pdfs)})")
        
        if max_papers:
            to_process = to_process[:max_papers]
            print(f"Limiting to first {max_papers} files.")
        
        all_data = []
        
        for pdf_path in to_process:
            data = self.process_pdf(pdf_path)
            if data:
                all_data.extend(data)
                
                # Save individual
                out_file = self.output_dir / f"{pdf_path.stem}.json"
                with open(out_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                # Mark done
                self._mark_processed(pdf_path.name, len(data))
                
                # Move original
                try:
                    pdf_path.rename(self.processed_dir / pdf_path.name)
                except Exception:
                    pass
            
            time.sleep(1) # Rate limit buffer
        
        # Save Combined
        if all_data:
            print("Saving combined results...")
            with open(self.output_dir / "combined_data.json", 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2)
            
            try:
                df = pd.DataFrame(all_data)
                df.to_excel(self.output_dir / "dataset.xlsx", index=False)
                print(f"Database saved to: {self.output_dir}/dataset.xlsx")
            except Exception as e:
                print(f"Excel export failed: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='PDF Data Extraction Pipeline')
    
    parser.add_argument('target_dir', nargs='?', default='.', help='Target folder containing PDFs')
    parser.add_argument('--api-key', type=str, help='API Key')
    parser.add_argument('--provider', type=str, default='gemini', help='LLM Provider (default: gemini)')
    parser.add_argument('--prompt', type=str, help='Custom prompt file')
    parser.add_argument('--max', type=int, help='Max files to process')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    parser.add_argument('--no-rename', action='store_true', help='Skip file renaming')
    
    args = parser.parse_args()
    
    target_dir = Path(args.target_dir).resolve()
    if not target_dir.exists():
        print(f"Error: Target directory '{target_dir}' does not exist.")
        return

    # Check Key
    api_key = args.api_key
    if not api_key:
         # Check environment variable
         if os.environ.get("GEMINI_API_KEY"):
             api_key = os.environ.get("GEMINI_API_KEY")
         else:
             # Check file in target dir or script dir
             key_file = target_dir / "api_key.txt"
             old_key_file = target_dir / "Gemini-api.txt"
             
             if not key_file.exists():
                 if old_key_file.exists():
                     key_file = old_key_file
                 else:
                     key_file = Path(__file__).parent / "api_key.txt"
             
             if key_file.exists():
                 with open(key_file) as f: api_key = f.read().strip()
    
    if not api_key:
        print("Error: API Key required. Set GEMINI_API_KEY env var or create api_key.txt")
        return

    pipeline = PDFDataExtractionPipeline(
        target_dir=str(target_dir),
        api_key=api_key,
        provider=args.provider,
        prompt_file=args.prompt,
        rename_pdfs=not args.no_rename,
        debug_mode=args.debug
    )
    
    pipeline.run(max_papers=args.max)

if __name__ == "__main__":
    main()
