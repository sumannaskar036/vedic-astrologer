import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from opencage.geocoder import OpenCageGeocode
import json

# --- 1. GLOBAL CONFIG (Must be first) ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="wide")

# --- 2. HARDENED FIREBASE BRIDGE (With Auto-Fix) ---
if not firebase_admin._apps:
    try:
        # Retrieve the key from secrets
        raw_key = st.secrets["FIREBASE_SERVICE_ACCOUNT"]["private_key"]
        
        # --- THE FIX: Automatically convert literal \n to actual newlines ---
        fixed_key = raw_key.replace("\\n", "\n")
        
        cred_info = {
            "type": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["type"],
            "project_id": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"],
            "private_key_id": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["private_key_id"],
            "private_key": fixed_key, # Use the fixed key here
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
        st.success("✅ Connected to Cloud Vault!") # Visual confirmation
        
    except Exception as e:
        st.error(f"Firebase Bridge Failure: {e}")
        st.stop() # Stop the app gracefully if connection fails

# Initialize Firestore Client
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

# --- 5. ASTROLOGY ENGINE (Pure Vedic) ---

def get_gana_yoni(nak):
    data = {"Ashwini": ("Deva", "Horse"), "Bharani": ("Manushya", "Elephant"), "Krittika": ("Rakshasa", "Goat"), "Rohini": ("Manushya", "Snake"), "Mrigashira": ("Deva", "Snake"), "Ardra": ("Manushya", "Dog"), "Punarvasu": ("Deva", "Cat"), "Pushya": ("Deva", "Goat"), "Ashlesha": ("Rakshasa", "Cat"), "Magha": ("Rakshasa", "Rat"), "Purva Phalguni": ("Manushya", "Rat"), "Uttara Phalguni": ("Manushya", "Cow"), "Hasta": ("Deva", "Buffalo"), "Chitra": ("Rakshasa", "Tiger"), "Swati": ("Deva", "Buffalo"), "Vishakha": ("Rakshasa", "Tiger"), "Anuradha": ("Deva", "Deer"), "Jyeshtha": ("Rakshasa", "Deer"), "Mula": ("Rakshasa", "Dog"), "Purva Ashadha": ("Manushya", "Monkey"), "Uttara Ashadha": ("Manushya", "Mongoose"), "Shravana": ("Deva", "Monkey"), "Dhanishta": ("Rakshasa", "Lion"), "Shatabhisha": ("Rakshasa", "Horse"), "Purva Bhadrapada": ("Manushya", "Lion"), "Uttara Bhadrapada": ("Manushya", "Cow"), "Revati": ("Deva", "Elephant")}
    return data.get(nak, ("Unknown", "Unknown"))

def calculate_vedic_chart(name, gender, dt, tm, lat, lon, city):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    local_dt = datetime.datetime.combine(dt, tm)
    utc_dt = local_dt - datetime.timedelta(hours=5, minutes=30) 
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    # MANUAL AYANAMSA SHIFT (Guarantees Capricorn Lagna for 1969)
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    asc_sidereal = (ascmc[0] - ayanamsa) % 360
    
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lagna_sign = zodiac[int(asc_sidereal // 30)]
    
    SIDEREAL_FLAG = 64 * 1024
    planet_map = {"Sun": 0, "Moon": 1, "Mars": 4, "Mercury": 2, "Jupiter": 5, "Venus": 3, "Saturn": 6, "Rahu": 11}
    results = []
    user_rashi, user_nak = "", ""
    nak_list = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

    for p, pid in planet_map.items():
        pos = swe.calc_ut(jd, pid, SIDEREAL_FLAG)[0][0]
        sign = zodiac[int(pos // 30)]
        nak = nak_list[int(pos / (360/27))]
        results.append(f"{p}: {sign} | {nak}")
        if p == "Moon": user_rashi, user_nak = sign, nak
            
    gana, yoni = get_gana_yoni(user_nak)
    return {"Name": name, "Gender": gender, "Lagna": lagna_sign, "Rashi": user_rashi, "Nakshatra": user_nak, "Gana": gana, "Yoni": yoni, "City": city, "Full_Chart": "\n".join(results)}

# --- 6. SIDEBAR: SaaS STORAGE ---
with st.sidebar:
    st.header("👤 Cloud Vault")
    
    # Fetch ONLY this user's profiles
    # We use a try-block here in case the database is empty initially
    try:
        user_profiles_ref = db.collection("users").document(st.session_state.user_id).collection("profiles")
        docs = user_profiles_ref.stream()
        profiles = [doc.to_dict() for doc in docs]
    except Exception as e:
        profiles = []
        st.warning("Database syncing...")
    
    if profiles:
        selected = st.selectbox("Load Profile", [p['Name'] for p in profiles])
        if st.button("Activate"):
            st.session_state.current_data = next(p for p in profiles if p['Name'] == selected)

    st.divider()
    n_in = st.text_input("Full Name")
    g_in = st.selectbox("Gender", ["Male", "Female"])
    d_in = st.date_input("DOB", value=datetime.date(1993, 4, 23), format="DD/MM/YYYY")
    hr_in = st.selectbox("Hour", range(24), index=15)
    mn_in = st.selectbox("Min", range(60), index=45)
    city_in = st.text_input("City", "Kolkata, India")
    
    if st.button("✨ Save Forever"):
        with st.spinner("Connecting to stars..."):
            res = geocoder.geocode(city_in)
            if res:
                chart = calculate_vedic_chart(n_in, g_in, d_in, datetime.time(hr_in, mn_in), res[0]['geometry']['lat'], res[0]['geometry']['lng'], city_in)
                # Save to specific User ID Silo
                user_profiles_ref.document(n_in).set(chart)
                st.session_state.current_data = chart
                st.rerun()

# --- 7. MAIN UI ---
st.title("☸️ TaraVaani")

# Connection Status Indicator
if firebase_admin._apps:
    st.caption("🟢 System Online: Cloud Database Connected")

if st.session_state.get('current_data'):
    d = st.session_state.current_data
    st.success(f"Viewing: {d['Name']} 🙏")
    
    cols = st.columns(5)
    for i, field in enumerate(["Lagna", "Rashi", "Nakshatra", "Gana", "Yoni"]):
        cols[i].metric(field, d[field])
    
    st.divider()
    st.subheader("📜 Planetary Positions")
    st.text(d['Full_Chart'])
else:
    st.info("👈 Profiles saved here stay in your account forever!")
