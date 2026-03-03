#!/usr/bin/env python3
"""
Rename PDF files based on extracted company name and invoice date.
Usage: python rename_pdfs.py [--dry-run]
"""

import os
import json
import re
import sys
from pdfminer.high_level import extract_text
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
PDF_FOLDER = os.getenv("PDF_FOLDER")
INDEX_FILE = os.path.join(os.path.dirname(__file__), "index.json")

import unicodedata

def sanitize_filename(name):
    """Return a safe filename by stripping control characters, reserved symbols, and normalizing.

    This aggressively removes characters that can break `os.rename`, such as embedded
    nulls (\x00) or other non-printable/control codes. It also takes care of the usual
    Windows/Unix reserved characters and limits length for safety.
    """
    # normalize unicode to composed form to avoid weird combining sequences
    name = unicodedata.normalize('NFKC', name)
    # strip control characters (0x00-0x1f, 0x7f) and other non-printable codes
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    # remove characters that are invalid in filenames on most platforms
    name = re.sub(r'[<>:\"/\\|?*]', '', name)
    # collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    # fallback if empty after cleaning
    if not name:
        name = "unnamed"
    # truncate to a reasonable length
    return name[:100]

def extract_company(text, filename=""):
    """Extract company/vendor name from text with multiple strategies."""
    lines = text.split('\n')
    
    # Strategy 1: Look for explicit company keywords
    company_keywords = [
        'from:', 'vendor:', 'billed by:', 'company:', 'invoice from:',
        'supplier:', 'trader:', 'trading as:', 'abn:', 'acn:', 'company name:'
    ]
    
    for line in lines[:50]:
        line_lower = line.lower()
        for keyword in company_keywords:
            if keyword in line_lower:
                parts = line.split(':')
                if len(parts) > 1:
                    company = parts[-1].strip()
                    if company and len(company) > 2 and len(company) < 100:
                        # Remove trailing reference numbers or extra info
                        company = re.sub(r'\s+abn.*$', '', company, flags=re.IGNORECASE)
                        company = re.sub(r'\s+acn.*$', '', company, flags=re.IGNORECASE)
                        return company[:80]
    
    # Strategy 2: Look for business address patterns
    for i, line in enumerate(lines[:40]):
        line = line.strip()
        # Check if next line looks like an address (has numbers, street keywords)
        if i + 1 < len(lines):
            next_line = lines[i + 1].lower()
            address_keywords = ['street', 'road', 'lane', 'avenue', 'drive', 'crescent', 
                              'close', 'way', 'court', 'terrace', 'place', 'rd', 'ave', 
                              'st.', 'p.o. box', 'po box']
            if any(keyword in next_line for keyword in address_keywords):
                if line and len(line) > 3 and len(line) < 80:
                    if not any(c.isdigit() for c in line[:5]):  # Doesn't start with numbers
                        if re.search(r'[A-Z]{2,}', line):  # Has capitals
                            return line
    
    # Strategy 3: Look for capitalized lines at the start (often company name)
    for line in lines[:30]:
        line = line.strip()
        if line and 4 < len(line) < 80:
            # Check if it has multiple capital letters and basic structure
            caps = sum(1 for c in line if c.isupper())
            if caps > 2 and not any(c.isdigit() for c in line[:10]):
                return line
    
    # Strategy 4: Try to extract from filename if it has meaningful text
    filename_clean = filename.replace('.pdf', '').replace('-', ' ').replace('_', ' ')
    if 'invoice' not in filename_clean.lower() and 'receipt' not in filename_clean.lower():
        words = filename_clean.split()
        if words and len(words) > 0:
            potential = ' '.join(words[:3])
            if len(potential) > 3 and len(potential) < 80:
                return potential
    
    return None

def extract_date(text, filename=""):
    """Extract invoice date with multiple strategies."""
    keywords = ['date:', 'date ', 'dated ', 'invoice date:', 'date of invoice:', 'issue date:']
    lines = text.split('\n')
    
    # Strategy 1: Look near common keywords
    for line in lines[:50]:
        line_lower = line.lower()
        for keyword in keywords:
            if keyword in line_lower:
                dates = re.findall(
                    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})',
                    line
                )
                if dates:
                    return normalize_date(dates[0])
    
    # Strategy 2: Search entire document for dates, prefer later ones (to avoid registration dates)
    all_dates = re.findall(
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        text[:3000]
    )
    if all_dates:
        # Return the last substantial date found (not the first)
        return normalize_date(all_dates[-2] if len(all_dates) > 1 else all_dates[0])
    
    # Strategy 3: Try to extract from filename
    dates_in_filename = re.findall(
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        filename
    )
    if dates_in_filename:
        return normalize_date(dates_in_filename[-1])
    
    # Strategy 4: Look for year-month patterns
    year_month = re.search(r'(20\d{2})[/-](0?[1-9]|1[0-2])', text[:2000])
    if year_month:
        year, month = year_month.groups()
        return f"{year}-{month.zfill(2)}-01"
    
    return None

