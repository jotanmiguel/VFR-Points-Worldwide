from dataclasses import dataclass
from enum import Enum

class PointType(str, Enum):
    """
    Userpoint types available in littlenavmap.

    Args:
        str (str): The string representation of the enum member.
        Enum (str): The base class for creating enumerated constants.
    """
    AIRPORT = "Airport"
    AIRSTRIP = "Airstrip"
    BUILDING = "Building"
    CABIN = "Cabin"
    CLOSED = "Closed"
    DME = "DME"
    FLAG = "Flag"
    HELIPAD = "Helipad"
    HISTORY = "History"
    LANDFORM = "Landform"
    LIGHTHOUSE = "Lighthouse"
    LOCATION = "Location"
    MARKER = "Marker"
    MOUNTAIN = "Mountain"
    NDB = "NDB"
    OBSTACLE = "Obstacle"
    OIL_PLATFORM = "Oil Platform"
    OTHER = "Other"
    POI = "Point of Interest"
    PARK = "Park"
    PIN = "Pin"
    RADIO_RANGE = "Radio Range"
    SEAPORT = "Seaport"
    SETTLEMENT = "Settlement"
    TACAN = "TACAN"
    UNKNOWN = "Unknown"
    VOR = "VOR"
    VORDME = "VORDME"
    VORTAC = "VORTAC"
    VRP = "VRP"
    WATER = "Water"
    WAYPOINT = "Waypoint" # Could be used to represent a reporting point or a visual holding point

# Order of the fields in the CSV file read by littlenavmap. This order is important for the CSV export to be compatible with littlenavmap.:
# 1 - Type, 2 - Name, 3 - Ident, 4 - Lat, 5 - Lon, 6 - Elev, 7 - Magnetic Declination, 8 - Tags, 9 - Remarks, 10 - Region, 11 - Visible From

@dataclass(slots=True)
class VFRPoint:
    """
    A point representation based on the littlenavmap fields.

    Returns:
        _type_: _description_
    """
    type: PointType = PointType.VRP
    name: str = "" # Actual name of the point, e.g., "Cabo Raso", "Esposende"
    ident: str = "" # Up to 5 characters, e.g., "CRASO (CABO RASO)", "ESPOS (ESPOSENDE)"
    lat: float = 0.0 # Latitude in decimal degrees
    lon: float = 0.0 # Longitude in decimal degrees
    elev: str = "0" # Elevation in feet, as a string to preserve formatting, e.g., "0", "10", "100"
    mag_decl: int = 0 # Magnetic declination in degrees, defaulting to 0
    tags: str = "" # Usually the country name, e.g., "Portugal". Could be used for other tags or categories.
    remarks: str = "" # Remarks or additional information about the point.
    region: str = "" # Usually the region name, e.g., "Norte", "Centro", "Sul" or "AML", "ALENTEJO", "ALGARVE", "MADEIRA", "AZORES"
    visible_from: int = 100 # Optional field indicating where the point is visible from, e.g., "Visible from the sea", "Visible from the air" 
    
    def to_csv_row(self) -> list[str]:
        return [
            self.type.value,
            self.name,
            self.ident,
            str(self.lat),
            str(self.lon),
            str(self.elev),
            str(self.mag_decl),
            self.tags,
            self.remarks,
            self.region,
            str(self.visible_from)
        ]
