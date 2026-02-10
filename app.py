import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from opencage.geocoder import OpenCageGeocode
import time

# --- 1. CONFIGURATION & CSS ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="centered", initial_sidebar_state="collapsed")

# Custom CSS for True Mobile-First Experience
st.markdown("""
<style>
    /* 1. APP CONTAINER RESET (Crucial for Mobile Look) */
    .stApp { background-color: #121212; color: #E0E0E0; font-family: sans-serif; }
    
    /* Remove huge top padding from Streamlit */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 5rem !important; /* Space for bottom nav */
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* 2. TOP HEADER (Fixed) */
    .top-header {
        position: sticky; top: 0; z-index: 1000;
        background-color: #F8BBD0; color: #880E4F;
        margin: 0 -1rem 1rem -1rem; /* Negative margin to span full width */
        padding: 15px 20px;
        display: flex; justify-content: space-between; align-items: center;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    
    /* 3. HERO RIBBON (Side-by-Side Cards) */
    .hero-grid {
        display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;
    }
    .hero-card {
        background: linear-gradient(135deg, #D32F2F 0%, #B71C1C 100%);
        padding: 20px 10px; border-radius: 15px; text-align: center;
        color: white; box-shadow: 0 4px 10px rgba(211, 47, 47, 0.4);
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        min-height: 100px;
    }
    
    /* 4. HORIZONTAL PROFILE SCROLL */
    .profile-scroll {
        display: flex; overflow-x: auto; gap: 10px; padding: 10px 5px; margin-bottom: 15px;
        scrollbar-width: none;
    }
    .profile-scroll::-webkit-scrollbar { display: none; }
    
    /* 5. INPUT FIELDS (Mobile Friendly) */
    div[data-baseweb="input"] { background-color: #2D2D2D !important; border-radius: 10px !important; border: none; color: white; }
    div[data-baseweb="select"] > div { background-color: #2D2D2D !important; border-radius: 10px !important; }
    
    /* 6. BOTTOM NAV (Fixed Footer) */
    .bottom-nav {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #1F1F1F; border-top: 1px solid #333;
        padding: 12px 0; display: flex; justify-content: space-around; z-index: 1000;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.5);
    }
    
    /* Hide Default Elements */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* Button Styling Override */
    .stButton > button {
        border-radius: 12px; height: 3em; font-weight: bold; border: none;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SETUP ---
if not firebase_admin._apps:
    try:
        raw_key = st.secrets["FIREBASE_SERVICE_ACCOUNT"]["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate({
            "type": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["type"],
            "project_id": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"],
            "private_key_id": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["private_key_id"],
            "private_key": raw_key,
            "client_email": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["client_email"],
            "client_id": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["client_id"],
            "auth_uri": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["auth_uri"],
            "token_uri": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["client_x509_cert_url"],
            "universe_domain": "googleapis.com"
        })
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except: pass

# --- 3. SESSION STATE ---
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'onboarding_complete' not in st.session_state: st.session_state.onboarding_complete = False
if 'wallet_balance' not in st.session_state: st.session_state.wallet_balance = 0
if 'active_profile' not in st.session_state: st.session_state.active_profile = None 
if 'page_view' not in st.session_state: st.session_state.page_view = "Home"

# --- 4. ENGINE ---
def calculate_chart_data(name, gender, dt, tm, city):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    try:
        res = geocoder.geocode(city)
        lat, lng = res[0]['geometry']['lat'], res[0]['geometry']['lng']
    except: lat, lng = 28.61, 77.20 
    
    birth_dt = datetime.datetime.combine(dt, tm)
    utc_dt = birth_dt - datetime.timedelta(hours=5, minutes=30)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lng, b'P')
    asc_deg = (ascmc[0] - ayanamsa) % 360
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lagna = zodiac[int(asc_deg // 30)]
    
    moon_pos = swe.calc_ut(jd, 1, swe.FLG_SIDEREAL | swe.FLG_MOSEPH)[0][0]
    moon_sign = zodiac[int(moon_pos // 30) % 12]
    
    nak_list = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    nak_idx = int(moon_pos / (360/27)) % 27
    nakshatra = nak_list[nak_idx]
    
    planet_map = {"Sun": 0, "Moon": 1, "Mars": 4, "Mercury": 2, "Jupiter": 5, "Venus": 3, "Saturn": 6, "Rahu": 11}
    chart_text = ""
    for p, pid in planet_map.items():
        try:
            pos = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL | swe.FLG_MOSEPH)[0][0]
            sign = zodiac[int(pos // 30) % 12]
            deg = pos % 30
            chart_text += f"{p}: {sign} ({deg:.2f}°)\n"
        except: pass

    return {"Name": name, "Gender": gender, "Lagna": lagna, "Rashi": moon_sign, "Nakshatra": nakshatra, "Full_Chart": chart_text}

@st.cache_data(ttl=2) 
def get_profiles(uid):
    try:
        docs = db.collection("users").document(uid).collection("profiles").stream()
        return [doc.to_dict() for doc in docs]
    except: return []

# --- 5. LOGIC: ONBOARDING SCREEN ---
if not st.session_state.onboarding_complete:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #F8BBD0; font-family:serif;'>☸️ TaraVaani</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #AAA; margin-bottom: 30px;'>Begin your Vedic Journey</p>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div style="background-color: #1E1E1E; padding: 20px; border-radius: 15px; margin-bottom: 20px;">', unsafe_allow_html=True)
        name = st.text_input("Name")
        gender = st.selectbox("Gender", ["Male", "Female"])
        
        dob = st.date_input("Date of Birth", value=datetime.date(1995, 1, 1), min_value=datetime.date(1900, 1, 1), max_value=datetime.date(2100, 12, 31), format="DD/MM/YYYY")
        
        # MANUAL TIME INPUTS (Hour | Minute)
        st.write("Time of Birth")
        c1, c2 = st.columns(2)
        hr = c1.number_input("Hour (0-23)", min_value=0, max_value=23, value=10)
        mn = c2.number_input("Minute (0-59)", min_value=0, max_value=59, value=30)
        
        city = st.text_input("City", "Kolkata, India")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("Create Profile & Enter", type="primary"):
            if name:
                uid = f"{name.replace(' ', '_')}_{int(time.time())}"
                st.session_state.user_id = uid
                chart = calculate_chart_data(name, gender, dob, datetime.time(hr,
