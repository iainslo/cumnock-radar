import streamlit as st
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import folium
from streamlit_folium import st_folium
import time

# --- 1. CONFIG & AREA ---
LAT_MIN, LAT_MAX = 55.3, 56.1   # Sanquhar to Balloch
LON_MIN, LON_MAX = -5.4, -3.6   # Arran to Lanark
CUMNOCK = [55.4542, -4.2673]

st.set_page_config(page_title="Ayrshire Radar", layout="wide")
st.title("✈️ Ayrshire & Central Flight Radar")

# --- 2. THE "SMART" DATA FETCHING ---
# This caches the data for 30 seconds so your family doesn't 
# accidentally spam the API and get blocked.
@st.cache_data(ttl=30)
def get_flight_data_hardened():
    user = st.secrets["OPENSKY_USER"]
    password = st.secrets["OPENSKY_PASS"]
    url = f"https://opensky-network.org/api/states/all?lamin={LAT_MIN}&lamax={LAT_MAX}&lomin={LON_MIN}&lomax={LON_MAX}"
    
    # Set up a "Retry Strategy"
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        # Request with a longer 30s timeout and the retry strategy
        r = session.get(url, auth=(user, password), timeout=30)
        r.raise_for_status()
        data = r.json()
        states = data.get("states", [])
        
        if not states:
            return pd.DataFrame()
            
        columns = ['icao24', 'callsign', 'origin', 'time', 'contact', 'lon', 'lat', 'alt', 'ground', 'vel', 'deg', 'vert', 'sens', 'geo', 'sqwk', 'spi', 'src']
        return pd.DataFrame(states, columns=columns)

    except Exception as e:
        return f"Error: {e}"

# --- 3. UI LAYOUT ---
col1, col2 = st.columns([1, 1])

with col1:
    if st.button('🔄 Refresh Map'):
        st.cache_data.clear()
        st.rerun()

with col2:
    # BACKUP LINK: If the API is failing, your family can click this
    backup_url = f"https://globe.adsbexchange.com/?lat={CUMNOCK[0]}&lon={CUMNOCK[1]}&zoom=10"
    st.markdown(f'''<a href="{backup_url}" target="_blank"><button style="background-color:#FF4B4B; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;">⚠️ API Slow? Use Backup Map</button></a>''', unsafe_allow_html=True)

# --- 4. PROCESSING ---
result = get_flight_data_hardened()

# Create Map
m = folium.Map(location=[55.65, -4.4], zoom_start=10, tiles='CartoDB dark_matter')
folium.Marker(CUMNOCK, tooltip="Cumnock", icon=folium.Icon(color='red', icon='home')).add_to(m)

if isinstance(result, pd.DataFrame) and not result.empty:
    for _, row in result.iterrows():
        if row['lat'] and row['lon']:
            callsign = row['callsign'].strip() or "N/A"
            alt = int(row['alt'] * 3.28) if row['alt'] else 0
            
            folium.Marker(
                [row['lat'], row['lon']],
                popup=f"Flight: {callsign}<br>Alt: {alt}ft",
                icon=folium.Icon(color='blue', icon='plane')
            ).add_to(m)
    st.success(f"Found {len(result)} aircraft.")
elif isinstance(result, str):
    st.error("The OpenSky server is currently overloaded.")
    st.info("This is common during busy hours. Please use the 'Backup Map' button above or try again in a few minutes.")
else:
    st.info("No planes currently in the specific Arran-Lanark box.")

st_folium(m, width="100%", height=600)
