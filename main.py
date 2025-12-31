import sys
import os
import re
import pdfplumber
import pandas as pd


# Bank configurations with column coordinate ranges (X-axis)
# Use find_coordinates.py to get the exact ranges for your PDF
# python find_coordinates.py <pdf_path> <page_number>
BANK_CONFIGS = {
    "BBVA": {
        "name": "BBVA",
        "columns": {
            "fecha": (0, 80),              # Columna Fecha de Operación
            "liq": (80, 160),              # Columna LIQ (Liquidación)
            "descripcion": (160, 400),     # Columna Descripción
            "cargos": (362, 398),          # Columna Cargos
            "abonos": (422, 458),          # Columna Abonos
            "saldo": (539, 593),           # Columna Saldo
        }
    },
    
    "Santander": {
        "name": "Santander",
        "columns": {
            "fecha": (18, 52),             # Columna Fecha de Operación
            "descripcion": (107, 149),     # Columna Descripción
            "cargos": (465, 492),          # Columna Cargos
            "abonos": (377, 411),          # Columna Abonos
            "saldo": (554, 573),           # Columna Saldo
        }
    },

    "Scotiabank": {
        "name": "Scotiabank",
        "columns": {
            "fecha": (56, 79),             # Columna Fecha de Operación
            "descripcion": (152, 189),     # Columna Descripción
            "cargos": (465, 488),          # Columna Cargos
            "abonos": (392, 426),          # Columna Abonos
            "saldo": (539, 561),           # Columna Saldo
        }
    },

    "Inbursa": {
        "name": "Inbursa",
        "columns": {
            "fecha": (16, 42),             # Columna Fecha de Operación
            "descripcion": (241, 283),     # Columna Descripción
            "cargos": (395, 427),          # Columna Cargos
            "abonos": (462, 494),          # Columna Abonos
            "saldo": (526, 552),           # Columna Saldo
        }
    },

    "Konfio": {
        "name": "Konfio",
        "columns": {
            "fecha": (59, 89),             # Columna Fecha de Operación
            "descripcion": (170, 228),     # Columna Descripción
            "cargos": (354, 375),          # Columna Cargos
            "abonos": (527, 548),          # Columna Abonos
        }
    },

    "Banregio": {
        "name": "Banregio",
        "columns": {
            "fecha": (35, 45),             # Columna Fecha de Operación
            "descripcion": (50, 300),     # Columna Descripción
            "cargos": (350, 399),          # Columna Cargos
            "abonos": (440, 475),          # Columna Abonos
            "saldo": (520, 573),           # Columna Saldo
        }
    },
    
     "Banorte": {
        "name": "Banorte",
        "columns": {
            "fecha": (54, 85),             # Columna Fecha de Operación
            "descripcion": (87, 300),     # Columna Descripción
            "cargos": (431, 489),          # Columna Cargos
            "abonos": (353, 420),          # Columna Abonos
            "saldo": (533, 553),           # Columna Saldo
        }
    },

     "Banbajío": {
        "name": "Banbajío",
        "columns": {
            "fecha": (19, 43),             # Columna Fecha de Operación
            "descripcion": (135, 300),     # Columna Descripción
            "cargos": (474, 525),          # Columna Cargos
            "abonos": (395, 451),          # Columna Abonos
            "saldo": (530, 585),           # Columna Saldo
        }
    },
    
    "Banamex": {
        "name": "Banamex",
        "columns": {
            "fecha": (17, 45),             # Columna Fecha de Operación
            "descripcion": (55, 260),      # Columna Descripción (ampliado para capturar mejor)
            "cargos": (275, 316),          # Columna Cargos (ampliado ligeramente)
            "abonos": (345, 395),          # Columna Abonos (ampliado ligeramente)
            "saldo": (425, 472),           # Columna Saldo (ampliado ligeramente)
        }
    },
        # Add more banks here as needed
}

DEFAULT_BANK = "BBVA"

# Bank detection keywords (case insensitive)
# Order matters: more specific patterns should come first
BANK_KEYWORDS = {
    
    "BBVA": [
        r"\bBBVA\b",
        r"\bBBVA\s+BANCOMER\b",
        r"ESTADO\s+DE\s+CUENTA\s+MAESTRA\s+PYME\s+BBVA",
        r"BBVA\s+ADELANTE",
    ],
    "Banamex": [
        r"\bDIGITEM\b",  # Palabra muy específica de Banamex
        r"\bBANAMEX\b",
        r"\bCITIBANAMEX\b",
        r"\bCITI\s+BANAMEX\b",
    ],
    "Banbajío": [
        r"\bBANBAJ[IÍ]O\b",
        r"\bBANCO\s+DEL\s+BAJ[IÍ]O\b",
    ],
    "Banorte": [
        r"\bBANORTE\b",
        r"\bBANCO\s+MACRO\s+BANORTE\b",
    ],
    "Banregio": [
        r"\bBANREGIO\b",
        r"\bBANCO\s+REGIONAL\b",
    ],
    "Clara": [
        r"\bCLARA\b",
        r"\bBANCO\s+CLARA\b",
    ],
    "Konfio": [
        r"\bKONFIO\b",
        r"\bBANCO\s+KONFIO\b",
    ],
    "Inbursa": [
        r"\bINBURSA\b",
        r"\bBANCO\s+INBURSA\b",
    ],
    "Santander": [
        r"\bSANTANDER\b",
        r"\bBANCO\s+SANTANDER\b",
        r"\bSANTANDER\s+MEXICANO\b",
    ],
    "Scotiabank": [
        r"\bSCOTIABANK\b",
        r"\bSCOTIA\s+BANK\b",
        r"\bBANCO\s+SCOTIABANK\b",
    ],
    "Hey": [
        r"\bHEY\s+BANCO\b",
        r"\bHEY\b",
    ],
}

