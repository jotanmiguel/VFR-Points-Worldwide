import csv

from parsers import parse_row_to_point

def save_to_csv(data: list, output_file: str, country: str | None = None, forced_type=None):
    """
    Salva os dados extraídos em um arquivo CSV.
    
    Args:
        data (list): Lista de dicionários contendo os dados a serem salvos.
        output_file (str): Caminho do arquivo CSV de saída.
    """
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in data:
            try:
                point = parse_row_to_point(row, country=country, forced_type=forced_type)
                writer.writerow(point.to_csv_row())
            except (ValueError, IndexError, AttributeError, KeyError) as e:
                print(f"Erro ao processar linha: {row} - {e}")
                continue
        
        print("Linhas extraídas com sucesso.")