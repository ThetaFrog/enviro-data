import csv
import math
import re
from pathlib import Path

import plotly.graph_objects as go
from pyproj import Transformer

#paths

HERE = Path(__file__).parent.parent
DATA_PATH = HERE / "Cleaned Data" / "Renewable Project Data Cleaned.csv"
OUT_PATH  = HERE.parent / "Website" / "renewable_map.html"



# Coordinate conversion: OS British National Grid to lat/lon - note EPSGs are refs to the respective coordinate systems

_transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)

def bng_to_latlon(easting: float, northing: float) -> tuple[float, float]:
    """
    Args:
        easting:  OS easting in metres (X-coordinate).
        northing: OS northing in metres (Y-coordinate).

    Returns:
        (latitude, longitude) in decimal degrees (WGS84).
    """
    lon, lat = _transformer.transform(easting, northing)
    return lat, lon


# ---------------------------------------------------------------------------
# Colour mapping
# ---------------------------------------------------------------------------
# Storage types take priority over technology type when present — they
# represent a distinct asset class regardless of co-located technology.
COLOUR_MAP = {
    # --- Storage types (shown when Storage Type is populated) ---
    "Stand-alone Storage":              "#e63946",  # red
    "Co-located with RE":               "#f4a261",  # orange
    "Co-located with fossil fuel plant":"#e76f51",  # burnt orange

    # --- Wind ---
    "Wind Onshore":                     "#2a9d8f",  # teal
    "Wind Offshore":                    "#264653",  # dark teal

    # --- Solar ---
    "Solar Photovoltaics":              "#e9c46a",  # yellow

    # --- Hydro / tidal / wave ---
    "Large Hydro":                      "#457b9d",  # steel blue
    "Small Hydro":                      "#a8dadc",  # light blue
    "Pumped Storage Hydroelectricity":  "#1d3557",  # navy
    "Tidal Stream":                     "#48cae4",  # cyan
    "Shoreline Wave":                   "#90e0ef",  # pale cyan

    # --- Bioenergy ---
    "Biomass (dedicated)":              "#606c38",  # dark green
    "Biomass (co-firing)":              "#a7c957",  # lime green
    "Anaerobic Digestion":              "#dda15e",  # tan
    "Landfill Gas":                     "#bc6c25",  # brown
    "Sewage Sludge Digestion":          "#8a5a44",  # dark brown
    "EfW Incineration":                 "#6a4c93",  # purple
    "Advanced Conversion Technologies": "#b5838d",  # mauve

    # --- Other renewables ---
    "Geothermal":                       "#f72585",  # pink
    "Hydrogen":                         "#7209b7",  # violet

    # --- Catch-all ---
    "Other":                            "#adb5bd",  # grey
}

DEFAULT_COLOUR = "#adb5bd"  # grey for anything not in the map

def get_colour(tech: str, storage: str) -> str:
    if storage and storage in COLOUR_MAP:
        return COLOUR_MAP[storage]
    return COLOUR_MAP.get(tech, DEFAULT_COLOUR)


# ---------------------------------------------------------------------------
# Dot size scaling — square root scale to handle the heavily skewed capacity
# distribution (median ~5 MW, max ~1728 MW). Maps sqrt(capacity) linearly
# onto the pixel range [MIN_SIZE, MAX_SIZE].
# ---------------------------------------------------------------------------
_SQRT_MAX = math.sqrt(1728)  # sqrt of dataset maximum
MIN_SIZE  = 4
MAX_SIZE  = 30

def capacity_to_size(capacity_str: str) -> float:
    try:
        cap = float(capacity_str)
        if cap <= 0:
            return MIN_SIZE
        return MIN_SIZE + (math.sqrt(cap) / _SQRT_MAX) * (MAX_SIZE - MIN_SIZE)
    except (ValueError, TypeError):
        return MIN_SIZE  # default for missing capacity


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

# Pass 1 — build a lookup of Ref ID -> (lat, lon) for all valid plotted points
coord_by_ref: dict[str, tuple[float, float]] = {}
all_rows = []