# Decimal / thousands amount regex (module-level so helpers can use it)
DEC_AMOUNT_RE = re.compile(r"\d{1,3}(?:[\.,\s]\d{3})*(?:[\.,]\d{2})")


def find_column_coordinates(pdf_path: str, page_number: int = 1):
    """Extract all words from a page and show their coordinates.
    Helps user find exact X ranges for columns.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_number > len(pdf.pages):
                print(f"❌ El PDF solo tiene {len(pdf.pages)} páginas")
                return
            
            page = pdf.pages[page_number - 1]
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            
            if not words:
                print("❌ No se encontraron palabras en la página")
                return
            
            # Group by approximate Y coordinate (rows)
            rows = {}
            for word in words:
                top = int(round(word['top']))
                if top not in rows:
                    rows[top] = []
                rows[top].append(word)
            
            print(f"\n📄 Página {page_number} del PDF: {pdf_path}")
            print("=" * 120)
            print(f"{'Y (top)':<8} {'X0':<8} {'X1':<8} {'X_center':<10} {'Texto':<40}")
            print("-" * 120)
            
            # Print words sorted by Y then X
            for top in sorted(rows.keys()):
                row_words = sorted(rows[top], key=lambda w: w['x0'])
                for i, word in enumerate(row_words):
                    x_center = (word['x0'] + word['x1']) / 2
                    print(f"{top:<8} {word['x0']:<8.1f} {word['x1']:<8.1f} {x_center:<10.1f} {word['text']:<40}")
            
            print("\n" + "=" * 120)
            print("\nRangos aproximados de columnas (X0 a X1):")
            print("-" * 120)
            
            # Find column boundaries
            all_x0 = [w['x0'] for word_list in rows.values() for w in word_list]
            all_x1 = [w['x1'] for word_list in rows.values() for w in word_list]
            
            min_x = min(all_x0)
            max_x = max(all_x1)
            
            print(f"Rango X total: {min_x:.1f} a {max_x:.1f}")
            print("\nAnaliza la salida anterior y proporciona estos valores en BANK_CONFIGS:")
            print("""
Ejemplo:
BANK_CONFIGS = {
    "BBVA": {
        "name": "BBVA",
        "columns": {
            "fecha": (x_min, x_max),           # Columna Fecha de Operación
            "liq": (x_min, x_max),              # Columna LIQ (Liquidación)
            "descripcion": (x_min, x_max),     # Columna Descripción
            "cargos": (x_min, x_max),          # Columna Cargos
            "abonos": (x_min, x_max),          # Columna Abonos
            "saldo": (x_min, x_max),           # Columna Saldo
        }
    },
}
            """)
    
    except Exception as e:
        print(f"❌ Error: {e}")


def detect_bank_from_pdf(pdf_path: str) -> str:
    """
    Detect the bank from PDF content by reading line by line.
    Returns the bank name if detected, otherwise returns DEFAULT_BANK.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Read first few pages (usually bank name appears early)
            max_pages_to_check = min(3, len(pdf.pages))
            
            for page_num in range(max_pages_to_check):
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                if not text:
                    continue
                
                # Split into lines and check each line
                lines = text.split('\n')
                for line in lines:
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    
                    # Check each bank's keywords
                    for bank_name, keywords in BANK_KEYWORDS.items():
                        for keyword_pattern in keywords:
                            if re.search(keyword_pattern, line_clean, re.I):
                                print(f"🏦 Banco detectado: {bank_name} (encontrado en línea: {line_clean[:50]}...)")
                                return bank_name
                    
                    # Also check if line contains bank name directly (case insensitive)
                    line_upper = line_clean.upper()
                    for bank_name in BANK_KEYWORDS.keys():
                        # Check for exact bank name match (as whole word)
                        if re.search(rf'\b{re.escape(bank_name.upper())}\b', line_upper):
                            print(f"🏦 Banco detectado: {bank_name} (encontrado en línea: {line_clean[:50]}...)")
                            return bank_name
    
    except Exception as e:
        print(f"⚠️  Error al detectar banco: {e}")
    
    # If no bank detected, return default
    print(f"⚠️  No se pudo detectar el banco, usando: {DEFAULT_BANK}")
    return DEFAULT_BANK


def extract_text_from_pdf(pdf_path: str) -> list:
    """
    Extract text and word positions from each page of a PDF.
    Returns a list of dictionaries (page_number, text, words).
    """
    extracted_data = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            # also extract words with positions for coordinate-based column detection
            try:
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
            except Exception:
                words = []
            extracted_data.append({
                "page": page_number,
                "content": text if text else "",
                "words": words
            })

    return extracted_data


def export_to_excel(data: list, output_path: str):
    """
    Export extracted PDF content to an Excel file.
    """
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False)
    print(f"✅ Excel file created: {output_path}")


def split_pages_into_lines(pages: list) -> list:
    """Return list of page dicts with lines: [{'page': n, 'lines': [...]}, ...]"""
    pages_lines = []
    for p in pages:
        content = (p.get('content') or '')
        # normalize NBSPs
        content = content.replace('\u00A0', ' ').replace('\u202F', ' ')
        lines = [" ".join(l.split()) for l in content.splitlines() if l and l.strip()]
        pages_lines.append({'page': p.get('page'), 'lines': lines})
    return pages_lines


def group_entries_from_lines(lines):
    """Group lines into transaction entries: a line starting with a date begins a new entry."""
    day_re = re.compile(r"\b(?:0[1-9]|[12][0-9]|3[01])(?:[\/\-\s])[A-Za-z]{3}\b")
    entries = []
    for line in lines:
        if day_re.search(line):
            entries.append(line)
        else:
            if entries:
                entries[-1] = entries[-1] + ' ' + line
            else:
                entries.append(line)
    return entries


