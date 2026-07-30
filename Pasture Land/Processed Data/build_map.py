import csv
import json
import os

import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# 1. FAO name → ISO-3 mapping (non-standard names only; standard ones resolved below)
# ---------------------------------------------------------------------------
MANUAL_ISO3 = {
    "Bolivia (Plurinational State of)":               "BOL",
    "Bosnia and Herzegovina":                          "BIH",
    "British Virgin Islands":                          "VGB",
    "Brunei Darussalam":                               "BRN",
    "Cabo Verde":                                      "CPV",
    "Central African Republic":                        "CAF",
    "Channel Islands":                                 "JEY",   # no single ISO; use Jersey as proxy
    "China, Hong Kong SAR":                            "HKG",
    "China, mainland":                                 "CHN",
    "Congo":                                           "COG",
    "Cook Islands":                                    "COK",
    "Côte d'Ivoire":                                   "CIV",
    "Democratic People's Republic of Korea":          "PRK",
    "Democratic Republic of the Congo":               "COD",
    "Dominican Republic":                              "DOM",
    "Equatorial Guinea":                               "GNQ",
    "Eswatini":                                        "SWZ",
    "Falkland Islands (Malvinas)":                     "FLK",
    "Faroe Islands":                                   "FRO",
    "French Guiana":                                   "GUF",
    "French Polynesia":                                "PYF",
    "Guinea-Bissau":                                   "GNB",
    "Iran (Islamic Republic of)":                      "IRN",
    "Isle of Man":                                     "IMN",
    "Kyrgyzstan":                                      "KGZ",
    "Lao People's Democratic Republic":               "LAO",
    "Marshall Islands":                                "MHL",
    "Micronesia (Federated States of)":               "FSM",
    "New Caledonia":                                   "NCL",
    "Norfolk Island":                                  "NFK",
    "North Macedonia":                                 "MKD",
    "Northern Mariana Islands":                        "MNP",
    "Palestine":                                       "PSE",
    "Papua New Guinea":                                "PNG",
    "Republic of Korea":                               "KOR",
    "Republic of Moldova":                             "MDA",
    "Russian Federation":                              "RUS",
    "Saint Helena, Ascension and Tristan da Cunha":   "SHN",
    "Saint Kitts and Nevis":                           "KNA",
    "Saint Lucia":                                     "LCA",
    "Saint Pierre and Miquelon":                       "SPM",
    "Saint Vincent and the Grenadines":                "VCT",
    "Sao Tome and Principe":                           "STP",
    "Saudi Arabia":                                    "SAU",
    "Sierra Leone":                                    "SLE",
    "Solomon Islands":                                 "SLB",
    "South Sudan":                                     "SSD",
    "Sri Lanka":                                       "LKA",
    "Syrian Arab Republic":                            "SYR",
    "Timor-Leste":                                     "TLS",
    "Trinidad and Tobago":                             "TTO",
    "Turks and Caicos Islands":                        "TCA",
    "Türkiye":                                         "TUR",
    "United Arab Emirates":                            "ARE",
    "United Kingdom of Great Britain and Northern Ireland": "GBR",
    "United Republic of Tanzania":                     "TZA",
    "United States Virgin Islands":                    "VIR",
    "United States of America":                        "USA",
    "Viet Nam":                                        "VNM",
    "Wallis and Futuna Islands":                       "WLF",
    "Western Sahara":                                  "ESH",
    "Venezuela (Bolivarian Republic of)":              "VEN",
    "Netherlands (Kingdom of the)":                   "NLD",
    "Réunion":                                         "REU",
    "American Samoa":                                  "ASM",
    "Antigua and Barbuda":                             "ATG",
    "Cayman Islands":                                  "CYM",
    "Guadeloupe":                                      "GLP",
    "Martinique":                                      "MTQ",
    "Mayotte":                                         "MYT",
    "Montserrat":                                      "MSR",
    "Niue":                                            "NIU",
    "Puerto Rico":                                     "PRI",
    "San Marino":                                      "SMR",
    "Seychelles":                                      "SYC",
    "Singapore":                                       "SGP",
    "Turkmenistan":                                    "TKM",
    "Uzbekistan":                                      "UZB",
}

