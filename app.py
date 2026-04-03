import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

# --- 1. CONFIGURATION & AREA ---
# This covers North of Glasgow down to the Border, and Belfast to Edinburgh
LAT_MIN, LAT_MAX = 54.8, 56.2
LON_MIN, LON_MAX = -6.5, -3.0
CUMNOCK_LAT, CUMNOCK_LON = 55.4542, -4.2673

st.set_page_config(page_title="Scotland & NI Live Radar", layout="wide")

st.markdown(f"""
    <style>
    .main {{
        background-color: #111;
    }}
    </style>
    """, unsafe_allow_html=True)

st.title("✈️ Live Flight Radar: Cumnock, GLA, EDI, BFS")
st.write("Showing aircraft from Belfast to Edinburgh. Click a plane for details.")

# Airline lookup for local traffic
AIRLINES = {
    "RYR": "Ryanair", "EZY": "EasyJet", "LOG": "Loganair", 
    "EXS": "Jet2", "BAW": "British Airways", "BEE": "Flybe",
    "NPT": "Atlantic Airlines", "BOX": "DHL/AeroLogic", "FDX": "FedEx"
}

# --- 2. DATA FETCHING FUNCTION ---
def get_flight_data():
    # Credentials from Streamlit Secrets
    try:
        user = st.secrets["OPENSKY_USER"]
        password = st.secrets["OPENSKY_PASS"]
    except:
        st.error("Error: OpenSky credentials not found in Streamlit Secrets.")
        return pd.DataFrame()

    # The OpenSky API URL with bounding box
    url = f"https://opensky-network.org/api/states/all?lamin={LAT_MIN}&lamax={LAT_MAX}&lomin={LON_MIN}&lomax={LON_MAX}"
    
    try:
        # 30 second timeout to avoid the connection error
        r = requests.get(url, auth=(user, password), timeout=30)
        
        if r.status_code == 503:
            st.warning("OpenSky server is busy. Retrying in 10 seconds...")
            return pd.DataFrame()
            
        data = r.json()
        states = data.get("states", [])
        
        if not states:
            return pd.DataFrame()
            
        columns = ['icao24', 'callsign', 'origin', 'time', 'contact', 'lon', 'lat', 'alt', 'ground', 'vel', 'deg', 'vert', 'sens', 'geo', 'sqwk', 'spi', 'src']
        return pd.DataFrame(states, columns=columns)

    except requests.exceptions.Timeout:
        st.error("The connection timed out. The OpenSky server is a bit slow right now—try clicking Refresh again.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Radar Error: {e}")
        return pd.DataFrame()

# --- 3. UI CONTROLS ---
col1, col2 = st.columns([1, 5])
with col1:
    refresh = st.button('🔄 Refresh Radar')
    if refresh:
        st.cache_data.clear()

# --- 4. MAP & VISUALIZATION ---
df = get_flight_data()

if not df.empty:
    # Create the map focused on the center of the region
    m = folium.Map(location=[55.5, -4.5], zoom_start=8, tiles='CartoDB dark_matter')
    
    # Red Marker for Home (Cumnock)
    folium.Marker(
        [CUMNOCK_LAT, CUMNOCK_LON], 
        tooltip="Cumnock", 
        icon=folium.Icon(color='red', icon='home')
    ).add_to(m)

    for _, row in df.iterrows():
        if row['lat'] and row['lon']:
            # Clean up the data
            callsign = row['callsign'].strip() if row['callsign'] else "N/A"
            airline = AIRLINES.get(callsign[:3], "Unknown/Private")
            alt_ft = int(row['alt'] * 3.28) if row['alt'] else 0
            speed_mph = int(row['vel'] * 2.237) if row['vel'] else 0
            heading = row['deg'] if row['deg'] else 0
            
            # FlightRadar24 Link
            fr24_link = f"https://www.flightradar24.com/{callsign}"
            
            popup_content = f"""
                <div style="font-family: Arial; width: 180px;">
                    <h4 style="margin:0; color:#007bff;">{callsign}</h4>
                    <b>Airline:</b> {airline}<br>
                    <b>Altitude:</b> {alt_ft:,} ft<br>
                    <b>Speed:</b> {speed_mph} mph<br>
                    <hr style="margin:5px 0;">
                    <a href="{fr24_link}" target="_blank" style="color:green; font-weight:bold;">View on FlightRadar24</a>
                </div>
            """
            
            # Draw plane icon
            folium.Marker(
                [row['lat'], row['lon']],
                popup=folium.Popup(popup_content, max_width=250),
                tooltip=f"{callsign} ({alt_ft}ft)",
                icon=folium.Icon(color='blue' if not row['ground'] else 'lightgray', icon='plane')
            ).add_to(m)

    # Display Map
    st_folium(m, width="100%", height=600)
    
    # Display Table
    with st.expander("See Raw Data List"):
        st.dataframe(df[['callsign', 'alt', 'vel', 'deg']])

else:
    st.info("No aircraft detected in the area at this moment. Hit Refresh to try again.")
    # Map still shows even if no planes
    m_empty = folium.Map(location=[55.5, -4.5], zoom_start=8, tiles='CartoDB dark_matter')
    st_folium(m_empty, width="100%", height=600)

st.caption("Data provided by OpenSky Network. All altitudes in feet. Locations are real-time.")
