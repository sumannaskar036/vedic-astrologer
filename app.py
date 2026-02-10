import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from opencage.geocoder import OpenCageGeocode

# --- 1. CONFIG ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="wide")

# --- 2. FIREBASE BRIDGE ---
# This block handles the connection to your database.
if not firebase_admin._apps:
    try:
        # We fix the private key format which often gets broken in copy-pasting
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
        st.error(f"Database Connection Error: {e}")
        st.stop()

db = firestore.client()

# --- 3. SESSION STATE ---
if 'user_id' not in st.session_state: st.session_state.user_id = "suman_naskar_admin" 
if 'current_data' not in st.session_state: st.session_state.current_data = None

# --- 4. API ENGINES ---
try:
    geocoder = OpenCageGeocode(st.secrets["OPENCAGE_API_KEY"])
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.warning("⚠️ Checking API Keys...")

# --- 5. ASTROLOGY ENGINE (Stable Lahiri) ---
def get_gana_yoni(nak):
    data = {"Ashwini": ("Deva", "Horse"), "Bharani": ("Manushya", "Elephant"), "Krittika": ("Rakshasa", "Goat"), "Rohini": ("Manushya", "Snake"), "Mrigashira": ("Deva", "Snake"), "Ardra": ("Manushya", "Dog"), "Punarvasu": ("Deva", "Cat"), "Pushya": ("Deva", "Goat"), "Ashlesha": ("Rakshasa", "Cat"), "Magha": ("Rakshasa", "Rat"), "Purva Phalguni": ("Manushya", "Rat"), "Uttara Phalguni": ("Manushya", "Cow"), "Hasta": ("Deva", "Buffalo"), "Chitra": ("Rakshasa", "Tiger"), "Swati": ("Deva", "Buffalo"), "Vishakha": ("Rakshasa", "Tiger"), "Anuradha": ("Deva", "Deer"), "Jyeshtha": ("Rakshasa", "Deer"), "Mula": ("Rakshasa", "Dog"), "Purva Ashadha": ("Manushya", "Monkey"), "Uttara Ashadha": ("Manushya", "Mongoose"), "Shravana": ("Deva", "Monkey"), "Dhanishta": ("Rakshasa", "Lion"), "Shatabhisha": ("Rakshasa", "Horse"), "Purva Bhadrapada": ("Manushya", "Lion"), "Uttara Bhadrapada": ("Manushya", "Cow"), "Revati": ("Deva", "Elephant")}
    return data.get(nak, ("Unknown", "Unknown"))

def calculate_vedic_chart(name, gender, dt, tm, lat, lon, city, time_correction_mins=0):
    # 1. Initialize Swiss Ephemeris with Lahiri Ayanamsa (Standard Vedic)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    # 2. Apply Time Correction (Refinement Logic)
    # This handles the "My chart is slightly different" issue by adjusting time, not math.
    birth_datetime = datetime.datetime.combine(dt, tm)
    adjusted_datetime = birth_datetime + datetime.timedelta(minutes=time_correction_mins)
    
    # 3. Convert to UTC (Assuming IST -5:30)
    utc_dt = adjusted_datetime - datetime.timedelta(hours=5, minutes=30) 
    
    # 4. Julian Day Calculation
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    # 5. Ayanamsa
    ayanamsa = swe.get_ayanamsa_ut(jd)
    
    # 6. Ascendant (Lagna) Calculation
    cusps, ascmc = swe.houses(jd, lat, lon, b'P') 
    asc_tropical = ascmc[0] 
    asc_sidereal = (asc_tropical - ayanamsa) % 360
    
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lagna_sign = zodiac[int(asc_sidereal // 30)]
    lagna_deg = asc_sidereal % 30
    
    # 7. Planetary Positions
    SIDEREAL_FLAG = 64 * 1024 
    planet_map = {"Sun": 0, "Moon": 1, "Mars": 4, "Mercury": 2, "Jupiter": 5, "Venus": 3, "Saturn": 6, "Rahu": 11}
    results = []
    user_rashi, user_nak = "", ""
    nak_list = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushinfo("👈 Please enter birth details in the sidebar.")
