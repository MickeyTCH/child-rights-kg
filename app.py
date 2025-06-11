import streamlit as st
from rdflib import Graph, Namespace
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="Child Rights Project Explorer", layout="wide")
st.title("📊 Child Rights Project Explorer with CRC Alignment")

# Load RDF file
ttl_file = "childrights_with_crc.ttl"
g = Graph()
g.parse(ttl_file, format="turtle")

# Namespaces
EX = Namespace("http://www.example.org/childrights#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

# SPARQL query including CRC alignment
query = """
PREFIX : <http://www.example.org/childrights#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?projectLabel ?startYear ?endYear ?regionLabel ?topicLabel ?ngoName ?crcNumber ?crcLabel WHERE {
  ?project a :Project ;
           :startYear ?start ;
           :endYear ?end ;
           rdfs:label ?projectLabel .

  OPTIONAL {
    ?project :locatedIn ?region .
    ?region rdfs:label ?regionLabel .
  }

  OPTIONAL {
    ?project :focusesOn ?topic .
    ?topic rdfs:label ?topicLabel .
  }

  OPTIONAL {
    ?project :implementedBy ?ngo .
    ?ngo :name ?ngoName .
  }

  OPTIONAL {
    ?project :alignsWithCRC ?crc .
    ?crc :articleNumber ?crcNumber ;
         rdfs:label ?crcLabel .
  }

  BIND(xsd:integer(?start) AS ?startYear)
  BIND(xsd:integer(?end) AS ?endYear)
}
"""

results = g.query(query)

# Convert to DataFrame
data = []
for row in results:
    data.append({
        "Project": str(row.projectLabel),
        "Start Year": int(row.startYear),
        "End Year": int(row.endYear),
        "Region": str(row.regionLabel) if row.regionLabel else "Unspecified",
        "Topic": str(row.topicLabel) if row.topicLabel else "Unspecified",
        "NGO": str(row.ngoName) if row.ngoName else "Unspecified",
        "CRC Article": f"Article {row.crcNumber} – {row.crcLabel}" if row.crcNumber else "Unspecified"
    })

df = pd.DataFrame(data)
df["Start Year"] = df["Start Year"].astype(str)
df["End Year"] = df["End Year"].astype(str)

# Sidebar Filters
with st.sidebar:
    st.header("🔍 Filter Projects")
    project_filter = st.text_input("Search project by name")
    min_year = st.selectbox("Start Year From", sorted(df["Start Year"].unique()))
    max_year = st.selectbox("End Year Until", sorted(df["End Year"].unique(), reverse=True))
    region_options = ["All"] + sorted(df["Region"].unique())
    topic_options = ["All"] + sorted(df["Topic"].unique())
    ngo_options = ["All"] + sorted(df["NGO"].unique())
    crc_options = ["All"] + sorted(df["CRC Article"].unique())

    selected_region = st.selectbox("Filter by Region", region_options)
    selected_topic = st.selectbox("Filter by Advocacy Topic", topic_options)
    selected_ngo = st.selectbox("Filter by NGO", ngo_options)
    selected_crc = st.selectbox("Filter by CRC Article", crc_options)

# Apply filters
filtered_df = df[
    df["Project"].str.contains(project_filter, case=False) &
    (df["Start Year"] >= min_year) &
    (df["End Year"] <= max_year)
]
if selected_region != "All":
    filtered_df = filtered_df[filtered_df["Region"] == selected_region]
if selected_topic != "All":
    filtered_df = filtered_df[filtered_df["Topic"] == selected_topic]
if selected_ngo != "All":
    filtered_df = filtered_df[filtered_df["NGO"] == selected_ngo]
if selected_crc != "All":
    filtered_df = filtered_df[filtered_df["CRC Article"] == selected_crc]

st.success(f"Showing {len(filtered_df)} of {len(df)} projects based on filters")
st.dataframe(filtered_df.style.format({"Start Year": "{}", "End Year": "{}"}), use_container_width=True)

# Region coordinates
region_coords = {
    "Zurich": (47.3769, 8.5417),
    "Lake Geneva Region": (46.2044, 6.1432),
    "Canton of Valais": (46.1950, 7.5956),
    "Unspecified": (None, None)
}

# Add coordinates
filtered_df["lat"] = filtered_df["Region"].apply(lambda x: region_coords.get(x, (None, None))[0])
filtered_df["lon"] = filtered_df["Region"].apply(lambda x: region_coords.get(x, (None, None))[1])
map_df = filtered_df.dropna(subset=["lat", "lon"])

# Show map
if not map_df.empty:
    st.subheader("🗺️ Project Region Map")
    view_state = pdk.ViewState(
        latitude=map_df["lat"].mean(),
        longitude=map_df["lon"].mean(),
        zoom=7,
        pitch=0,
    )
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position=["lon", "lat"],
        get_radius=10000,
        get_fill_color=[255, 140, 0],
        pickable=True,
        auto_highlight=True,
    )
    tooltip = {
        "html": "<b>Project:</b> {Project}<br><b>Years:</b> {Start Year}–{End Year}<br><b>Region:</b> {Region}<br><b>Topic:</b> {Topic}<br><b>NGO:</b> {NGO}<br><b>CRC:</b> {CRC Article}",
        "style": {"backgroundColor": "navy", "color": "white"}
    }
    deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)
    st.pydeck_chart(deck)
else:
    st.info("No valid coordinates for map view.")