def group_words_by_row(words, y_tolerance=5):
    """Group words by Y-coordinate (rows) to extract table rows."""
    if not words:
        return []
    
    # Sort by top coordinate
    sorted_words = sorted(words, key=lambda w: w.get('top', 0))
    
    rows = []
    current_row = []
    current_y = None
    
    for word in sorted_words:
        word_y = word.get('top', 0)
        if current_y is None:
            current_y = word_y
        
        # If word is within y_tolerance of current row, add it
        if abs(word_y - current_y) <= y_tolerance:
            current_row.append(word)
        else:
            # Start a new row
            if current_row:
                rows.append(current_row)
            current_row = [word]
            current_y = word_y
    
    # Don't forget the last row
    if current_row:
        rows.append(current_row)
    
    return rows


def assign_word_to_column(word_x0, word_x1, columns):
    """Assign a word (with x0, x1 coordinates) to a column based on X-ranges.
    Returns column name or None if not in any range.
    """
    word_center = (word_x0 + word_x1) / 2
    for col_name, (x_min, x_max) in columns.items():
        if x_min <= word_center <= x_max:
            return col_name
    return None


def is_transaction_row(row_data):
    """Check if a row is an actual bank transaction (not a header or empty row).
    A transaction must have:
    - A date in 'fecha' column
    - At least one amount in cargos, abonos, or saldo
    """
    fecha = (row_data.get('fecha') or '').strip()
    cargos = (row_data.get('cargos') or '').strip()
    abonos = (row_data.get('abonos') or '').strip()
    saldo = (row_data.get('saldo') or '').strip()
    
    # Must have a date matching DD/MMM pattern
    day_re = re.compile(r"\b(?:0[1-9]|[12][0-9]|3[01])(?:[\/\-\s])[A-Za-z]{3}\b")
    has_date = bool(day_re.search(fecha))
    
    # Must have at least one numeric amount
    has_amount = bool(cargos or abonos or saldo)
    
    return has_date and has_amount


def extract_movement_row(words, columns):
    """Extract a structured movement row from grouped words using coordinate-based column assignment."""
    row_data = {col: '' for col in columns.keys()}
    amounts = []
    
    # Sort words by X coordinate within the row
    sorted_words = sorted(words, key=lambda w: w.get('x0', 0))
    
    for word in sorted_words:
        text = word.get('text', '')
        x0 = word.get('x0', 0)
        x1 = word.get('x1', 0)
        center = (x0 + x1) / 2

        # detect amount tokens inside the word
        m = DEC_AMOUNT_RE.search(text)
        if m:
            amounts.append((m.group(), center))

        col_name = assign_word_to_column(x0, x1, columns)
        if col_name:
            if row_data[col_name]:
                row_data[col_name] += ' ' + text
            else:
                row_data[col_name] = text

    # attach detected amounts for later disambiguation
    row_data['_amounts'] = amounts
    return row_data