# Simple name → ISO3 for countries whose FAO name is close enough to resolve directly
SIMPLE_ISO3 = {
    "Afghanistan": "AFG", "Albania": "ALB", "Algeria": "DZA",
    "Andorra": "AND", "Angola": "AGO", "Argentina": "ARG",
    "Armenia": "ARM", "Aruba": "ABW", "Australia": "AUS",
    "Austria": "AUT", "Azerbaijan": "AZE", "Bahamas": "BHS",
    "Bahrain": "BHR", "Bangladesh": "BGD", "Barbados": "BRB",
    "Belarus": "BLR", "Belgium": "BEL", "Belize": "BLZ",
    "Benin": "BEN", "Bermuda": "BMU", "Bhutan": "BTN",
    "Botswana": "BWA", "Brazil": "BRA", "Bulgaria": "BGR",
    "Burkina Faso": "BFA", "Burundi": "BDI", "Cambodia": "KHM",
    "Cameroon": "CMR", "Canada": "CAN", "Chad": "TCD",
    "Chile": "CHL", "Colombia": "COL", "Comoros": "COM",
    "Croatia": "HRV", "Cuba": "CUB", "Cyprus": "CYP",
    "Czechia": "CZE", "Denmark": "DNK", "Djibouti": "DJI",
    "Dominica": "DMA", "Ecuador": "ECU", "Egypt": "EGY",
    "El Salvador": "SLV", "Eritrea": "ERI", "Estonia": "EST",
    "Ethiopia": "ETH", "Fiji": "FJI", "Finland": "FIN",
    "France": "FRA", "Gabon": "GAB", "Gambia": "GMB",
    "Georgia": "GEO", "Germany": "DEU", "Ghana": "GHA",
    "Greece": "GRC", "Greenland": "GRL", "Grenada": "GRD",
    "Guam": "GUM", "Guatemala": "GTM", "Guinea": "GIN",
    "Guyana": "GUY", "Haiti": "HTI", "Honduras": "HND",
    "Hungary": "HUN", "Iceland": "ISL", "India": "IND",
    "Indonesia": "IDN", "Iraq": "IRQ", "Ireland": "IRL",
    "Israel": "ISR", "Italy": "ITA", "Jamaica": "JAM",
    "Japan": "JPN", "Jordan": "JOR", "Kazakhstan": "KAZ",
    "Kenya": "KEN", "Kiribati": "KIR", "Kuwait": "KWT",
    "Latvia": "LVA", "Lebanon": "LBN", "Lesotho": "LSO",
    "Liberia": "LBR", "Libya": "LBY", "Liechtenstein": "LIE",
    "Lithuania": "LTU", "Luxembourg": "LUX", "Madagascar": "MDG",
    "Malawi": "MWI", "Malaysia": "MYS", "Maldives": "MDV",
    "Mali": "MLI", "Malta": "MLT", "Mauritania": "MRT",
    "Mauritius": "MUS", "Mexico": "MEX", "Mongolia": "MNG",
    "Montenegro": "MNE", "Morocco": "MAR", "Mozambique": "MOZ",
    "Myanmar": "MMR", "Namibia": "NAM", "Nepal": "NPL",
    "Nicaragua": "NIC", "Niger": "NER", "Nigeria": "NGA",
    "Norway": "NOR", "Oman": "OMN", "Pakistan": "PAK",
    "Palau": "PLW", "Panama": "PAN", "Paraguay": "PRY",
    "Peru": "PER", "Philippines": "PHL", "Poland": "POL",
    "Portugal": "PRT", "Qatar": "QAT", "Romania": "ROU",
    "Rwanda": "RWA", "Samoa": "WSM", "Senegal": "SEN",
    "Serbia": "SRB", "Slovakia": "SVK", "Slovenia": "SVN",
    "Somalia": "SOM", "South Africa": "ZAF", "Spain": "ESP",
    "Sudan": "SDN", "Suriname": "SUR", "Sweden": "SWE",
    "Switzerland": "CHE", "Tajikistan": "TJK", "Thailand": "THA",
    "Togo": "TGO", "Tonga": "TON", "Tunisia": "TUN",
    "Uganda": "UGA", "Ukraine": "UKR", "Uruguay": "URY",
    "Vanuatu": "VUT", "Yemen": "YEM", "Zambia": "ZMB",
    "Zimbabwe": "ZWE", "Kosovo": "XKX",
    "Costa Rica": "CRI", "New Zealand": "NZL",
}

ALL_ISO3 = {**SIMPLE_ISO3, **MANUAL_ISO3}

# ---------------------------------------------------------------------------
# 2. Load processed data
# ---------------------------------------------------------------------------
DATA_PATH = "/Users/angad/Documents/Kiro Projects/enviro-data/Pasture Land/Processed Data/Pasture Land Percentages 2021.txt"

rows = []
with open(DATA_PATH, encoding="utf-8") as f:
    reader = csv.reader(f, delimiter=";")
    next(reader)
    for row in reader:
        if len(row) < 4:
            continue
        country  = row[0].strip('"')
        perm     = float(row[1].strip('"'))
        tmp      = float(row[2].strip('"'))
        overall  = float(row[3].strip('"'))
        iso3     = ALL_ISO3.get(country)
        rows.append({"country": country, "perm": perm, "tmp": tmp, "overall": overall, "iso3": iso3})

