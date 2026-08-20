import argparse
import csv
import configparser
from io import BytesIO
from pathlib import Path

from extract_from_pdf import extract_all_tables
from manage_csv import save_to_csv
from models.vfr_point import PointType


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config.ini"


CANONICAL_HEADER = [
    "type",
    "name",
    "ident",
    "lat",
    "lon",
    "elev",
    "mag_decl",
    "tags",
    "remarks",
    "region",
    "visible_from",
]


def flatten_tables(all_tables, skip_header=True, start_index: int = 0):
    rows = []
    for table_info in all_tables[start_index:]:
        data = table_info.get("data", [])
        if not data:
            continue
        start = 1 if skip_header and len(data) > 1 else 0
        for row in data[start:]:
            rows.append(row)
    return rows


def load_csv_rows(csv_path: Path):
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            with open(csv_path, "r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                return list(reader)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, f"Unable to decode {csv_path}")


def parse_point_type(value: str | None):
    if not value:
        return None
    normalized = value.strip().lower()
    for point_type in PointType:
        if normalized in {point_type.name.lower(), point_type.value.lower()}:
            return point_type
    raise ValueError(f"Invalid point type: {value}")


def detect_input_kind(path: Path) -> str:
    if path.suffix.lower() == ".csv":
        return "csv"
    if path.suffix.lower() == ".pdf":
        return "pdf"

    try:
        with open(path, "rb") as f:
            signature = f.read(4)
        if signature.startswith(b"%PDF"):
            return "pdf"
    except OSError:
        pass

    return "csv"


def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding="utf-8")
    return config


def get_config_value(config, section: str, key: str, fallback: str):
    if config.has_option(section, key):
        return config.get(section, key)
    return fallback


def resolve_input_path(input_name: str, config) -> Path:
    data_dir = Path(get_config_value(config, "paths", "data_dir", "data"))
    if not data_dir.is_absolute():
        data_dir = ROOT_DIR / data_dir
    return data_dir / Path(input_name).name


def resolve_output_path(output_name: str, country: str | None, config) -> Path:
    points_dir = Path(get_config_value(config, "paths", "points_dir", "points"))
    if not points_dir.is_absolute():
        points_dir = ROOT_DIR / points_dir

    country_folder = country or get_config_value(config, "defaults", "country", "Unknown") or "Unknown"
    country_folder = country_folder.strip() or "Unknown"

    output_dir = points_dir / country_folder
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / output_name


def is_header_row(row: list[str]) -> bool:
    normalized = {cell.strip().lower() for cell in row if cell}
    return "type" in normalized and ("name" in normalized or "ident" in normalized)


def load_csv_rows_raw(csv_path: Path):
    rows = None
    last_error = None
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            with open(csv_path, "r", encoding=encoding, newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    if rows is None:
        raise last_error
    if rows and is_header_row(rows[0]):
        return rows[1:], rows[0]
    return rows, None


def merge_csv_files(input_files: list[str], output_file: str, dedupe: bool = True):
    merged_rows: list[list[str]] = []
    seen = set()
    header = None

    for file_name in input_files:
        path = Path(file_name)
        rows, detected_header = load_csv_rows_raw(path)
        if header is None and detected_header is not None:
            header = detected_header

        for row in rows:
            row_key = tuple(row)
            if dedupe and row_key in seen:
                continue
            seen.add(row_key)
            merged_rows.append(row)

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if header is not None:
            writer.writerow(header)
        writer.writerows(merged_rows)

    print(f"Merged {len(input_files)} CSV files into {output_file} ({len(merged_rows)} rows)")


def main():
    parser = argparse.ArgumentParser(description="Extract VFR points from PDF or CSV and save to CSV")
    parser.add_argument("input", nargs="?", help="Input PDF file path")
    parser.add_argument("-o", "--output", default=None, help="Output CSV file name")
    parser.add_argument("-c", "--country", default=None, help="Country tag to apply to rows")
    parser.add_argument("--type", dest="forced_type", default=None, help="Force all points to this type")
    parser.add_argument("--merge", nargs="+", help="Merge already treated CSV files into a single output")
    parser.add_argument("--no-dedupe", action="store_true", help="Do not remove duplicate rows when merging CSVs")
    parser.add_argument("--start-page-index", type=int, default=0, help="Index of first table to process (0-based)")
    args = parser.parse_args()

    config = load_config()

    if args.merge:
        country = args.country.capitalize() if args.country else get_config_value(config, "defaults", "country", "").capitalize() or None
        output_name = args.output or get_config_value(config, "defaults", "merge_output", "merged.csv")
        output_path = resolve_output_path(output_name, country, config)
        merge_csv_files(args.merge, str(output_path), dedupe=not args.no_dedupe)
        return

    if not args.input:
        parser.error("input is required unless --merge is used")

    pdf_path = resolve_input_path(args.input, config)
    if not pdf_path.exists():
        print(f"Input file not found: {pdf_path}")
        return

    input_kind = detect_input_kind(pdf_path)

    if input_kind == "csv":
        rows = load_csv_rows(pdf_path)
        all_tables = []
    else:
        with open(pdf_path, "rb") as f:
            pdf_buffer = BytesIO(f.read())

        all_tables = extract_all_tables(pdf_buffer)
        rows = flatten_tables(all_tables, start_index=args.start_page_index)

    forced_type = parse_point_type(args.forced_type)
    country = args.country.capitalize() if args.country else get_config_value(config, "defaults", "country", "").capitalize() or None
    output_name = args.output or get_config_value(config, "defaults", "output_name_template", f"{pdf_path.stem}.csv").format(input_stem=pdf_path.stem, country=country or "Unknown")
    output_path = resolve_output_path(output_name, country, config)
    save_to_csv(
        rows,
        str(output_path),
        country=country,
        forced_type=forced_type,
    )
    source_label = "CSV" if input_kind == "csv" else "PDF"
    print(f"Wrote {output_path} ({len(rows)} rows parsed from {len(all_tables)} tables, source={source_label})")


if __name__ == "__main__":
    main()
