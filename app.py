import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from opencage.geocoder import OpenCageGeocode
import json

# --- 1. GLOBAL CONFIG ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="wide")

# --- 2. FIREBASE BRIDGE (Auto-Fix Included) ---
if not firebase_admin._apps:
    try:
        raw_key = st.secrets["FIREBASE_SERVICE_ACCOUNT"]["private_key"]
        fixed_key = raw_key.replace("\\n", "\n")
        
        cred_info = {
            "type": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["type"],
            "project_id": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"],
            "private_key_id": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["private_key_id"],
            "private_key": fixed_key,
            "client_email": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["client_email"],
            "client_id": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["client_id"],
            "auth_uri": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["auth_uri"],
            "token_uri": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["client_x509_cert_url"],
            "universe_domain": "googleapis.com"
        }
        cred = credentials.Certificate(cred_info)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

db = firestore.client()

# --- 3. SESSION STATE ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = "suman_naskar_admin" 

if 'current_data' not in st.session_state:
    st.session_state.current_data = None

# --- 4. ENGINES ---
try:
    geocoder = OpenCageGeocode(st.secrets["OPENCAGE_API_KEY"])
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.warning("⚠️ Checking API Keys...")

# --- 5. ASTROLOGY ENGINE (FIXED FOR VEDIC LAGNA) ---

def get_gana_yoni(nak):
    data = {"Ashwini": ("Deva", "Horse"), "Bharani": ("Manushya", "Elephant"), "Krittika": ("Rakshasa", "Goat"), "Rohini": ("Manushya", "Snake"), "Mrigashira": ("Deva", "Snake"), "Ardra": ("Manushya", "Dog"), "Punarvasu": ("Deva", "Cat"), "Pushya": ("Deva", "Goat"), "Ashlesha": ("Rakshasa", "Cat"), "Magha": ("Rakshasa", "Rat"), "Purva Phalguni": ("Manushya", "Rat"), "Uttara Phalguni": ("Manushya", "Cow"), "Hasta": ("Deva", "Buffalo"), "Chitra": ("Rakshasa", "Tiger"), "Swati": ("Deva", "Buffalo"), "Vishakha": ("Rakshasa", "Tiger"), "Anuradha": ("Deva", "Deer"), "Jyeshtha": ("Rakshasa", "Deer"), "Mula": ("Rakshasa", "Dog"), "Purva Ashadha": ("Manushya", "Monkey"), "Uttara Ashadha": ("Manushya", "Mongoose"), "Shravana": ("Deva", "Monkey"), "Dhanishta": ("Rakshasa", "Lion"), "Shatabhisha": ("Rakshasa", "Horse"), "Purva Bhadrapada": ("Manushya", "Lion"), "Uttara Bhadrapada": ("Manushya", "Cow"), "Revati": ("Deva", "Elephant")}
    return data.get(nak, ("Unknown", "Unknown"))

