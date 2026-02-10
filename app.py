import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from opencage.geocoder import OpenCageGeocode

# --- 1. FIREBASE AUTH & DATABASE BRIDGE ---
if not firebase_admin._apps:
    try:
        # Securely links your app to the Firebase Cloud
        fb_creds = dict(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase Bridge Failure: {e}")

db = firestore.client()

# --- 2. SaaS GLOBAL CONFIG ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="wide")

# This is your current "Development" user ID.
# When you add a login page, this will become dynamic.
if 'user_id' not in st.session_state:
    st.session_state.user_id = "suman_naskar_admin" 

# --- 3. ENGINES (Paid Gemini + OpenCage) ---
try:
    geocoder = OpenCageGeocode(st.secrets["OPENCAGE_API_KEY"])
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Check your Gemini/OpenCage API keys in Secrets!")

# --- 4. ASTROLOGY ENGINE (Pure Vedic Accuracy) ---

def get_gana_yoni(nak):
    data = {"Ashwini": ("Deva", "Horse"), "Bharani": ("Manushya", "Elephant"), "Krittika": ("Rakshasa", "Goat"), "Rohini": ("Manushya", "Snake"), "Mrigashira": ("Deva", "Snake"), "Ardra": ("Manushya", "Dog"), "Punarvasu": ("Deva", "Cat"), "Pushya": ("Deva", "Goat"), "Ashlesha": ("Rakshasa", "Cat"), "Magha": ("Rakshasa", "Rat"), "Purva Phalguni": ("Manushya", "Rat"), "Uttara Phalguni": ("Manushya", "Cow"), "Hasta": ("Deva", "Buffalo"), "Chitra": ("Rakshasa", "Tiger"), "Swati": ("Deva", "Buffalo"), "Vishakha": ("Rakshasa", "Tiger"), "Anuradha": ("Deva", "Deer"), "Jyeshtha": ("Rakshasa", "Deer"), "Mula": ("Rakshasa", "Dog"), "Purva Ashadha": ("Manushya", "Monkey"), "Uttara Ashadha": ("Manushya", "Mongoose"), "Shravana": ("Deva", "Monkey"), "Dhanishta": ("Rakshasa", "Lion"), "Shatabhisha": ("Rakshasa", "Horse"), "Purva Bhadrapada": ("Manushya", "Lion"), "Uttara Bhadrapada": ("Manushya", "Cow"), "Revati": ("Deva", "Elephant")}
    return data.get(nak, ("Unknown", "Unknown"))

def calculate_vedic_chart(name, gender, dt, tm, lat, lon, city):
    # Ensures 1969 chart correctly shows Capricorn Lagna
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    local_dt = datetime.datetime.combine(dt, tm)
    utc_dt = local_dt - datetime.timedelta(hours=5, minutes=30) 
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    # MANUAL AYANAMSA SHIFT (Vedic Accuracy Guarantee)
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

# --- 5. SIDEBAR: SaaS STORAGE LOGIC ---
with st.sidebar:
    st.header("👤 Your Account Vault")
    # Multi-user Silos: Fetch only this user's profiles
    user_profiles_ref = db.collection("users").document(st.session_state.user_id).collection("profiles")
    docs = user_profiles_ref.stream()
    profiles = [doc.to_dict() for doc in docs]
    
    if profiles:
        selected = st.selectbox("Switch Saved Member", [p['Name'] for p in profiles])
        if st.button("Load"):
            st.session_state.current_data = next(p for p in profiles if p['Name'] == selected)

    st.divider()
    n_in = st.text_input("Full Name")
    g_in = st.selectbox("Gender", ["Male", "Female"])
    d_in = st.date_input("DOB", value=datetime.date(1993, 4, 23), format="DD/MM/YYYY")
    hr_in = st.selectbox("Hour", range(24), index=15)
    mn_in = st.selectbox("Min", range(60), index=45)
    city_in = st.text_input("City", "Kolkata, India")
    
    if st.button("✨ Save to Cloud"):
        with st.spinner("Calculating destiny..."):
            coords = geocoder.geocode(city_in)
            if coords:
                chart = calculate_vedic_chart(n_in, g_in, d_in, datetime.time(hr_in, mn_in), coords[0]['geometry']['lat'], coords[0]['geometry']['lng'], city_in)
                # Save PERMANENTLY for THIS User
                user_profiles_ref.document(n_in).set(chart)
                st.session_state.current_data = chart
                st.rerun()

# --- 6. MAIN UI ---
st.title("☸️ TaraVaani")
if st.session_state.get('current_data'):
    d = st.session_state.current_data
    st.success(f"Active Profile: {d['Name']} 🙏")
    
    cols = st.columns(5)
    for i, field in enumerate(["Lagna", "Rashi", "Nakshatra", "Gana", "Yoni"]):
        cols[i].metric(field, d[field])
    
    st.divider()
    st.subheader("📜 Planetary Positions")
    st.text(d['Full_Chart'])
else:
    st.info("👈 Your commercial users can manage their saved profiles here.")
