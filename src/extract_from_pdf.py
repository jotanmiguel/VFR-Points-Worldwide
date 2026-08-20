import pdfplumber
from io import BytesIO
import geo_conversion


def extract_all_tables(pdf_buffer: BytesIO) -> list[dict]:
    """
    Extract all tables from PDF buffer.
    
    Args:
        pdf_buffer (io.BytesIO): PDF in memory.
    
    Returns:
        list: List of tables (each table is a list of lists).
    """
    tables = []
    
    with pdfplumber.open(pdf_buffer) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            page_tables = page.extract_tables()
            if page_tables:
                for table in page_tables:
                    # Limpar newlines e espaços vazios
                    cleaned_table = []
                    for row in table:
                        cleaned_row = [
                            cell.replace('\n', ' ').strip() if cell else ''
                            for cell in row
                        ]
                        # Remover colunas vazias no final
                        cleaned_row = [c for c in cleaned_row if c]
                        cleaned_table.append(cleaned_row)
                    
                    tables.append({
                        "page": page_num,
                        "data": cleaned_table
                    })
    
    return tables

def analyze_pdf(file: str, country: str|None = None, table_range: tuple[int, int] | None = None) -> list[dict]:
    """
    Analyze PDF using Camelot to extract tables.
    
    Args:
        pdf_buffer (io.BytesIO): PDF in memory.
    
    Returns:
        list: List of tables (each table is a list of lists).
    """
    with open(file, "rb") as f:
        pdf_buffer = BytesIO(f.read())
        
    extracted_tables = extract_all_tables(pdf_buffer)[table_range[0]:table_range[1]] if table_range else extract_all_tables(pdf_buffer)
    
def handle_row(row: list[str], country: str|None = None) -> dict:
    """
    Handle a single row of extracted table data.
    
    Args:
        row (list): A single row from the extracted table.
    
    Returns:
        dict: Processed data from the row.
    """
    try:
        type_vrp = "VRP"
        ident = row[0].strip() if len(row) > 0 else ""
        
        # Extract combined lat/lon from row[1]
        coord_str = row[1].strip() if len(row) > 1 else ""
        
        if not coord_str:
            raise ValueError(f"Coordenadas vazias para {ident}")
        
        # Parse combined coordinates
        lat_str, lon_str = geo_conversion.parse_dms_combined(coord_str)
        lat, lon = geo_conversion.latlon_to_xyz(lat_str, lon_str)
        
        name = row[2].strip() if len(row) > 2 else ""
        elev = row[3].strip() if len(row) > 3 else "0"
        unk = 0
        tags = country or "Portugal"
        
        return {
            "type": type_vrp,
            "ident": ident,
            "name": name,
            "lat": lat,
            "lon": lon,
            "elev": elev,
            "unk": unk,
            "tags": tags,
            "remarks": None,
            "region": None
        }
    except Exception as e:
        print(f"Erro ao processar linha: {row} - {e}")
        return {} 
