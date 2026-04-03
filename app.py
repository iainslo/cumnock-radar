import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

# --- 1. SETTINGS & AREA ---
ST_LAT, ST_LON = 55.4542, -4.2673  # Cumnock
# Bounding box: Cumnock to Prestwick
LAT_MIN, LAT_MAX = 55.3, 55.7
LON_MIN, LON_MAX = -4.9, -4.0

st.set_page_config(page_title="Cumnock Radar", layout="wide")
st.title("✈️ Cumnock & Prestwick Live Radar")

# Airline Lookup Dictionary
AIRLINES = {"RYR": "Ryanair", "EZY": "EasyJet", "LOG": "Loganair", "EXS": "Jet2", "BAW": "British Airways"}

# --- 2. FETCH DATA FROM OPENSKY ---
def get_flight_data():
    # Use Secrets for credentials
    user = st.secrets["OPENSKY_USER"]
    password = st.secrets["OPENSKY_PASS"]
    
    url = f"https://opensky-network.org/api/states/all?lamin={LAT_MIN}&lamin={LAT_MIN}&lamax={LAT_MAX}&lomin={LON_MIN}&lomax={LON_MAX}"
    
    try:
        r = requests.get(url, auth=(user, password), timeout=10)
        data = r.json()
        states = data.get("states", [])
        columns = ['icao24', 'callsign', 'origin', 'time', 'contact', 'lon', 'lat', 'alt', 'ground', 'vel', 'deg', 'vert', 'sens', 'geo', 'sqwk', 'spi', 'src']
        return pd.DataFrame(states, columns=columns)
    except:
        return pd.DataFrame()

# --- 3. BUILD THE INTERFACE ---
if st.button('Refresh Live Data'):
    st.cache_data.clear()

df = get_flight_data()

if not df.empty:
    # Map Setup
    m = folium.Map(location=[ST_LAT, ST_LON], zoom_start=11, tiles='CartoDB dark_matter')
    
    # Add Cumnock Home Marker
    folium.Marker([ST_LAT, ST_LON], tooltip="Cumnock", icon=folium.Icon(color='red')).add_to(m)

    for _, row in df.iterrows():
        if row['lat'] and row['lon']:
            callsign = row['callsign'].strip() if row['callsign'] else "N/A"
            airline_code = callsign[:3]
            airline_name = AIRLINES.get(airline_code, "Unknown Airline")
            alt_ft = int(row['alt'] * 3.28) if row['alt'] else 0
            
            # Create a link for more info
            fr24_link = f"https://www.flightradar24.com/{callsign}"
            
            popup_html = f"""
                <b>Flight: {callsign}</b><br>
                <b>Airline:</b> {airline_name}<br>
                <b>Alt:</b> {alt_ft} ft<br>
                <a href="{fr24_link}" target="_blank">View Details</a>
            """
            
            folium.Marker(
                [row['lat'], row['lon']],
                popup=folium.Popup(popup_html, max_width=200),
                icon=folium.Icon(color='blue', icon='plane'),
                tooltip=f"{callsign} ({airline_name})"
            ).add_to(m)

    st_folium(m, width=1200, height=600)
    st.dataframe(df[['callsign', 'alt', 'vel']])
else:
    st.warning("No aircraft found in the Cumnock/Prestwick box right now.")
