import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import time
from opencage.geocoder import OpenCageGeocode

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="wide")

# Initialize Session States for Multi-Profile Memory
if 'profiles' not in st.session_state:
    st.session_state.profiles = [] 
if 'current_data' not in st.session_state:
    st.session_state.current_data = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

# --- 2. RELIABLE ENGINES (OpenCage & Gemini) ---
def get_coords(city_name):
    """Uses OpenCage API for reliable location searching."""
    try:
        key = st.secrets["OPENCAGE_API_KEY"]
        geocoder = OpenCageGeocode(key)
        results = geocoder.geocode(city_name)
        if results and len(results):
            return results[0]['geometry']['lat'], results[0]['geometry']['lng']
    except Exception as e:
        st.error(f"Geocoding Error: {e}")
    return None

try:
    # Uses your new PAID Gemini key from Streamlit Secrets
    SERVER_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=SERVER_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Missing GEMINI_API_KEY in Secrets.")
    st.stop()

# --- 3. ASTROLOGY ENGINE (Core Functions) ---

def get_gana_yoni(nakshatra_name):
    """Vital data for Gana and Yoni calculations."""
    data = {
        "Ashwini": ("Deva", "Horse"), "Bharani": ("Manushya", "Elephant"), "Krittika": ("Rakshasa", "Goat"),
        "Rohini": ("Manushya", "Snake"), "Mrigashira": ("Deva", "Snake"), "Ardra": ("Manushya", "Dog"),
        "Punarvasu": ("Deva", "Cat"), "Pushya": ("Deva", "Goat"), "Ashlesha": ("Rakshasa", "Cat"),
        "Magha": ("Rakshasa", "Rat"), "Purva Phalguni": ("Manushya", "Rat"), "Uttara Phalguni": ("Manushya", "Cow"),
        "Hasta": ("Deva", "Buffalo"), "Chitra": ("Rakshasa", "Tiger"), "Swati": ("Deva", "Buffalo"),
        "Vishakha": ("Rakshasa", "Tiger"), "Anuradha": ("Deva", "Deer"), "Jyeshtha": ("Rakshasa", "Deer"),
        "Mula": ("Rakshasa", "Dog"), "Purva Ashadha": ("Manushya", "Monkey"), "Uttara Ashadha": ("Manushya", "Mongoose"),
        "Shravana": ("Deva", "Monkey"), "Dhanishta": ("Rakshasa", "Lion"), "Shatabhisha": ("Rakshasa", "Horse"),
        "Purva Bhadrapada": ("Manushya", "Lion"), "Uttara Bhadrapada": ("Manushya", "Cow"), "Revati": ("Deva", "Elephant")
    }
    return data.get(nakshatra_name, ("Unknown", "Unknown"))

def calculate_vedic_chart(name, gender, dt, tm, lat, lon, city):
    """Calculates precisely to ensure 1969 Capricorn Lagna Fix."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    local_dt = datetime.datetime.combine(dt, tm)
    # Adjust for IST (UTC+5:30)
    utc_dt = local_dt - datetime.timedelta(hours=5, minutes=30) 
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    # THE CRITICAL LAGNA FIX: Manual Ayanamsa shift
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    
    # Shifting the Ascendant degree by Ayanamsa back from Aquarius to Capricorn
    asc_sidereal = (ascmc[0] - ayanamsa) % 360
    
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lagna_sign = zodiac[int(asc_sidereal // 30)]
    
    # PLANETARY POSITIONS (Force Sidereal Flag 65536)
    SIDEREAL_FLAG = 64 * 1024
    planet_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, 
                  "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, 
                  "Rahu": swe.MEAN_NODE, "Ketu": swe.MEAN_NODE}
    
    results = []
    user_rashi, user_nak = "", ""
    nak_list = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

    for p, pid in planet_map.items():
        pos = swe.calc_ut(jd, pid, SIDEREAL_FLAG)[0][0]
        if p == "Ketu": pos = (pos + 180) % 360
        sign = zodiac[int(pos // 30)]
        nak = nak_list[int(pos / (360/27))]
        results.append(f"{p}: {sign} ({pos % 30:.2f}°) | {nak}")
        if p == "Moon": user_rashi, user_nak = sign, nak
            
    gana, yoni = get_gana_yoni(user_nak)
    return {"Name": name, "Gender": gender, "Lagna": lagna_sign, "Rashi": user_rashi, 
            "Nakshatra": user_nak, "Gana": gana, "Yoni": yoni, "City": city, 
            "Full_Chart": "\n".join(results)}

# --- 4. SIDEBAR (Multi-Profile Logic) ---
with st.sidebar:
    st.header("🗂 Profiles")
    if st.session_state.profiles:
        p_names = [p['Name'] for p in st.session_state.profiles]
        selected_p = st.selectbox("Switch Active Profile", ["New Profile..."] + p_names)
        if selected_p != "New Profile...":
            st.session_state.current_data = next(p for p in st.session_state.profiles if p['Name'] == selected_p)

    st.divider()
    st.header("👤 Add Birth Details")
    name_in = st.text_input("Name")
    gender_in = st.selectbox("Gender", ["Male", "Female", "Other"])
    dob_in = st.date_input("Date", value=datetime.date(1993, 4, 23), min_value=datetime.date(1900, 1, 1), format="DD/MM/YYYY")
    
    c1, c2 = st.columns(2)
    with c1: hour_in = st.selectbox("Hour", range(24), index=15)
    with c2: min_in = st.selectbox("Minute", range(60), index=45)
    city_in = st.text_input("Birth City", "Kolkata, India")
    
    if st.button("✨ Save & Generate", type="primary"):
        with st.spinner("Connecting to stars..."):
            coords = get_coords(city_in)
            if coords:
                chart = calculate_vedic_chart(name_in, gender_in, dob_in, datetime.time(hour_in, min_in), coords[0], coords[1], city_in)
                st.session_state.profiles.append(chart)
                st.session_state.current_data = chart
                st.rerun()

# --- 5. MAIN UI ---
st.title("☸️ TaraVaani")
if st.session_state.current_data:
    data = st.session_state.current_data
    st.success(f"Radhe Radhe! {data['Name']}'s chart is now active. 🙏")
    
    cols = st.columns(5)
    cols[0].metric("Lagna", data['Lagna'])
    cols[1].metric("Rashi", data['Rashi'])
    cols[2].metric("Nakshatra", data['Nakshatra'])
    cols[3].metric("Gana", data['Gana'])
    cols[4].metric("Yoni", data['Yoni'])
    
    st.divider()
    st.subheader("📜 Planetary Positions")
    st.text(data['Full_Chart'])
else:
    st.info("👈 Enter birth details in the sidebar to create your first profile.")