df = pd.DataFrame(rows)
unmatched = df[df["iso3"].isna()]["country"].tolist()
if unmatched:
    print("WARNING – no ISO3 code for:", unmatched)

df = df.dropna(subset=["iso3"])

# ---------------------------------------------------------------------------
# 3. Build colour scale: white → yellow → orange → red
# ---------------------------------------------------------------------------
COLORSCALE = [
    [0.00, "#ffffff"],
    [0.25, "#ffee88"],
    [0.50, "#ffaa00"],
    [0.75, "#ff5500"],
    [1.00, "#cc0000"],
]

def make_trace(col_field, label):
    return go.Choropleth(
        locations=df["iso3"],
        z=df[col_field],
        text=df["country"],
        customdata=df[col_field],
        hovertemplate=(
            "<b>%{text}</b><br>"
            f"{label}: " + "%{customdata:.2f}%<extra></extra>"
        ),
        colorscale=COLORSCALE,
        zmin=0,
        zmax=100,
        marker_line_color="rgba(80,80,80,0.4)",
        marker_line_width=0.4,
        colorbar=dict(
            title=dict(text="% of land area", font=dict(size=12)),
            tickvals=[0, 25, 50, 75, 100],
            ticktext=["0%", "25%", "50%", "75%", "100%"],
            thickness=14,
            len=0.6,
            x=1.01,
        ),
        visible=False,
    )

trace_overall = make_trace("overall", "Overall pastureland")
trace_perm    = make_trace("perm",    "Permanent pasture")
trace_tmp     = make_trace("tmp",     "Temporary pasture")

trace_overall.visible = True   # default view

# ---------------------------------------------------------------------------
# 4. Toggle buttons
# ---------------------------------------------------------------------------
buttons = [
    dict(
        label="Overall",
        method="update",
        args=[
            {"visible": [True, False, False]},
            {"title": {"text": (
                "Pastureland as % of Total Land Area (2021)<br>"
                "<sup>Overall (permanent + temporary) · Values in '000 ha · Source: FAO</sup>"
            ), "x": 0.5, "xanchor": "center"}},
        ],
    ),
    dict(
        label="Permanent",
        method="update",
        args=[
            {"visible": [False, True, False]},
            {"title": {"text": (
                "Permanent Pasture as % of Total Land Area (2021)<br>"
                "<sup>Permanent pasture only · Values in '000 ha · Source: FAO</sup>"
            ), "x": 0.5, "xanchor": "center"}},
        ],
    ),
    dict(
        label="Temporary",
        method="update",
        args=[
            {"visible": [False, False, True]},
            {"title": {"text": (
                "Temporary Pasture as % of Total Land Area (2021)<br>"
                "<sup>Temporary pasture only · Values in '000 ha · Source: FAO</sup>"
            ), "x": 0.5, "xanchor": "center"}},
        ],
    ),
]

# ---------------------------------------------------------------------------
# 5. Layout
# ---------------------------------------------------------------------------
fig = go.Figure(data=[trace_overall, trace_perm, trace_tmp])

fig.update_layout(
    title=dict(
        text=(
            "Pastureland as % of Total Land Area (2021)<br>"
            "<sup>Overall (permanent + temporary) · Values in '000 ha · Source: FAO</sup>"
        ),
        x=0.5,
        xanchor="center",
        font=dict(size=18),
    ),
    geo=dict(
        showframe=False,
        showcoastlines=True,
        coastlinecolor="rgba(100,100,100,0.5)",
        showland=True,
        landcolor="#f0f0f0",
        showocean=True,
        oceancolor="#ffffff",
        showlakes=True,
        lakecolor="#ffffff",
        projection_type="robinson",
        bgcolor="rgba(0,0,0,0)",
    ),
    updatemenus=[
        dict(
            type="buttons",
            direction="right",
            x=0.5,
            xanchor="center",
            y=1.08,
            yanchor="top",
            buttons=buttons,
            showactive=True,
            bgcolor="#f7f7f7",
            bordercolor="#cccccc",
            font=dict(size=13),
            pad={"r": 8, "t": 8, "b": 8, "l": 8},
        )
    ],
    margin=dict(l=0, r=0, t=100, b=0),
    paper_bgcolor="white",
    height=620,
)

# ---------------------------------------------------------------------------
# 6. Save
# ---------------------------------------------------------------------------
OUT_PATH = "/Users/angad/Documents/Kiro Projects/enviro-data/Pasture Land/Processed Data/pasture_map.html"
fig.write_html(OUT_PATH, include_plotlyjs="cdn")
print(f"Saved → {OUT_PATH}")
print(f"Countries plotted: {len(df)}")