def calculate_vedic_chart(name, gender, dt, tm, lat, lon, city):
    # Set Sidereal Mode (Lahiri)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    # Convert Time to UTC
    local_dt = datetime.datetime.combine(dt, tm)
    utc_dt = local_dt - datetime.timedelta(hours=5, minutes=30) 
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    # --- THE VEDIC LAGNA FIX ---
    # 1. Get the Ayanamsa (The difference between Western & Vedic)
    ayanamsa = swe.get_ayanamsa_ut(jd)
    
    # 2. Calculate Houses (Standard usually returns Tropical)
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    asc_tropical = ascmc[0]
    
    # 3. Manually subtract Ayanamsa to force it to Vedic
    asc_sidereal = (asc_tropical - ayanamsa) % 360
    
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lagna_sign = zodiac[int(asc_sidereal // 30)]
    
    # --- PLANETS (Use Sidereal Flag) ---
    # Note: 64*1024 is the flag for Sidereal calculations in Swiss Ephemeris
    SIDEREAL_FLAG = 64 * 1024 
    
    planet_map = {"Sun": 0, "Moon": 1, "Mars": 4, "Mercury": 2, "Jupiter": 5, "Venus": 3, "Saturn": 6, "Rahu": 11}
    results = []
    user_rashi, user_nak = "", ""
    nak_list = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

    for p, pid in planet_map.items():
        # Calculate planet position with Sidereal Flag
        pos = swe.calc_ut(jd, pid, SIDEREAL_FLAG)[0][0]
        sign = zodiac[int(pos // 30)]
        degree = pos % 30
        nak = nak_list[int(pos / (360/27))]
        
        results.append(f"{p}: {sign} ({degree:.2f}°) | {nak}")
        
        if p == "Moon":
            user_rashi = sign
            user_nak = nak
            
    gana, yoni = get_gana_yoni(user_nak)
    
    return {
        "Name": name, "Gender": gender, 
        "Lagna": lagna_sign, # Now correctly shifted!
        "Rashi": user_rashi, "Nakshatra": user_nak, 
        "Gana": gana, "Yoni": yoni, "City": city, 
        "Full_Chart": "\n".join(results)
    }

# --- 6. SIDEBAR: UI ---
with st.sidebar:
    st.header("✨ Create Profile")
    n_in = st.text_input("Full Name")
    g_in = st.selectbox("Gender", ["Male", "Female"])
    d_in = st.date_input("Date of Birth", value=datetime.date(1993, 4, 23), min_value=datetime.date(1900, 1, 1), format="DD/MM/YYYY")
    
    c1, c2 = st.columns(2)
    with c1: hr_in = st.selectbox("Hour (24h)", range(24), index=15)
    with c2: mn_in = st.selectbox("Minute", range(60), index=45)
    
    city_in = st.text_input("Birth City", value="Kolkata, India", help="Type any city name")

    if st.button("🔮 Generate Kundali"):
        with st.spinner("Aligning Stars..."):
            res = geocoder.geocode(city_in)
            if res:
                lat = res[0]['geometry']['lat']
                lng = res[0]['geometry']['lng']
                formatted_city = res[0]['formatted']
                
                chart = calculate_vedic_chart(n_in, g_in, d_in, datetime.time(hr_in, mn_in), lat, lng, formatted_city)
                
                # Save to Firebase
                try:
                    user_ref = db.collection("users").document(st.session_state.user_id).collection("profiles")
                    user_ref.document(n_in).set(chart)
                except Exception as e:
                    st.warning(f"Cloud Save Issue: {e}")
                
                st.session_state.current_data = chart
                st.rerun()
            else:
                st.error("City not found. Check spelling.")

    st.divider()
    st.subheader("📂 Saved Profiles")
    try:
        user_ref = db.collection("users").document(st.session_state.user_id).collection("profiles")
        docs = user_ref.stream()
        profiles = [doc.to_dict() for doc in docs]
    except:
        profiles = []

    if profiles:
        selected = st.selectbox("Load Profile", [p['Name'] for p in profiles])
        if st.button("Load"):
            st.session_state.current_data = next(p for p in profiles if p['Name'] == selected)

# --- 7. MAIN DASHBOARD ---
st.title("☸️ TaraVaani")

if st.session_state.get('current_data'):
    d = st.session_state.current_data
    st.success(f"Janma Kundali: {d['Name']} 🙏")
    
    cols = st.columns(5)
    cols[0].metric("Lagna (Ascendant)", d['Lagna'])
    cols[1].metric("Rashi (Moon Sign)", d['Rashi'])
    cols[2].metric("Nakshatra", d['Nakshatra'])
    cols[3].metric("Gana", d['Gana'])
    cols[4].metric("Yoni", d['Yoni'])
    
    st.divider()
    st.subheader("📜 Graha Spashta (Planetary Degrees)")
    st.code(d['Full_Chart'], language="text")
else:
    st.info("👈 Please enter birth details in the sidebar to generate a Kundali.")
