import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import time
from geopy.geocoders import Nominatim # For location search

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="TaraVaani", 
    page_icon="☸️", 
    layout="centered"
)

# Initialize Geocoder
geolocator = Nominatim(user_agent="taravaani_app")

# --- SECURITY: Get Key ---
try:
    SERVER_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("Secrets not found. Please set GEMINI_API_KEY in Streamlit Cloud.")
    st.stop()

# --- 2. ASTROLOGY ENGINE ---
def get_gana_yoni(nakshatra_name):
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
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    local_dt = datetime.datetime.combine(dt, tm)
    # Standard Indian Offset. Future fix: Use timezone library for global cities.
    utc_dt = local_dt - datetime.timedelta(hours=5, minutes=30) 
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    asc_vedic = (ascmc[0] - swe.get_ayanamsa_ut(jd)) % 360
    
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    nakshatras = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
                  "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
                  "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
                  "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
                  "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    
    lagna_sign = zodiac[int(asc_vedic // 30)]
    planet_map = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
        "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, 
        "Rahu": swe.MEAN_NODE, "Ketu": swe.MEAN_NODE
    }
    
    results = []
    user_rashi = ""
    user_nak = ""
    for p, pid in planet_map.items():
        if p == "Ketu": 
            pos_rahu = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SIDEREAL)[0][0]
            pos = (pos_rahu + 180) % 360
        else:
            pos = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]
        sign = zodiac[int(pos // 30)]
        nak = nakshatras[int(pos / (360/27))]
        degree = pos % 30
        results.append(f"{p}: {sign} ({degree:.2f}°) | {nak}")
        if p == "Moon":
            user_rashi = sign
            user_nak = nak
            
    gana, yoni = get_gana_yoni(user_nak)
    return {
        "Name": name, "Gender": gender, "Lagna": lagna_sign, "Rashi": user_rashi,
        "Nakshatra": user_nak, "Gana": gana, "Yoni": yoni, "City": city,
        "Full_Chart": "\n".join(results)
    }

def get_ai_response(user_data, question, lang):
    genai.configure(api_key=SERVER_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f'''
    You are "TaraVaani", a wise Vedic Astrologer.
    CONTEXT: {user_data['Gender']} born in {user_data['City']}.
    USER: {user_data['Name']}
    CHART: {user_data['Full_Chart']}
    DETAILS: Rashi={user_data['Rashi']}, Lagna={user_data['Lagna']}, Nakshatra={user_data['Nakshatra']}, Gana={user_data['Gana']}, Yoni={user_data['Yoni']}
    
    Question: {question}
    Language: {lang}
    
    Answer concisely (max 120 words) with empathy. Use gender-appropriate Vedic terms. 
    Start with "Namaste {user_data['Name']} 🙏".
    '''
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        time.sleep(1)
        try:
            response = model.generate_content(prompt)
            return response.text
        except:
            return "The stars are currently obscured. Please try again in a moment. 🙏"

# --- 3. STATE MANAGEMENT ---
if 'app_state' not in st.session_state:
    st.session_state.app_state = {'generated': False, 'data': None}
if 'messages' not in st.session_state:
    st.session_state.messages = []

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("👤 Birth Details")
    name = st.text_input("Name", "Suman", key="input_name")
    gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="input_gender")
    
    # Range: 1900 to present
    dob = st.date_input(
        "Date of Birth", 
        value=datetime.date(1993, 4, 23), 
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date.today(),
        format="DD/MM/YYYY", 
        key="input_dob"
    )
    
    c1, c2 = st.columns(2)
    with c1: hour = st.selectbox("Hour", range(0, 24), index=15)
    with c2: minute = st.selectbox("Minute", range(0, 60), index=45)
    tob = datetime.time(hour, minute)
    
    city_input = st.text_input("Birth City", "Kolkata, India", help="Enter City and Country for accuracy")
    lang = st.selectbox("Language", ["English", "Hindi", "Bengali"], key="input_lang")
    
    if st.button("✨ Generate My Destiny", type="primary"):
        with st.spinner("Locating birth stars..."):
            try:
                location = geolocator.geocode(city_input)
                if location:
                    chart_data = calculate_vedic_chart(name, gender, dob, tob, location.latitude, location.longitude, city_input)
                    st.session_state.app_state = {'generated': True, 'data': chart_data}
                    st.session_state.messages = [] 
                    st.rerun()
                else:
                    st.error("Could not find city. Please try adding the Country name.")
            except Exception as e:
                st.error(f"Error: {e}")

# --- 5. MAIN PAGE ---
st.title("☸️ TaraVaani")

if st.session_state.app_state['generated']:
    data = st.session_state.app_state['data']
    st.success(f"Radhe Radhe! Chart calculated for {data['Name']} in {data['City']} 🙏")
    
    st.markdown(f"""
    | **Lagna** | **Rashi** | **Nakshatra** | **Gana** | **Yoni** |
    | :--- | :--- | :--- | :--- | :--- |
    | {data['Lagna']} | {data['Rashi']} | {data['Nakshatra']} | {data['Gana']} | {data['Yoni']} |
    """)
    st.markdown("---") 

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(f"Ask TaraVaani in {lang}..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Consulting the stars..."):
                reply = get_ai_response(data, prompt, lang)
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
else:
    st.info("👈 Enter your birth details in the sidebar and click 'Generate My Destiny' to start.")
