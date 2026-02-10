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
        st.error(f"Database Error: {e}")
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

# --- 5. ASTROLOGY ENGINE (Topocentric Fix) ---
def get_gana_yoni(nak):
    data = {"Ashwini": ("Deva", "Horse"), "Bharani": ("Manushya", "Elephant"), "Krittika": ("Rakshasa", "Goat"), "Rohini": ("Manushya", "Snake"), "Mrigashira": ("Deva", "Snake"), "Ardra": ("Manushya", "Dog"), "Punarvasu": ("Deva", "Cat"), "Pushya": ("Deva", "Goat"), "Ashlesha": ("Rakshasa", "Cat"), "Magha": ("Rakshasa", "Rat"), "Purva Phalguni": ("Manushya", "Rat"), "Uttara Phalguni": ("Manushya", "Cow"), "Hasta": ("Deva", "Buffalo"), "Chitra": ("Rakshasa", "Tiger"), "Swati": ("Deva", "Buffalo"), "Vishakha": ("Rakshasa", "Tiger"), "Anuradha": ("Deva", "Deer"), "Jyeshtha": ("Rakshasa", "Deer"), "Mula": ("Rakshasa", "Dog"), "Purva Ashadha": ("Manushya", "Monkey"), "Uttara Ashadha": ("Manushya", "Mongoose"), "Shravana": ("Deva", "Monkey"), "Dhanishta": ("Rakshasa", "Lion"), "Shatabhisha": ("Rakshasa", "Horse"), "Purva Bhadrapada": ("Manushya", "Lion"), "Uttara Bhadrapada": ("Manushya", "Cow"), "Revati": ("Deva", "Elephant")}
    return data.get(nak, ("Unknown", "Unknown"))

def calculate_vedic_chart(name, gender, dt, tm, lat, lon, city, time_adj_mins=0):
    # 1. Set Ayanamsa (Lahiri)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    # 2. FORCE TOPOCENTRIC CALCULATION (Fixes the Cusp Issue)
    # This accounts for the observer being on the SURFACE of Kolkata, not Earth's center.
    swe.set_topo(lon, lat, 0) 
    
    # 3. Time Processing
    birth_dt = datetime.datetime.combine(dt, tm)
    adjusted_dt = birth_dt + datetime.timedelta(minutes=time_adj_mins)
    
    # IST to UTC (-5:30)
    utc_dt = adjusted_dt - datetime.timedelta(hours=5, minutes=30)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    # 4. Math
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    asc_deg = (ascmc[0] - ayanamsa) % 360
    
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lagna_sign = zodiac[int(asc_deg // 30)]
    lagna_val = asc_deg % 30
    
    planet_map = {"Sun": 0, "Moon": 1, "Mars": 4, "Mercury": 2, "Jupiter": 5, "Venus": 3, "Saturn": 6, "Rahu": 11}
    results = []
    user_rashi, user_nak = "", ""
    nak_list = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

    SIDEREAL_FLAG = 64 * 1024
    for p, pid in planet_map.items():
        try:
            pos = swe.calc_ut(jd, pid, SIDEREAL_FLAG)[0][0]
            sign = zodiac[int(pos // 30) % 12]
            deg = pos % 30
            nak_idx = int(pos / (360/27)) % 27
            nak = nak_list[nak_idx]
            results.append(f"{p}: {sign} ({deg:.2f}°) | {nak}")
            if p == "Moon": user_rashi, user_nak = sign, nak
        except:
            results.append(f"{p}: Error")
            
    gana, yoni = get_gana_yoni(user_nak)
    
    return {
        "Name": name, "Gender": gender,
        "Lagna": lagna_sign, "Lagna_Deg": f"{lagna_val:.2f}",
        "Rashi": user_rashi, "Nakshatra": user_nak,
        "Gana": gana, "Yoni": yoni, "City": city,
        "Full_Chart": "\n".join(results)
    }

# --- 6. SIDEBAR ---
with st.sidebar:
    st.header("✨ Create Profile")
    n_in = st.text_input("Full Name")
    g_in = st.selectbox("Gender", ["Male", "Female"])
    d_in = st.date_input("Date of Birth", value=datetime.date(1969, 3, 16), min_value=datetime.date(1900, 1, 1), format="DD/MM/YYYY")
    
    c1, c2 = st.columns(2)
    with c1: hr_in = st.selectbox("Hour (24h)", range(24), index=4)
    with c2: mn_in = st.selectbox("Minute", range(60), index=30)
    
    city_in = st.text_input("Birth City", value="Kolkata, India", help="Type exact city name")

    st.divider()
    
    # --- PRO FEATURE: Advanced Accuracy ---
    with st.expander("🛠️ Advanced Accuracy"):
        st.caption("If your Lagna seems off, adjust this slider slightly.")
        time_adj = st.slider("Fine-tune Time (Minutes)", -10, 10, 0)

    if st.button("🔮 Generate Kundali"):
        with st.spinner("Aligning Stars..."):
            res = geocoder.geocode(city_in)
            if res:
                lat = res[0]['geometry']['lat']
                lng = res[0]['geometry']['lng']
                formatted_city = res[0]['formatted']
                
                chart = calculate_vedic_chart(n_in, g_in, d_in, datetime.time(hr_in, mn_in), lat, lng, formatted_city, time_adj)
                
                try:
                    user_ref = db.collection("users").document(st.session_state.user_id).collection("profiles")
                    user_ref.document(n_in).set(chart)
                except: pass
                
                st.session_state.current_data = chart
                st.rerun()
            else:
                st.error("City not found.")

    st.divider()
    st.subheader("📂 Saved Profiles")
    try:
        user_ref = db.collection("users").document(st.session_state.user_id).collection("profiles")
        profiles = [doc.to_dict() for doc in user_ref.stream()]
    except: profiles = []

    if profiles:
        selected_prof = st.selectbox("Load Profile", [p['Name'] for p in profiles])
        if st.button("Load"):
            found = next((p for p in profiles if p['Name'] == selected_prof), None)
            if found: st.session_state.current_data = found

# --- 7. UI ---
st.title("☸️ TaraVaani")

if st.session_state.get('current_data'):
    d = st.session_state.current_data
    st.success(f"Janma Kundali: {d['Name']} 🙏")
    
    cols = st.columns(5)
    cols[0].metric("Lagna", f"{d['Lagna']} ({d.get('Lagna_Deg', '')}°)")
    cols[1].metric("Rashi", d['Rashi'])
    cols[2].metric("Nakshatra", d['Nakshatra'])
    cols[3].metric("Gana", d['Gana'])
    cols[4].metric("Yoni", d['Yoni'])
    
    st.divider()
    st.subheader("📜 Planetary Degrees")
    st.code(d['Full_Chart'], language="text")
else:
    st.info("👈 Please enter birth details in the sidebar.")