def normalize_date(date_str):
    """Normalize date to YYYY-MM-DD format."""
    # Try different patterns
    # DD/MM/YYYY or DD-MM-YYYY
    match = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # YYYY/MM/DD or YYYY-MM-DD
    match = re.match(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    return date_str

def rename_pdfs(dry_run=False):
    """Rename all PDFs based on company and date."""
    if not PDF_FOLDER or not os.path.isdir(PDF_FOLDER):
        print(f"❌ PDF_FOLDER not configured or does not exist: {PDF_FOLDER}")
        return False
    
    renamed_count = 0
    failed_count = 0
    skipped_count = 0
    
    print(f"📁 Scanning {PDF_FOLDER}...")
    print()
    
    for root, dirs, files in os.walk(PDF_FOLDER):
        for filename in files:
            if not filename.lower().endswith('.pdf'):
                continue
            
            full_path = os.path.join(root, filename)
            relative_dir = os.path.relpath(root, PDF_FOLDER)
            
            try:
                # Extract text from PDF
                print(f"📄 {filename[:50]:<50} ", end="", flush=True)
                text = extract_text(full_path)
                
                # Extract metadata
                company = extract_company(text, filename)
                date = extract_date(text, filename)
                
                # Need at least company or date to rename
                if not company and not date:
                    print(f"⚠️  skip (no data)")
                    skipped_count += 1
                    continue
                
                # Build reasonable filename
                if company and date:
                    new_filename = f"{company}_{date}.pdf"
                elif company:
                    new_filename = f"{company}.pdf"
                elif date:
                    new_filename = f"Invoice_{date}.pdf"
                else:
                    print(f"⚠️  skip")
                    skipped_count += 1
                    continue
                
                new_filename = sanitize_filename(new_filename)
                new_path = os.path.join(root, new_filename)
                
                # Check if already correctly named
                if new_path == full_path:
                    print(f"✓ already named")
                    continue
                
                # Handle duplicates
                if os.path.exists(new_path):
                    # Try with company initial or counter
                    base_name = new_filename.replace('.pdf', '')
                    counter = 1
                    while os.path.exists(os.path.join(root, f"{base_name}_{counter}.pdf")):
                        counter += 1
                    new_filename = f"{base_name}_{counter}.pdf"
                    new_path = os.path.join(root, new_filename)
                
                if dry_run:
                    print(f"→ {new_filename[:40]}")
                    renamed_count += 1
                else:
                    try:
                        os.rename(full_path, new_path)
                        print(f"✓ {new_filename[:40]}")
                        renamed_count += 1
                    except Exception as e:
                        print(f"❌ {str(e)[:30]}")
                        failed_count += 1
                        
            except Exception as e:
                print(f"❌ error: {str(e)[:30]}")
                failed_count += 1
    
    print()
    if dry_run:
        print(f"📊 Dry run results:")
        print(f"   {renamed_count} files would be renamed")
        print(f"   {skipped_count} files skipped (no extractable data)")
        print(f"   {failed_count} files failed")
    else:
        print(f"✅ Results:")
        print(f"   {renamed_count} files renamed")
        print(f"   {skipped_count} files skipped")
        print(f"   {failed_count} files failed")
    
    return renamed_count > 0

def regenerate_index():
    """Regenerate the index after renaming."""
    print("\n🔄 Regenerating index...")
    from backend.indexer import scan_pdfs, save_index
    
    documents = scan_pdfs(PDF_FOLDER)
    save_index(documents)
    print(f"✅ Index regenerated with {len(documents)} documents")

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be renamed\n")
    else:
        print("⚠️  WARNING: This will rename files in your PDF folder\n")
        confirm = input("Continue? (yes/no): ").lower().strip()
        if confirm not in ['yes', 'y']:
            print("❌ Cancelled")
            sys.exit(1)
        print()
    
    success = rename_pdfs(dry_run=dry_run)
    
    if not dry_run and success:
        confirm_index = input("\nRegenerate index now? (yes/no): ").lower().strip()
        if confirm_index in ['yes', 'y']:
            regenerate_index()
