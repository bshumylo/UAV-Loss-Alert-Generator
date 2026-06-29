#!/usr/bin/env python3
"""
Fix mojibake encoding in database.js and database.json.

The Ukrainian city names were encoded as cp1251 bytes but the files were saved/read
as if they were Latin-1 (ISO-8859-1), creating mojibake.

Fix: re-encode each garbled string back to latin-1 bytes, then decode as cp1251.
"""

import re
import os
import shutil

BASE = r"c:\Users\useR\Мий диск\1 Projects\Подання БПЛА"

def fix_mojibake_string(s: str) -> str:
    """Try to fix a single string value that might be mojibake."""
    try:
        recovered = s.encode('latin-1').decode('cp1251')
        return recovered
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s  # leave unchanged

def fix_file(input_path: str, output_path: str):
    print(f"Reading: {input_path}")
    
    # Read as latin-1 to preserve the raw bytes exactly
    with open(input_path, 'r', encoding='latin-1') as f:
        content = f.read()

    print(f"  Total chars: {len(content)}")

    # Replace quoted string values
    # This regex matches "..." allowing escaped characters inside
    count = 0
    def replacer(m):
        nonlocal count
        s = m.group(1)
        fixed = fix_mojibake_string(s)
        if fixed != s:
            count += 1
        return '"' + fixed + '"'

    fixed_content = re.sub(r'"((?:[^"\\]|\\.)*)"', replacer, content)
    print(f"  Fixed {count} strings")

    # Write as UTF-8
    with open(output_path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(fixed_content)
    print(f"Saved: {output_path}")

def main():
    files = ['database.js', 'database.json']
    base = r"c:\Users\useR\Мій диск\1 Projects\Подання БПЛА"
    
    for fname in files:
        fpath = os.path.join(base, fname)
        if not os.path.exists(fpath):
            print(f"File not found: {fpath}")
            continue
        
        # Create backup
        backup = fpath + '.bak'
        if not os.path.exists(backup):
            shutil.copy2(fpath, backup)
            print(f"Backup: {backup}")
        
        fix_file(fpath, fpath)
    
    print("\nAll done!")

if __name__ == '__main__':
    main()
