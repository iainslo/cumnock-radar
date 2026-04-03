import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

# --- 1. NEW FOCUSED AREA (Arran to Lanark / Balloch to Sanquhar) ---
LAT_MIN, LAT_MAX = 55.3, 56.1   # Sanquhar to Balloch
LON_MIN, LON_MAX = -5.4, -3.6   # Arran to Lanark
CUMNOCK_LAT, CUMNOCK_LON = 55.4542, -4.2673

st.set_page_config(page_title="Ayrshire & Central Radar", layout="wide")

st.title("✈️ Live Radar: GLA, PIK & Cumnock Area")
st.write("Focused on Arran to Lanark / Balloch to Sanquhar.")

# Airline lookup
AIRLINES = {
    "RYR": "Ryanair", "EZY": "EasyJet", "LOG": "Loganair", 
    "EXS": "Jet2", "BAW": "British Airways", "NPT": "Atlantic Airlines", 
    "BOX": "DHL", "FDX": "FedEx", "TAY": "ASL Airlines"
}

# --- 2. DATA FETCHING ---
def get_flight_data():
    try:
        user = st.secrets["OPENSKY_USER"]
        password = st.secrets["OPENSKY_PASS"]
    except:
        st.error("Error: Check your Streamlit Secrets for credentials.")
        return pd.DataFrame()

    url = f"https://opensky-network.org/api/states/all?lamin={LAT_MIN}&lamax={LAT_MAX}&lomin={LON_MIN}&lomax={LON_MAX}"
    
    try:
        # Request data with a 20s timeout
        r = requests.get(url, auth=(user, password), timeout=20)
        
        if r.status_code == 200:
            data = r.json()
            states = data.get("states", [])
            if not states:
                return pd.DataFrame()
            
            columns = ['icao24', 'callsign', 'origin', 'time', 'contact', 'lon', 'lat', 'alt', 'ground', 'vel', 'deg', 'vert', 'sens', 'geo', 'sqwk', 'spi', 'src']
            return pd.DataFrame(states, columns=columns)
        elif r.status_code == 503:
            st.warning("OpenSky server is temporarily busy. Please wait a moment.")
            return pd.DataFrame()
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Waiting for OpenSky connection... ({e})")
        return pd.DataFrame()

# --- 3. UI CONTROLS ---
if st.button('🔄 Refresh Radar'):
    st.cache_data.clear()

df = get_flight_data()

# --- 4. MAP VISUALIZATION ---
# Focused on the midpoint between GLA and PIK
m = folium.Map(location=[55.65, -4.4], zoom_start=10, tiles='CartoDB dark_matter')

# Marker for Cumnock
folium.Marker(
    [CUMNOCK_LAT, CUMNOCK_LON], 
    tooltip="Cumnock", 
    icon=folium.Icon(color='red', icon='home')
).add_to(m)

if not df.empty:
    for _, row in df.iterrows():
        if row['lat'] and row['lon']:
            callsign = row['callsign'].strip() if row['callsign'] else "N/A"
            airline = AIRLINES.get(callsign[:3], "Unknown/Private")
            alt_ft = int(row['alt'] * 3.28) if row['alt'] else 0
            speed_mph = int(row['vel'] * 2.237) if row['vel'] else 0
            
            fr24_link = f"https://www.flightradar24.com/{callsign}"
            
            popup_html = f"""
                <div style="font-family: Arial; width: 160px;">
                    <b style="color:#007bff;">{callsign}</b><br>
                    {airline}<br>
                    {alt_ft:,} ft | {speed_mph} mph<br>
                    <a href="{fr24_link}" target="_blank">View on FR24</a>
                </div>
            """
            
            folium.Marker(
                [row['lat'], row['lon']],
                popup=folium.Popup(popup_html, max_width=200),
                tooltip=f"{callsign}",
                icon=folium.Icon(color='blue' if not row['ground'] else 'lightgray', icon='plane')
            ).add_to(m)

# Display Map
st_folium(m, width="100%", height=650)

if not df.empty:
    with st.expander("Show List View"):
        st.dataframe(df[['callsign', 'alt', 'vel']])
else:
    st.info("No planes currently in the Arran-Lanark-Balloch-Sanquhar box.")
