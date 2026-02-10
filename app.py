import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import time
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter # For reliable cloud connections

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="centered")

# --- 2. THE RELIABLE GEOCODER ---
# Using a unique name and longer timeout to prevent "Connection Refused"
try:
    geolocator = Nominatim(user_agent="taravaani_exclusive_astro_2026", timeout=10)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
except Exception as e:
    st.error(f"Geocoder Init Error: {e}")

# --- SECURITY: Get Paid Tier Key ---
try:
    SERVER_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=SERVER_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Secrets not found. Ensure GEMINI_API_KEY is in Streamlit Cloud Settings.")
    st.stop()

# --- 3. ASTROLOGY ENGINE (Functions) ---
def get_gana_yoni(nakshatra_name):
    # (Data stays the same as your previous working code)
    data = {"Ashwini": ("Deva", "Horse"), "Bharani": ("Manushya", "Elephant"), "Krittika": ("Rakshasa", "Goat"), "Rohini": ("Manushya", "Snake"), "Mrigashira": ("Deva", "Snake"), "Ardra": ("Manushya", "Dog"), "Punarvasu": ("Deva", "Cat"), "Pushya": ("Deva", "Goat"), "Ashlesha": ("Rakshasa", "Cat"), "Magha": ("Rakshasa", "Rat"), "Purva Phalguni": ("Manushya", "Rat"), "Uttara Phalguni": ("Manushya", "Cow"), "Hasta": ("Deva", "Buffalo"), "Chitra": ("Rakshasa", "Tiger"), "Swati": ("Deva", "Buffalo"), "Vishakha": ("Rakshasa", "Tiger"), "Anuradha": ("Deva", "Deer"), "Jyeshtha": ("Rakshasa", "Deer"), "Mula": ("Rakshasa", "Dog"), "Purva Ashadha": ("Manushya", "Monkey"), "Uttara Ashadha": ("Manushya", "Mongoose"), "Shravana": ("Deva", "Monkey"), "Dhanishta": ("Rakshasa", "Lion"), "Shatabhisha": ("Rakshasa", "Horse"), "Purva Bhadrapada": ("Manushya", "Lion"), "Uttara Bhadrapada": ("Manushya", "Cow"), "Revati": ("Deva", "Elephant")}
    return data.get(nakshatra_name, ("Unknown", "Unknown"))

def calculate_vedic_chart(name, gender, dt, tm, lat, lon, city):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    local_dt = datetime.datetime.combine(dt, tm)
    utc_dt = local_dt - datetime.timedelta(hours=5, minutes=30) 
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    asc_vedic = (ascmc[0] - swe.get_ayanamsa_ut(jd)) % 360
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    nakshatras = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    lagna_sign = zodiac[int(asc_vedic // 30)]
    planet_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE, "Ketu": swe.MEAN_NODE}
    results = []
    user_rashi, user_nak = "", ""
    for p, pid in planet_map.items():
        pos = (swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]) if p != "Ketu" else (swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SIDEREAL)[0][0] + 180) % 360
        sign, nak, degree = zodiac[int(pos // 30)], nakshatras[int(pos / (360/27))], pos % 30
        results.append(f"{p}: {sign} ({degree:.2f}°) | {nak}")
        if p == "Moon": user_rashi, user_nak = sign, nak
    gana, yoni = get_gana_yoni(user_nak)
    return {"Name": name, "Gender": gender, "Lagna": lagna_sign, "Rashi": user_rashi, "Nakshatra": user_nak, "Gana": gana, "Yoni": yoni, "City": city, "Full_Chart": "\n".join(results)}

# --- 4. SIDEBAR (With Date & Location Fix) ---
with st.sidebar:
    st.header("👤 Birth Details")
    name = st.text_input("Name", "Suman")
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    dob = st.date_input("Date of Birth", value=datetime.date(1993, 4, 23), min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today())
    c1, c2 = st.columns(2)
    with c1: hour = st.selectbox("Hour", range(0, 24), index=15)
    with c2: minute = st.selectbox("Minute", range(0, 60), index=45)
    tob = datetime.time(hour, minute)
    city_input = st.text_input("Birth City", "Kolkata, India")
    lang = st.selectbox("Language", ["English", "Hindi", "Bengali"])
    
    if st.button("✨ Generate My Destiny", type="primary"):
        with st.spinner("Connecting to stars..."):
            try:
                location = geolocator.geocode(city_input)
                if location:
                    chart_data = calculate_vedic_chart(name, gender, dob, tob, location.latitude, location.longitude, city_input)
                    st.session_state.app_state = {'generated': True, 'data': chart_data}
                    st.session_state.messages = [] 
                    st.rerun()
                else:
                    st.error("City not found. Add country name (e.g. 'Paris, France')")
            except Exception as e:
                st.error(f"Connection Error: {e}. Try again in 5 seconds.")

# --- 5. MAIN UI (Chat) ---
st.title("☸️ TaraVaani")
if st.session_state.get('app_state', {}).get('generated'):
    data = st.session_state.app_state['data']
    st.success(f"Radhe Radhe! {data['Name']}'s chart from {data['City']} is ready. 🙏")
    st.markdown(f"| **Lagna** | **Rashi** | **Nakshatra** | **Gana** | **Yoni** |\n| :--- | :--- | :--- | :--- | :--- |\n| {data['Lagna']} | {data['Rashi']} | {data['Nakshatra']} | {data['Gana']} | {data['Yoni']} |")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about your career, health or love..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Consulting..."):
                # Use your existing get_ai_response logic here
                st.markdown("Consulting the Stars...") 
else:
    st.info("👈 Enter your birth details to unlock your Vedic journey.")
