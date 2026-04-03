
import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

# --- 1. SETTINGS & NEW LARGE AREA ---
# This covers North of GLA down to the Border, and Belfast to Edinburgh
LAT_MIN, LAT_MAX = 54.8, 56.2
LON_MIN, LON_MAX = -6.5, -3.0
CENTER_LAT, CENTER_LON = 55.5, -4.5 # Center of the map (Ayrshire area)

st.set_page_config(page_title="Scotland & NI Flight Radar", layout="wide")
st.title("✈️ Live Radar: GLA - EDI - BFS - Cumnock")

# Airline Lookup
AIRLINES = {
    "RYR": "Ryanair", "EZY": "EasyJet", "LOG": "Loganair", 
    "EXS": "Jet2", "BAW": "British Airways", "BEE": "Flybe",
    "NPT": "Atlantic Airlines (Cargo)", "BOX": "DHL/AeroLogic"
}

# --- 2. FETCH DATA ---
def get_flight_data():
    user = st.secrets["OPENSKY_USER"]
    password = st.secrets["OPENSKY_PASS"]
    
    # Corrected API URL with the expanded bounding box
    url = f"https://opensky-network.org/api/states/all?lamin={LAT_MIN}&lamax={LAT_MAX}&lomin={LON_MIN}&lomax={LON_MAX}"
    
    try:
        r = requests.get(url, auth=(user, password), timeout=10)
        data = r.json()
        states = data.get("states", [])
        if not states:
            return pd.DataFrame()
            
        columns = ['icao24', 'callsign', 'origin', 'time', 'contact', 'lon', 'lat', 'alt', 'ground', 'vel', 'deg', 'vert', 'sens', 'geo', 'sqwk', 'spi', 'src']
        return pd.DataFrame(states, columns=columns)
    except Exception as e:
        st.error(f"API Error: {e}")
        return pd.DataFrame()

# --- 3. BUILD INTERFACE ---
if st.button('Refresh Radar'):
    st.cache_data.clear()

df = get_flight_data()

if not df.empty:
    # Zoomed out to 8 to see the whole region
    m = folium.Map(location=[CENTER_LAT, CENTER_LON], zoom_start=8, tiles='CartoDB dark_matter')
    
    # Marker for Cumnock (Home)
    folium.Marker([55.4542, -4.2673], tooltip="Cumnock", icon=folium.Icon(color='red')).add_to(m)

    for _, row in df.iterrows():
        if row['lat'] and row['lon']:
            callsign = row['callsign'].strip() if row['callsign'] else "N/A"
            airline_name = AIRLINES.get(callsign[:3], "Unknown/Private")
            alt_ft = int(row['alt'] * 3.28) if row['alt'] else 0
            speed_mph = int(row['vel'] * 2.237) if row['vel'] else 0
            
            # Link to FlightRadar24 for Aircraft Type/Route details
            fr24_link = f"https://www.flightradar24.com/{callsign}"
            
            popup_html = f"""
                <div style="font-family: sans-serif; min-width: 150px;">
                    <b style="color: #007bff;">Flight: {callsign}</b><br>
                    <b>Airline:</b> {airline_name}<br>
                    <b>Altitude:</b> {alt_ft:,} ft<br>
                    <b>Speed:</b> {speed_mph} mph<br>
                    <hr>
                    <a href="{fr24_link}" target="_blank" style="color: #28a745;">More Info (FR24)</a>
                </div>
            """
            
            folium.Marker(
                [row['lat'], row['lon']],
                popup=folium.Popup(popup_html, max_width=250),
                # Using a simple plane icon, rotating it by the degree of travel
                icon=folium.Icon(color='blue' if not row['ground'] else 'lightgray', icon='plane'),
                tooltip=f"{callsign} - {alt_ft}ft"
            ).add_to(m)

    st_folium(m, width=1200, height=700)
    
    # Table below the map
    st.subheader("Live Data Table")
    st.dataframe(df[['callsign', 'alt', 'vel', 'deg']].dropna())
else:
    st.warning("No aircraft found in this region. Check if the OpenSky API is down or try refreshing.")
