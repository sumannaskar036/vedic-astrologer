import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import time
from opencage.geocoder import OpenCageGeocode # Highly reliable API

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="wide")

# --- 2. SESSION STATE (The Brain) ---
# This persists your family data even when you click buttons
if 'profiles' not in st.session_state:
    st.session_state.profiles = [] # List to store Mother, Brother, etc.
if 'current_data' not in st.session_state:
    st.session_state.current_data = None

# --- 3. RELIABLE GEOCODER (OpenCage) ---
def get_coords(city_name):
    """Uses OpenCage API for 100% reliable city searching."""
    try:
        # Get key from st.secrets
        key = st.secrets["OPENCAGE_API_KEY"]
        geocoder = OpenCageGeocode(key)
        results = geocoder.geocode(city_name)
        if results and len(results):
            return results[0]['geometry']['lat'], results[0]['geometry']['lng']
    except Exception as e:
        st.error(f"Geocoding Error: {e}")
    return None

# --- SECURITY: Get Paid Tier AI Key ---
try:
    SERVER_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=SERVER_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Missing GEMINI_API_KEY in Secrets.")
    st.stop()

# --- 4. ASTROLOGY ENGINE (Core Functions) ---
def calculate_vedic_chart(name, gender, dt, tm, lat, lon, city):
    # 1. INITIALIZE VEDIC ENGINE
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    # 2. CONVERT TIME TO JULIAN DAY
    local_dt = datetime.datetime.combine(dt, tm)
    # Adjust for IST (UTC+5:30)
    utc_dt = local_dt - datetime.timedelta(hours=5, minutes=30) 
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    # 3. CALCULATE THE EXACT AYANAMSA (The secret to shifting from Aquarius to Capricorn)
    ayanamsa = swe.get_ayanamsa_ut(jd)
    
    # 4. CALCULATE HOUSES (Get Tropical first, then shift manually)
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    
    # 5. MANUALLY SHIFT ASCENDANT TO SIDEREAL (The Absolute Fix)
    # (Tropical Ascendant - Ayanamsa) = Vedic Ascendant
    asc_sidereal = (ascmc[0] - ayanamsa) % 360
    
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    
    lagna_sign = zodiac[int(asc_sidereal // 30)]
    
    # 6. PLANETARY POSITIONS (Force Sidereal Flag 65536)
    SIDEREAL_FLAG = 64 * 1024
    planet_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, 
                  "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, 
                  "Rahu": swe.MEAN_NODE, "Ketu": swe.MEAN_NODE}
    
    results = []
    user_rashi, user_nak = "", ""
    nak_list = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

    for p, pid in planet_map.items():
        # Get planetary position using the sidereal flag
        pos = swe.calc_ut(jd, pid, SIDEREAL_FLAG)[0][0]
        if p == "Ketu": pos = (pos + 180) % 360
        
        sign = zodiac[int(pos // 30)]
        nak = nak_list[int(pos / (360/27))]
        results.append(f"{p}: {sign} ({pos % 30:.2f}°) | {nak}")
        
        if p == "Moon":
            user_rashi, user_nak = sign, nak
            
    gana, yoni = get_gana_yoni(user_nak)
    return {"Name": name, "Gender": gender, "Lagna": lagna_sign, "Rashi": user_rashi, "Nakshatra": user_nak, "Gana": gana, "Yoni": yoni, "City": city, "Full_Chart": "\n".join(results)}
    for p, pid in planet_map.items():
        # Get planetary position using the sidereal flag
        pos = swe.calc_ut(jd, pid, SIDEREAL_FLAG)[0][0]
        if p == "Ketu": pos = (pos + 180) % 360
        
        sign = zodiac[int(pos // 30)]
        nak = nak_list[int(pos / (360/27))]
        results.append(f"{p}: {sign} ({pos % 30:.2f}°) | {nak}")
        
        if p == "Moon":
            user_rashi, user_nak = sign, nak
            
    gana, yoni = get_gana_yoni(user_nak)
    return {"Name": name, "Gender": gender, "Lagna": lagna_sign, "Rashi": user_rashi, "Nakshatra": user_nak, "Gana": gana, "Yoni": yoni, "City": city, "Full_Chart": "\n".join(results)}

    for p, pid in planet_map.items():
        pos = swe.calc_ut(jd, pid, SEFLG_SIDEREAL)[0][0]
        if p == "Ketu": pos = (pos + 180) % 360
        
        sign = zodiac[int(pos // 30)]
        nak = nak_list[int(pos / (360/27))]
        results.append(f"{p}: {sign} ({pos % 30:.2f}°) | {nak}")
        
        if p == "Moon":
            user_rashi, user_nak = sign, nak
            
    gana, yoni = get_gana_yoni(user_nak)
    return {"Name": name, "Gender": gender, "Lagna": lagna_sign, "Rashi": user_rashi, "Nakshatra": user_nak, "Gana": gana, "Yoni": yoni, "City": city, "Full_Chart": "\n".join(results)}

# --- 5. SIDEBAR (Profiles & Inputs) ---
with st.sidebar:
    st.header("🗂 Profiles")
    # Multi-Profile Selection
    if st.session_state.profiles:
        profile_names = [p['Name'] for p in st.session_state.profiles]
        selected = st.selectbox("Select Saved Profile", ["Create New..."] + profile_names)
    else:
        selected = "Create New..."

    st.divider()
    st.header("👤 Add Birth Details")
    name_in = st.text_input("Full Name")
    gender_in = st.selectbox("Gender", ["Male", "Female", "Other"])
    dob_in = st.date_input("Date of Birth", value=datetime.date(1993, 4, 23), min_value=datetime.date(1900, 1, 1), format="DD/MM/YYYY")
    
    c1, c2 = st.columns(2)
    with c1: hour_in = st.selectbox("Hour", range(24), index=15)
    with c2: min_in = st.selectbox("Minute", range(60), index=45)
    tob_in = datetime.time(hour_in, min_in)
    
    city_in = st.text_input("Birth City", "Kolkata, India")
    
    if st.button("✨ Save & Generate", type="primary"):
        with st.spinner("Geocoding & Calculating..."):
            coords = get_coords(city_in)
            if coords:
                chart_data = calculate_vedic_chart(name_in, gender_in, dob_in, tob_in, coords[0], coords[1], city_in)
                st.session_state.profiles.append(chart_data) # Save to session
                st.session_state.current_data = chart_data
                st.rerun()
            else:
                st.error("Could not find city. Check spelling.")

# --- 6. MAIN UI ---
st.title("☸️ TaraVaani")
if st.session_state.current_data:
    data = st.session_state.current_data
    st.success(f"Radhe Radhe! {data['Name']}'s chart is active. 🙏")
    
    # Beautiful Data Table
    cols = st.columns(5)
    fields = ["Lagna", "Rashi", "Nakshatra", "Gana", "Yoni"]
    for i, field in enumerate(fields):
        cols[i].metric(field, data[field])
    
    st.divider()
    st.subheader("📜 Planetary Positions")
    st.text(data['Full_Chart'])
else:
    st.info("👈 Enter birth details in the sidebar and click 'Save & Generate' to begin.")