with open(DATA_PATH, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        try:
            easting  = float(row["X-coordinate"])
            northing = float(row["Y-coordinate"])
        except (ValueError, KeyError):
            continue

        lat, lon = bng_to_latlon(easting, northing)
        if not (49.0 <= lat <= 61.0 and -8.5 <= lon <= 2.0):
            continue

        row["_lat"] = lat
        row["_lon"] = lon
        all_rows.append(row)

        refid = row.get("Ref ID", "").strip()
        if refid:
            coord_by_ref[refid] = (lat, lon)

# Pass 2 — group points by legend category and collect co-location line segments
# Dict keyed by legend label -> {lats, lons, labels, colour}
groups: dict[str, dict] = {}

# Co-location lines: build as a single trace using None separators between segments
line_lats: list[float | None] = []
line_lons: list[float | None] = []
seen_pairs: set[frozenset] = set()  # avoid drawing the same line twice

for row in all_rows:
    lat      = row["_lat"]
    lon      = row["_lon"]
    refid    = row.get("Ref ID", "").strip()
    site     = row.get("Site Name", "").strip()
    tech     = row.get("Technology Type", "").strip()
    storage  = row.get("Storage Type", "").strip()
    colocated= row.get("Storage Co-location REPD Ref ID", "").strip()
    capacity = row.get("Installed Capacity (MWelec)", "").strip()

    # Legend label: storage type if present, otherwise technology type
    legend_label = storage if storage else tech
    colour = get_colour(tech, storage)

    if legend_label not in groups:
        groups[legend_label] = {"lats": [], "lons": [], "labels": [], "sizes": [], "colour": colour}

    hover = f"<b>{site}</b><br>Technology: {tech}"
    if storage:
        hover += f"<br>Storage: {storage}"
    hover += f"<br>Capacity: {capacity} MWe"

    groups[legend_label]["lats"].append(lat)
    groups[legend_label]["lons"].append(lon)
    groups[legend_label]["labels"].append(hover)
    groups[legend_label]["sizes"].append(capacity_to_size(capacity))

    # Co-location lines
    if colocated and colocated.upper() != "NA" and refid:
        # Field may contain multiple refs separated by commas or "&"
        target_refs = [r.strip() for r in re.split(r"[,&]", colocated) if r.strip()]
        for target_ref in target_refs:
            pair = frozenset([refid, target_ref])
            if pair in seen_pairs:
                continue
            if target_ref in coord_by_ref:
                seen_pairs.add(pair)
                t_lat, t_lon = coord_by_ref[target_ref]
                # Append segment with None separator so all lines stay in one trace
                line_lats.extend([lat,   t_lat, None])
                line_lons.extend([lon,   t_lon, None])


# ---------------------------------------------------------------------------
# Build map — lines first (underneath), then one marker trace per category
# ---------------------------------------------------------------------------
fig = go.Figure()

# Co-location lines — single trace, shown in legend as its own entry
if line_lats:
    fig.add_trace(go.Scattermap(
        lat=line_lats,
        lon=line_lons,
        mode="lines",
        line=dict(width=1.5, color="black"),
        hoverinfo="skip",
        name="Co-located (linked)",
        opacity=0.6,
    ))

for legend_label, data in sorted(groups.items()):
    fig.add_trace(go.Scattermap(
        lat=data["lats"],
        lon=data["lons"],
        mode="markers",
        marker=dict(size=data["sizes"], opacity=0.7, color=data["colour"]),
        text=data["labels"],
        hoverinfo="text",
        name=legend_label,
    ))

fig.update_layout(
    title=dict(
        text=(
            "UK Renewable Energy and Storage Projects<br>"
            "<sup>Source: GOV.UK Renewable Energy Planning Database (REPD) - Jul 2026</sup>"
        )  
    ),
    map=dict(
        style="carto-positron",
        center=dict(lat=54.5, lon=-2.5),
        zoom=5,
    ),
    legend=dict(
        title=dict(text="Technology / Storage Type"),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#cccccc",
        borderwidth=1,
    ),
    margin=dict(l=0, r=0, t=40, b=0),
)

fig.write_html(OUT_PATH, include_plotlyjs="cdn")
print(f"Saved → {OUT_PATH}")