def main():
    # Validate input
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main2.py <input.pdf>              # Parse PDF and create Excel")
        print("  python main2.py <input.pdf> --find <page> # Find column coordinates on page N")
        print("\nExample:")
        print("  python main2.py BBVA.pdf")
        print("  python main2.py BBVA.pdf --find 2")
        sys.exit(1)

    pdf_path = sys.argv[1]
    
    # Check for --find mode
    if len(sys.argv) >= 3 and sys.argv[2] == '--find':
        page_num = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        print(f"🔍 Buscando coordenadas en página {page_num}...")
        find_column_coordinates(pdf_path, page_num)
        return

    if not os.path.isfile(pdf_path):
        print("❌ File not found.")
        sys.exit(1)

    if not pdf_path.lower().endswith(".pdf"):
        print("❌ Only PDF files are supported.")
        sys.exit(1)

    output_excel = os.path.splitext(pdf_path)[0] + ".xlsx"

    print("📄 Reading PDF...")
    
    # Detect bank from PDF content (read PDF directly for detection)
    detected_bank = detect_bank_from_pdf(pdf_path)
    
    # Now extract full data
    extracted_data = extract_text_from_pdf(pdf_path)
    # split pages into lines
    pages_lines = split_pages_into_lines(extracted_data)

    # Get bank config based on detected bank
    bank_config = BANK_CONFIGS.get(detected_bank)
    if not bank_config:
        print(f"⚠️  Bank config not found for {detected_bank}, using generic fallback")
        # Create a generic config for non-BBVA banks
        # They will use raw text extraction instead of coordinate-based
        bank_config = {
            "name": detected_bank,
            "columns": {}  # Empty columns means will use raw extraction
        }
    else:
        # Ensure the name matches the detected bank
        bank_config = bank_config.copy()
        bank_config["name"] = detected_bank
    
    columns_config = bank_config.get("columns", {})

    # find where movements start (first line anywhere that matches a date or contains header keywords)
    day_re = re.compile(r"\b(?:0[1-9]|[12][0-9]|3[01])(?:[\/\-\s])[A-Za-z]{3}\b")
    # match lines that contain both 'fecha' AND 'descripcion', OR lines that contain 'concepto'
    # Implemented with lookahead for the AND case, and an alternation for 'concepto'
    header_keywords_re = re.compile(r"(?:(?=.*\bfecha\b)(?=.*\bdescripcion\b))|(?:\bconcepto\b)", re.I)
    # ensure a reusable date pattern is available for later checks
    date_pattern = day_re
    movement_start_found = False
    movement_start_page = None
    movement_start_index = None
    movements_lines = []
    for p in pages_lines:
        if not movement_start_found:
            for i, ln in enumerate(p['lines']):
                if day_re.search(ln) or header_keywords_re.search(ln):
                    movement_start_found = True
                    movement_start_page = p['page']
                    movement_start_index = i
                    # collect from this line onward in this page
                    movements_lines.extend(p['lines'][i:])
                    break
        else:
            movements_lines.extend(p['lines'])

    # build summary from first page (lines before movements start if movements begin on page 1)
    if pages_lines:
        first_page = pages_lines[0]
        if movement_start_found and movement_start_page == first_page['page'] and movement_start_index is not None:
            summary_lines = first_page['lines'][:movement_start_index]
        else:
            summary_lines = first_page['lines']
    else:
        summary_lines = []

    # Extract movements using coordinate-based column detection
    movement_rows = []
    # regex to detect decimal-like amounts (used to strip amounts from descriptions and detect amounts)
    dec_amount_re = re.compile(r"\d{1,3}(?:[\.,\s]\d{3})*(?:[\.,]\d{2})")
    for page_data in extracted_data:
        page_num = page_data['page']
        words = page_data.get('words', [])
        
        if not words:
            continue
        
        # Check if this page contains movements (page >= movement_start_page if found)
        if movement_start_found and page_num < movement_start_page:
            continue
        
        # Group words by row
        word_rows = group_words_by_row(words)
        
        for row_words in word_rows:
            if not row_words:
                continue

            # Extract structured row using coordinates
            row_data = extract_movement_row(row_words, columns_config)

            # Determine if this row starts a new movement (contains a date)
            # If columns_config is empty, check all words for dates
            if not columns_config:
                # Check all words in the row for dates
                all_text = ' '.join([w.get('text', '') for w in row_words])
                has_date = bool(date_pattern.search(all_text))
                if has_date:
                    # Create a basic row_data structure
                    row_data = {'raw': all_text, '_amounts': row_data.get('_amounts', [])}
            else:
                # A new movement begins when the 'fecha' column contains a date token.
                fecha_val = str(row_data.get('fecha') or '')
                has_date = bool(date_pattern.search(fecha_val))

            if has_date:
                row_data['page'] = page_num
                movement_rows.append(row_data)
            else:
                # Continuation row: append description-like text and amounts to previous movement if exists
                if movement_rows:
                    prev = movement_rows[-1]
                    
                    # First, capture amounts from continuation row and assign to appropriate columns
                    cont_amounts = row_data.get('_amounts', [])
                    if cont_amounts and columns_config:
                        # Get description range to exclude amounts from it
                        descripcion_range = None
                        if 'descripcion' in columns_config:
                            x0, x1 = columns_config['descripcion']
                            descripcion_range = (x0, x1)
                        
                        # Get column ranges for numeric columns
                        col_ranges = {}
                        for col in ('cargos', 'abonos', 'saldo'):
                            if col in columns_config:
                                x0, x1 = columns_config[col]
                                col_ranges[col] = (x0, x1)
                        
                        # Assign amounts from continuation row
                        tolerance = 10
                        for amt_text, center in cont_amounts:
                            # Skip if amount is within description range
                            if descripcion_range and descripcion_range[0] <= center <= descripcion_range[1]:
                                continue
                            
                            # Find which numeric column this amount belongs to
                            assigned = False
                            for col in ('cargos', 'abonos', 'saldo'):
                                if col in col_ranges:
                                    x0, x1 = col_ranges[col]
                                    if (x0 - tolerance) <= center <= (x1 + tolerance):
                                        # Only assign if the column is empty or if this is a better match
                                        existing = prev.get(col) or ''
                                        if not existing or amt_text not in existing:
                                            if existing:
                                                prev[col] = (existing + ' ' + amt_text).strip()
                                            else:
                                                prev[col] = amt_text
                                        assigned = True
                                        break
                            
                            # If not assigned by range, use proximity as fallback
                            if not assigned and col_ranges:
                                valid_cols = {}
                                for col in col_ranges.keys():
                                    x0, x1 = col_ranges[col]
                                    if center >= (x0 - 20) and center <= (x1 + 20):
                                        col_center = (x0 + x1) / 2
                                        valid_cols[col] = abs(center - col_center)
                                
                                if valid_cols:
                                    nearest = min(valid_cols.keys(), key=lambda c: valid_cols[c])
                                    if not descripcion_range or not (descripcion_range[0] <= center <= descripcion_range[1]):
                                        existing = prev.get(nearest) or ''
                                        if not existing or amt_text not in existing:
                                            if existing:
                                                prev[nearest] = (existing + ' ' + amt_text).strip()
                                            else:
                                                prev[nearest] = amt_text
                    
                    # Also merge amounts list for later processing
                    prev_amounts = prev.get('_amounts', [])
                    prev['_amounts'] = prev_amounts + cont_amounts
                    
                    # Collect possible text pieces from this row (prefer descripcion, then liq, then any other text)
                    cont_parts = []
                    for k in ('descripcion', 'fecha'):
                        v = row_data.get(k)
                        if v:
                            cont_parts.append(str(v))
                    # Also capture any stray text in other columns
                    for k, v in row_data.items():
                        if k in ('descripcion', 'fecha', 'cargos', 'abonos', 'saldo', 'page', '_amounts'):
                            continue
                        if v:
                            cont_parts.append(str(v))

                    cont_text = ' '.join(cont_parts)
                    # Remove decimal amounts (they belong to cargos/abonos/saldo)
                    cont_text = dec_amount_re.sub('', cont_text)
                    cont_text = ' '.join(cont_text.split()).strip()

                    if cont_text:
                        # append to previous 'descripcion' field
                        if prev.get('descripcion'):
                            prev['descripcion'] = (prev.get('descripcion') or '') + ' ' + cont_text
                        else:
                            prev['descripcion'] = cont_text
                else:
                    # No previous movement to attach to; ignore or treat as header
                    continue

    # Process summary lines to format them properly
    def format_summary_line(line):
        """Format a summary line and return list of (titulo, dato) tuples.
        Intelligently separates title:value pairs based on data type changes.
        """
        line = line.strip()
        if not line:
            return []
        
        results = []
        
        # Pattern for "Periodo DEL [date] AL [date]" (case insensitive)
        periodo_pattern = re.compile(r'periodo\s+del\s+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\s+al\s+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', re.I)
        match = periodo_pattern.search(line)
        if match:
            fecha_inicio = match.group(1)
            fecha_fin = match.group(2)
            results.append(('Periodo DEL:', fecha_inicio))
            results.append(('AL:', fecha_fin))
            return results
        
        # Pattern for "No. de Cuenta [number]" or "No. de Cliente [number]" (case insensitive)
        cuenta_pattern = re.compile(r'(no\.?\s*de\s+(?:cuenta|cliente))\s+(.+)', re.I)
        match = cuenta_pattern.search(line)
        if match:
            titulo = match.group(1).strip()
            # Capitalize properly: "No. de Cuenta" or "No. de Cliente"
            if 'cuenta' in titulo.lower():
                titulo = 'No. de Cuenta'
            elif 'cliente' in titulo.lower():
                titulo = 'No. de Cliente'
            dato = match.group(2).strip()
            results.append((titulo + ':', dato))
            return results
        
        # Pattern for lines with "/" that separate multiple concepts (e.g., "Retiros / Cargos (-) 73 1,120,719.64")
        # Look for pattern: "Title1 / Title2 (optional) number1 number2"
        # More flexible: allows for optional parentheses and various number formats
        slash_pattern = re.compile(r'^([A-Za-z][A-Za-z\s]+?)\s*/\s*([A-Za-z][A-Za-z\s]*(?:\([^)]+\))?)\s+(\d+(?:,\d{3})*(?:\.\d{2})?)\s+([\d,\.\s]+)$', re.I)
        match = slash_pattern.search(line)
        if match:
            title1 = match.group(1).strip()
            title2 = match.group(2).strip()
            value1 = match.group(3).strip()
            value2 = match.group(4).strip()
            results.append((title1 + ':', value1))
            results.append((title2 + ':', value2))
            return results
        
        # Check if line is likely a company name/address (all caps, or contains common business terms)
        # Don't split these
        is_company_name = (
            line.isupper() or 
            re.search(r'\b(SA DE CV|S\.A\.|S\.A\. DE C\.V\.|S\.R\.L\.|INC\.|CORP\.|LLC)\b', line, re.I) or
            (len(line.split()) > 3 and not re.search(r'\d', line))  # Long text without numbers
        )
        if is_company_name:
            results.append((line, ''))
            return results
        
        # Pattern for lines that already have a colon
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                titulo = parts[0].strip()
                dato = parts[1].strip()
                results.append((titulo + ':', dato))
                return results
        
        # Intelligent splitting: detect data type changes
        # Split when we transition from text to number, or number to text
        tokens = line.split()
        if len(tokens) < 2:
            results.append((line, ''))
            return results
        
        # Find split points based on data type changes
        split_points = []
        for i in range(len(tokens) - 1):
            current = tokens[i]
            next_token = tokens[i + 1]
            
            # Check if current is text and next is number (or vice versa)
            # Better number detection: allows for formatted numbers with commas and decimals
            # Pattern: digits with optional thousands separators (commas) and optional decimal part
            num_pattern = re.compile(r'^\d{1,3}(?:,\d{3})*(?:\.\d{2})?$|^\d+(?:\.\d{2})?$')
            current_is_num = bool(num_pattern.match(current))
            next_is_num = bool(num_pattern.match(next_token))
            
            # Also check for date patterns
            current_is_date = bool(re.match(r'^\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}$', current))
            next_is_date = bool(re.match(r'^\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}$', next_token))
            
            # Split if: text->number, number->text, or text->date
            if (not current_is_num and not current_is_date and (next_is_num or next_is_date)):
                split_points.append(i + 1)
            elif (current_is_num or current_is_date) and not next_is_num and not next_is_date:
                # Number/date followed by text - might be a new field
                # But be careful, don't split if it's part of a longer description
                if i < len(tokens) - 2:  # Not the last token
                    split_points.append(i + 1)
        
        # If we found split points, use them
        if split_points:
            # Use first split point
            split_idx = split_points[0]
            titulo = ' '.join(tokens[:split_idx]).strip()
            dato = ' '.join(tokens[split_idx:]).strip()
            
            # Clean up título (remove trailing special chars, add colon)
            titulo = re.sub(r'[:\-]+$', '', titulo).strip()
            if not titulo.endswith(':'):
                titulo += ':'
            
            results.append((titulo, dato))
            return results
        
        # Fallback: try to split on multiple spaces or first number
        kv_match = re.match(r'^([A-Za-z][A-Za-z\s]+(?:de|del|la|el|los|las)?)\s{2,}(.+)$', line, re.I)
        if kv_match:
            titulo = kv_match.group(1).strip()
            dato = kv_match.group(2).strip()
            if not titulo.endswith(':'):
                titulo += ':'
            results.append((titulo, dato))
            return results
        
        # Try to split on first number or date
        num_match = re.search(r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|[\d,\.]+)', line)
        if num_match:
            split_pos = num_match.start()
            if split_pos > 0:
                titulo = line[:split_pos].strip()
                dato = line[split_pos:].strip()
                titulo = re.sub(r'[:\-]+$', '', titulo).strip()
                if not titulo.endswith(':'):
                    titulo += ':'
                results.append((titulo, dato))
                return results
        
        # If no pattern matches, return as título with empty dato
        results.append((line, ''))
        return results
    
    # Process all summary lines
    summary_rows = []
    for line in summary_lines:
        formatted = format_summary_line(line)
        summary_rows.extend(formatted)
    
    # Create DataFrame with two columns: Título and Dato
    if summary_rows:
        df_summary = pd.DataFrame(summary_rows, columns=['Título', 'Dato'])
    else:
        df_summary = pd.DataFrame({'Título': [], 'Dato': []})
    
    # Reassign amounts to cargos/abonos/saldo by proximity when needed
    if movement_rows:
        # prepare column centers and ranges
        col_centers = {}
        col_ranges = {}
        descripcion_range = None
        
        # Get description range to exclude amounts from it
        if 'descripcion' in columns_config:
            x0, x1 = columns_config['descripcion']
            descripcion_range = (x0, x1)
        
        for col in ('cargos', 'abonos', 'saldo'):
            if col in columns_config:
                x0, x1 = columns_config[col]
                col_centers[col] = (x0 + x1) / 2
                col_ranges[col] = (x0, x1)

        for r in movement_rows:
            amounts = r.get('_amounts', [])
            if not amounts:
                continue

            # Check if columns already have values from initial extraction
            # If they do, we should preserve them unless we find better matches
            existing_cargos = r.get('cargos', '').strip()
            existing_abonos = r.get('abonos', '').strip()
            existing_saldo = r.get('saldo', '').strip()
            
            # If columns already have numbers, keep them but prefer reassignment
            # We'll assign each detected amount to the appropriate numeric column
            # ONLY if it's within the column's coordinate range
            for amt_text, center in amounts:
                # Skip if amount is within description range (don't assign to numeric columns)
                if descripcion_range and descripcion_range[0] <= center <= descripcion_range[1]:
                    continue
                
                # Find which numeric column this amount belongs to based on coordinate range
                # Use a small tolerance for edge cases (amounts near column boundaries)
                tolerance = 10
                assigned = False
                for col in ('cargos', 'abonos', 'saldo'):
                    if col in col_ranges:
                        x0, x1 = col_ranges[col]
                        # Check with tolerance to handle amounts slightly outside the range
                        if (x0 - tolerance) <= center <= (x1 + tolerance):
                            # Amount is within this column's range (with tolerance)
                            existing = r.get(col) or ''
                            # Check if this amount is already in the column (to avoid duplicates)
                            if existing and amt_text in existing:
                                assigned = True
                                break
                            # Only assign if column is empty or if this amount is not already there
                            if not existing or amt_text not in existing:
                                if existing:
                                    r[col] = (existing + ' ' + amt_text).strip()
                                else:
                                    r[col] = amt_text
                            assigned = True
                            break
                
                # If not assigned by range, use proximity as fallback (but still exclude description range)
                if not assigned and col_centers:
                    # Calculate distances, but only consider columns that are reasonably close
                    valid_cols = {}
                    for col in col_centers.keys():
                        if col in col_ranges:
                            x0, x1 = col_ranges[col]
                            # Only consider if center is reasonably close to the column
                            if center >= (x0 - 20) and center <= (x1 + 20):
                                valid_cols[col] = abs(center - col_centers[col])
                    
                    if valid_cols:
                        nearest = min(valid_cols.keys(), key=lambda c: valid_cols[c])
                        # Double check it's not in description range
                        if not descripcion_range or not (descripcion_range[0] <= center <= descripcion_range[1]):
                            existing = r.get(nearest) or ''
                            if existing:
                                if amt_text not in existing:
                                    r[nearest] = (existing + ' ' + amt_text).strip()
                            else:
                                r[nearest] = amt_text

            # Remove amount tokens from descripcion if present
            if r.get('descripcion'):
                r['descripcion'] = DEC_AMOUNT_RE.sub('', r.get('descripcion'))

            # cleanup helper key
            if '_amounts' in r:
                del r['_amounts']
        
        # If columns_config was empty, we may have rows but without cargos/abonos/saldo
        # Try to extract them from raw text or _amounts
        if movement_rows and not columns_config and bank_config['name'] != 'BBVA':
            has_saldo = 'saldo' in columns_config
            for r in movement_rows:
                # If row has 'raw', extract from it
                if 'raw' in r and r.get('raw'):
                    raw_text = str(r.get('raw'))
                    amounts = DEC_AMOUNT_RE.findall(raw_text)
                    if len(amounts) >= 3:
                        r['cargos'] = amounts[-3]
                        r['abonos'] = amounts[-2]
                        if has_saldo:
                            r['saldo'] = amounts[-1]
                    elif len(amounts) == 2:
                        r['abonos'] = amounts[0]
                        if has_saldo:
                            r['saldo'] = amounts[1]
                    elif len(amounts) == 1:
                        if has_saldo:
                            r['saldo'] = amounts[0]
                # If row has _amounts but no cargos/abonos/saldo, try to assign them
                elif '_amounts' in r and r.get('_amounts'):
                    amounts_list = [amt for amt, _ in r.get('_amounts', [])]
                    if len(amounts_list) >= 3:
                        r['cargos'] = amounts_list[-3]
                        r['abonos'] = amounts_list[-2]
                        if has_saldo:
                            r['saldo'] = amounts_list[-1]
                    elif len(amounts_list) == 2:
                        r['abonos'] = amounts_list[0]
                        if has_saldo:
                            r['saldo'] = amounts_list[1]
                    elif len(amounts_list) == 1:
                        if has_saldo:
                            r['saldo'] = amounts_list[0]

        df_mov = pd.DataFrame(movement_rows)
    else:
        # No coordinate-based extraction available, use raw text extraction
        movement_entries = group_entries_from_lines(movements_lines)
        df_mov = pd.DataFrame({'raw': movement_entries})
        
        # For non-BBVA banks, try to extract Cargos, Abonos, Saldo from raw text
        if bank_config['name'] != 'BBVA' and len(df_mov) > 0:
            has_saldo = 'saldo' in columns_config
            def extract_amounts_from_raw(raw_text):
                """Extract Cargos, Abonos, and Saldo from raw text line."""
                if not raw_text or not isinstance(raw_text, str):
                    return {'cargos': None, 'abonos': None, 'saldo': None}
                
                # Find all amounts in the line
                amounts = DEC_AMOUNT_RE.findall(str(raw_text))
                
                # Common patterns in bank statements:
                # - Usually: Date Description Amount1 Amount2 Amount3
                # - Or: Date Description Cargos Abonos Saldo
                # - Or: Date Description Amount (could be any of the three)
                
                result = {'cargos': None, 'abonos': None, 'saldo': None}
                
                # If we have amounts, try to identify them
                # Typically, the last amount is Saldo, and before that could be Cargos/Abonos
                if len(amounts) >= 3:
                    # Three amounts: likely Cargos, Abonos, Saldo
                    result['cargos'] = amounts[-3]
                    result['abonos'] = amounts[-2]
                    if has_saldo:
                        result['saldo'] = amounts[-1]
                elif len(amounts) == 2:
                    # Two amounts: could be Cargos/Abonos and Saldo, or just two of them
                    # Check if there are keywords in the text
                    text_lower = raw_text.lower()
                    if 'cargo' in text_lower or 'retiro' in text_lower:
                        result['cargos'] = amounts[0]
                        if has_saldo:
                            result['saldo'] = amounts[1]
                    elif 'abono' in text_lower or 'deposito' in text_lower:
                        result['abonos'] = amounts[0]
                        if has_saldo:
                            result['saldo'] = amounts[1]
                    else:
                        # Default: first is Abonos (more common), second is Saldo (if exists)
                        result['abonos'] = amounts[0]
                        if has_saldo:
                            result['saldo'] = amounts[1]
                        else:
                            # If no saldo column, second amount could be cargos
                            result['cargos'] = amounts[1]
                elif len(amounts) == 1:
                    # One amount: could be any of them, check keywords
                    text_lower = raw_text.lower()
                    if 'cargo' in text_lower or 'retiro' in text_lower:
                        result['cargos'] = amounts[0]
                    elif 'abono' in text_lower or 'deposito' in text_lower:
                        result['abonos'] = amounts[0]
                    else:
                        # Default: assume it's Saldo (if exists), otherwise Abonos
                        if has_saldo:
                            result['saldo'] = amounts[0]
                        else:
                            result['abonos'] = amounts[0]
                
                return result
            
            # Extract amounts from raw text
            extracted = df_mov['raw'].apply(extract_amounts_from_raw)
            df_mov['cargos'] = extracted.apply(lambda x: x.get('cargos'))
            df_mov['abonos'] = extracted.apply(lambda x: x.get('abonos'))
            if has_saldo:
                df_mov['saldo'] = extracted.apply(lambda x: x.get('saldo'))

    # Split combined fecha values into two separate columns: Fecha Oper and Fecha Liq
    # Works for coordinate-based extraction (column 'fecha') and for fallback raw lines ('raw').
    date_pattern = re.compile(r"(?:0[1-9]|[12][0-9]|3[01])(?:[\/\-\s])[A-Za-z]{3}", re.I)

    def _extract_two_dates(txt):
        if not txt or not isinstance(txt, str):
            return (None, None)
        found = date_pattern.findall(txt)
        if not found:
            return (None, None)
        if len(found) == 1:
            return (found[0], None)
        # If more than two, take first two
        return (found[0], found[1])

    if 'fecha' in df_mov.columns:
        dates = df_mov['fecha'].astype(str).apply(_extract_two_dates)
    elif 'raw' in df_mov.columns:
        dates = df_mov['raw'].astype(str).apply(_extract_two_dates)
    else:
        dates = pd.Series([(None, None)] * len(df_mov))

    df_mov['Fecha Oper'] = dates.apply(lambda t: t[0])
    df_mov['Fecha Liq'] = dates.apply(lambda t: t[1])

    # Remove original 'fecha' if present
    if 'fecha' in df_mov.columns:
        df_mov = df_mov.drop(columns=['fecha'])
    
    # For non-BBVA banks, use only 'Fecha' column (based on Fecha Oper) and remove Fecha Liq
    if bank_config['name'] != 'BBVA':
        df_mov['Fecha'] = df_mov['Fecha Oper']
        df_mov = df_mov.drop(columns=['Fecha Oper', 'Fecha Liq'])

    # For BBVA, split 'saldo' column into 'OPERACIÓN' and 'LIQUIDACIÓN'
    if bank_config['name'] == 'BBVA' and 'saldo' in df_mov.columns:
        def _extract_two_amounts(txt):
            """Extract two amounts from the saldo column (OPERACIÓN and LIQUIDACIÓN)."""
            if not txt or not isinstance(txt, str):
                return (None, None)
            # Find all amounts matching the decimal pattern
            amounts = DEC_AMOUNT_RE.findall(str(txt))
            if len(amounts) >= 2:
                # Check if both amounts are the same (normalize by removing separators)
                # Normalize: remove commas, spaces, and compare numeric parts
                def normalize_amount(amt):
                    # Remove commas, spaces, keep only digits and decimal separator
                    normalized = re.sub(r'[,\s]', '', amt)
                    return normalized
                
                amt1_normalized = normalize_amount(amounts[0])
                amt2_normalized = normalize_amount(amounts[1])
                
                if amt1_normalized == amt2_normalized:
                    # If amounts are the same, return the same value for both columns
                    return (amounts[0], amounts[0])
                # Return first two amounts (first is LIQUIDACIÓN, second is OPERACIÓN)
                return (amounts[0], amounts[1])
            elif len(amounts) == 1:
                # Only one amount found - assign it to both columns
                return (amounts[0], amounts[0])
            else:
                return (None, None)
        
        # Extract the two amounts from saldo column
        amounts = df_mov['saldo'].astype(str).apply(_extract_two_amounts)
        df_mov['OPERACIÓN'] = amounts.apply(lambda t: t[1])  # Second amount is OPERACIÓN
        df_mov['LIQUIDACIÓN'] = amounts.apply(lambda t: t[0])  # First amount is LIQUIDACIÓN
        
        # Remove the original 'saldo' column
        df_mov = df_mov.drop(columns=['saldo'])

    # Merge 'liq' and 'descripcion' into a single 'Descripcion' column.
    # Remove any date tokens and decimal amounts from the description text.
    dec_amount_re = re.compile(r"\d{1,3}(?:[\.,\s]\d{3})*(?:[\.,]\d{2})")
    # date_pattern already defined above; reuse it

    def _build_description(row):
        parts = []
        # prefer explicit columns if present
        if 'liq' in row and row.get('liq'):
            parts.append(str(row.get('liq')))
        if 'descripcion' in row and row.get('descripcion'):
            parts.append(str(row.get('descripcion')))
        # fallback to raw if no column-based description
        if not parts and 'raw' in row and row.get('raw'):
            parts = [str(row.get('raw'))]

        text = ' '.join(parts)
        # remove extracted dates from description (handle both BBVA and non-BBVA formats)
        if 'Fecha Oper' in row:
            fo = (row.get('Fecha Oper') or '')
            if fo:
                text = text.replace(str(fo), '')
        if 'Fecha Liq' in row:
            fl = (row.get('Fecha Liq') or '')
            if fl:
                text = text.replace(str(fl), '')
        if 'Fecha' in row:
            fecha = (row.get('Fecha') or '')
            if fecha:
                text = text.replace(str(fecha), '')

        # Remove decimal amounts (they belong to cargos/abonos/saldo)
        text = dec_amount_re.sub('', text)

        # Normalize whitespace
        text = ' '.join(text.split()).strip()
        return text if text else None

    # Apply description building
    df_mov['Descripcion'] = df_mov.apply(_build_description, axis=1)

    # Drop old columns used to build description
    drop_cols = []
    for c in ('liq', 'descripcion'):
        if c in df_mov.columns:
            drop_cols.append(c)
    if drop_cols:
        df_mov = df_mov.drop(columns=drop_cols)

    # Rename columns to match desired format
    column_rename = {}
    if bank_config['name'] == 'BBVA':
        if 'Descripcion' in df_mov.columns:
            column_rename['Descripcion'] = 'Descripción'
        if 'cargos' in df_mov.columns:
            column_rename['cargos'] = 'Cargos'
        if 'abonos' in df_mov.columns:
            column_rename['abonos'] = 'Abonos'
        if 'OPERACIÓN' in df_mov.columns:
            column_rename['OPERACIÓN'] = 'Operación'
        if 'LIQUIDACIÓN' in df_mov.columns:
            column_rename['LIQUIDACIÓN'] = 'Liquidación'
    else:
        if 'Descripcion' in df_mov.columns:
            column_rename['Descripcion'] = 'Descripción'
        if 'cargos' in df_mov.columns:
            column_rename['cargos'] = 'Cargos'
        if 'abonos' in df_mov.columns:
            column_rename['abonos'] = 'Abonos'
        if 'saldo' in df_mov.columns:
            column_rename['saldo'] = 'Saldo'
    
    if column_rename:
        df_mov = df_mov.rename(columns=column_rename)

    # Rename "Fecha Liq" to "Fecha Liq." for BBVA if needed
    if bank_config['name'] == 'BBVA' and 'Fecha Liq' in df_mov.columns:
        df_mov = df_mov.rename(columns={'Fecha Liq': 'Fecha Liq.'})
    
    # Reorder columns according to bank type
    if bank_config['name'] == 'BBVA':
        # For BBVA: Fecha Oper, Fecha Liq., Descripción, Cargos, Abonos, Operación, Liquidación
        desired_order = ['Fecha Oper', 'Fecha Liq.', 'Descripción', 'Cargos', 'Abonos', 'Operación', 'Liquidación']
        # Filter to only include columns that exist in the dataframe
        desired_order = [col for col in desired_order if col in df_mov.columns]
        # Add any remaining columns that are not in desired_order
        other_cols = [c for c in df_mov.columns if c not in desired_order]
        df_mov = df_mov[desired_order + other_cols]
    else:
        # For other banks: Fecha, Descripción, Cargos, Abonos, Saldo (if available)
        # Build desired_order based on what columns are configured for this bank
        desired_order = ['Fecha', 'Descripción', 'Cargos', 'Abonos']
        
        # Only include Saldo if it's in the bank's column configuration
        if 'saldo' in columns_config:
            desired_order.append('Saldo')
        
        # Remove 'saldo' column if it exists but shouldn't (e.g., for Konfio)
        if 'saldo' in df_mov.columns and 'saldo' not in columns_config:
            df_mov = df_mov.drop(columns=['saldo'])
        if 'Saldo' in df_mov.columns and 'saldo' not in columns_config:
            df_mov = df_mov.drop(columns=['Saldo'])
        
        # Filter to only include columns that exist in the dataframe
        desired_order = [col for col in desired_order if col in df_mov.columns]
        # Only keep the desired columns, remove all others
        df_mov = df_mov[desired_order]

    print("📊 Exporting to Excel...")
    # write two sheets: summary and movements
    try:
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            df_mov.to_excel(writer, sheet_name='Movements', index=False)
        print(f"✅ Excel file created -> {output_excel}")
    except Exception as e:
        print('Error writing Excel:', e)


if __name__ == "__main__":
    main()
