import re
from typing import Any, Iterable, Optional

from models.vfr_point import PointType, VFRPoint
import geo_conversion


# Accept both "384951N 0075023W" and "384951N0075023W"
COMPACT_COORD_RE = re.compile(r"\d{6,7}[NS]\s*\d{6,7}[EW]", re.IGNORECASE)
COMPACT_COORD_EMBEDDED_RE = re.compile(r"(\d{6,7}[NS])\s*(\d{6,7}[EW])", re.IGNORECASE)
COMPACT_COORD_TIGHT_RE = re.compile(r"(\d{6,7}[NS])(\d{6,7}[EW])", re.IGNORECASE)


def _strip_embedded_coords(text: str) -> str:
    if not text:
        return ""
    cleaned = COMPACT_COORD_EMBEDDED_RE.sub("", text)
    cleaned = cleaned.replace("  ", " ").strip(" ,;|-\t\n\r")
    return cleaned


def infer_type_from_name(name: str) -> PointType:
    n = (name or "").lower()
    mapping = {
        "helipad": PointType.HELIPAD,
        "heliport": PointType.HELIPAD,
        "heliporto": PointType.HELIPAD,
        "aeroporto": PointType.AIRPORT,
        "airport": PointType.AIRPORT,
        "airstrip": PointType.AIRSTRIP,
        "marina": PointType.SEAPORT,
        "porto": PointType.SEAPORT,
    }

    for k, v in mapping.items():
        if k in n:
            return v
    return PointType.VRP


def resolve_point_type(value: str | PointType | None, fallback_name: str = "") -> PointType:
    if isinstance(value, PointType):
        return value
    if value:
        normalized = str(value).strip().lower()
        for point_type in PointType:
            if normalized in {point_type.name.lower(), point_type.value.lower()}:
                return point_type
    return infer_type_from_name(fallback_name)


def find_coords_index(row: Iterable[str]) -> Optional[int]:
    for i, cell in enumerate(row):
        if not cell:
            continue
        text = cell.replace('\n', ' ').strip()
        # Only detect compact coordinate format (e.g., 384951N 0075023W or 384951N0075023W)
        if COMPACT_COORD_RE.search(text) or COMPACT_COORD_TIGHT_RE.search(text):
            return i
    return None


def find_ident_index(row: Iterable[str]) -> Optional[int]:
    for i, cell in enumerate(row):
        if not cell:
            continue
        text = cell.strip()
        # Ident is up to 5 chars (letters or digits)
        if re.fullmatch(r"[A-Z0-9]{1,5}", text.upper()):
            return i
    return None


def find_embedded_coords(row: Iterable[str]) -> tuple[Optional[int], str]:
    for i, cell in enumerate(row):
        if not cell:
            continue
        text = cell.replace("\n", " ").strip()
        match = COMPACT_COORD_EMBEDDED_RE.search(text)
        if match:
            return i, f"{match.group(1)} {match.group(2)}"
    return None, ""


def _get_value(row: list[str] | dict[str, Any], key: str, index: Optional[int] = None) -> str:
    if isinstance(row, dict):
        lowered = {str(k).strip().lower(): v for k, v in row.items()}
        value = lowered.get(key.lower(), "")
        return str(value).strip() if value is not None else ""
    if index is None or index >= len(row):
        return ""
    value = row[index]
    return str(value).strip() if value is not None else ""


def parse_row_to_point(
    row: list[str] | dict[str, Any],
    country: Optional[str] = None,
    column_map: Optional[dict] = None,
    forced_type: str | PointType | None = None,
) -> VFRPoint:
    """
    Converte uma linha de tabela arbitrária para `VFRPoint`.

    - `column_map` pode ser {'name': idx, 'coords': idx, 'ident': idx} para forçar colunas.
    - Se não for fornecido, tentamos detetar automaticamente.
    """
    name = ""
    ident = ""
    coords_raw = ""

    if isinstance(row, dict):
        lowered = {str(k).strip().lower(): v for k, v in row.items()}
        name = str(lowered.get("name", "") or "").strip()
        coords_raw = str(lowered.get("coords", lowered.get("coord", lowered.get("coordinates", ""))) or "").strip()
        ident = str(lowered.get("ident", lowered.get("id", "")) or "").strip()
    elif column_map:
        name = _get_value(row, "name", column_map.get("name"))
        coords_raw = _get_value(row, "coords", column_map.get("coords"))
        ident = _get_value(row, "ident", column_map.get("ident"))
    else:
        coords_idx = find_coords_index(row)
        ident_idx = find_ident_index(row)

        if coords_idx is None:
            coords_idx, embedded_coords = find_embedded_coords(row)
            if embedded_coords:
                coords_raw = embedded_coords

        if coords_idx is not None:
            coords_raw = row[coords_idx].strip()
        if ident_idx is not None:
            ident = row[ident_idx].strip()

        # name: pick the longest non-coord, non-ident cell and strip embedded coords if any
        candidates = [
            _strip_embedded_coords(c.strip())
            for i, c in enumerate(row)
            if c and i not in (coords_idx, ident_idx)
        ]
        candidates = [c for c in candidates if c]
        if candidates:
            name = max(candidates, key=len)

        # If ident is still empty, use the shortest remaining clean alpha-numeric cell
        if not ident:
            ident_candidates = [
                _strip_embedded_coords(c.strip())
                for i, c in enumerate(row)
                if c and i != coords_idx
            ]
            ident_candidates = [c for c in ident_candidates if re.fullmatch(r"[A-Z0-9]{1,5}", c.upper())]
            if ident_candidates:
                ident = min(ident_candidates, key=len)

        # Last resort: if name still empty, choose any remaining text after stripping coords
        if not name:
            text_candidates = [
                _strip_embedded_coords(c.strip())
                for c in row
                if c and _strip_embedded_coords(c.strip())
            ]
            if text_candidates:
                name = max(text_candidates, key=len)

    # Normalizar coords compactas sem espaço: 384951N0075023W -> inserir espaço
    if coords_raw and not re.search(r"\s", coords_raw):
        m = COMPACT_COORD_TIGHT_RE.search(coords_raw)
        if m:
            coords_raw = m.group(1) + " " + m.group(2)

    # Converter para decimais
    lat = lon = 0.0
    if coords_raw:
        try:
            # se for compacto (digitos) use compact_to_decimal
            if COMPACT_COORD_RE.search(coords_raw):
                lat, lon = geo_conversion.compact_to_decimal(coords_raw)
            else:
                lat_str, lon_str = geo_conversion.parse_dms_combined(coords_raw)
                lat, lon = geo_conversion.latlon_to_xyz(lat_str, lon_str)
        except (ValueError, IndexError, AttributeError):
            lat, lon = 0.0, 0.0

    point_type = resolve_point_type(forced_type, name)
    
    elev = None  # Default elevation; could be enhanced to parse from row if available
    
    mag_decl = None  # Default magnetic declination; could be enhanced to parse from row if available
    
    remarks = None  # Default remarks; could be enhanced to parse from row if available

    region = None  # Default region; could be enhanced to parse from row if available
    
    visible_from = None  # Default visibility; could be enhanced to parse from row if available
    
    return VFRPoint(
        type=point_type,
        ident=ident,
        name=name,
        lat=lat,
        lon=lon,
        elev=elev or "0",
        mag_decl=mag_decl or 0,
        tags=country or "",
        remarks=remarks or "",
        region=region or "",
        visible_from=visible_from or 100
    )
