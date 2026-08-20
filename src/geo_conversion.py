import re


def _dms_to_decimal(value: str) -> float:
    """
    Converte uma coordenada DMS (Degrees, Minutes, Seconds) para graus decimais.

    Args:
        value (str): Coordenada em formato DMS, ex: "38° 49' 51" N"

    Raises:
        ValueError: Se a coordenada não for válida

    Returns:
        float: Coordenada em graus decimais
    """
    text = value.strip().upper()
    sign = -1 if any(h in text for h in ("S", "W")) else 1

    numbers = [float(part) for part in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        raise ValueError(f"Coordenada inválida: {value}")

    degrees = numbers[0]
    minutes = numbers[1] if len(numbers) > 1 else 0.0
    seconds = numbers[2] if len(numbers) > 2 else 0.0

    return sign * (degrees + minutes / 60.0 + seconds / 3600.0)


def parse_dms_combined(coord_str: str) -> tuple[str, str]:
    """
    Parse coordenadas DMS combinadas em formato comprimido.
    
    Entrada esperada: "384951N 0075023W"
    - 38° 49' 51" N (latitude)
    - 007° 50' 23" W (longitude)
    
    Retorna: ("38° 49' 51\" N", "7° 50' 23\" W")
    """
    text = coord_str.strip()
    
    # Pattern para formato comprimido: DDMMSSN DDDMMSEW
    pattern_compact = re.compile(
        r"(\d{2})(\d{2})(\d{2})([NS])\s+(\d{3})(\d{2})(\d{2})([EW])",
        re.IGNORECASE,
    )
    match = pattern_compact.search(text)
    if match:
        lat_deg, lat_min, lat_sec, lat_dir = match.group(1, 2, 3, 4)
        lon_deg, lon_min, lon_sec, lon_dir = match.group(5, 6, 7, 8)
        
        lat_str = f"{int(lat_deg)}° {int(lat_min)}' {int(lat_sec)}\" {lat_dir}"
        lon_str = f"{int(lon_deg)}° {int(lon_min)}' {int(lon_sec)}\" {lon_dir}"
        
        return lat_str, lon_str
    
    # Pattern para formato com separadores: 38° 49' 51" N, 7° 50' 23" W
    pattern_formatted = re.compile(
        r"([0-9°º''\"\.\s]+[NS])\s*[,;/ ]+\s*([0-9°º''\"\.\s]+[EW])",
        re.IGNORECASE,
    )
    match = pattern_formatted.search(text)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # Fallback: split por espaços/virgulas
    parts = re.split(r"\s{2,}|,|;|/", text)
    parts = [part.strip() for part in parts if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1]

    raise ValueError(f"Não foi possível separar latitude/longitude: {coord_str}")


def latlon_to_xyz(lat_str: str, lon_str: str) -> tuple[float, float]:
    """
    Converte coordenadas DMS para graus decimais (xyz).

    Args:
        lat_str (str): Latitude em formato DMS
        lon_str (str): Longitude em formato DMS

    Returns:
        tuple[float, float]: (latitude decimal, longitude decimal)
    """
    return _dms_to_decimal(lat_str), _dms_to_decimal(lon_str)


def compact_to_decimal(coord_str: str) -> tuple[float, float]:
    """
    Converte coordenadas em formato comprimido diretamente para graus decimais.
    
    Entrada esperada: "384951N 0075023W"
    Saída: (38.83083333333334, -7.839722222222222)

    Args:
        coord_str (str): Coordenadas em formato comprimido (ex: "384951N 0075023W")

    Returns:
        tuple[float, float]: (latitude decimal, longitude decimal)
    """
    lat_str, lon_str = parse_dms_combined(coord_str)
    return latlon_to_xyz(lat_str, lon_str)


if __name__ == "__main__":
    print(compact_to_decimal("384951N 0075023W"))  # (38.83083333333334, -7.839722222222222)
