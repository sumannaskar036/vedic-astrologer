import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from opencage.geocoder import OpenCageGeocode

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TaraVaani Chat", page_icon="☸️", layout="wide")

# Clean, Minimal Dark Theme
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    .stChatInput { position: fixed; bottom: 0; padding-bottom: 20px; }
    /* Hide default menu */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. SETUP BACKEND ---
# Firebase
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

# AI & Geocoding
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except: pass
try:
    geocoder = OpenCageGeocode(st.secrets["OPENCAGE_API_KEY"])
except: pass

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Namaste! I am TaraVaani. Please enter your birth details in the sidebar so I can read your chart."}]
if "chart_context" not in st.session_state: st.session_state.chart_context = None

# --- 4. CALCULATION ENGINE ---
def calculate_chart(name, dt, tm, city):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    try:
        res = geocoder.geocode(city)
        lat, lng = res[0]['geometry']['lat'], res[0]['geometry']['lng']
    except: lat, lng = 28.61, 77.20 # Default Delhi
    
    birth_dt = datetime.datetime.combine(dt, tm)
    # Convert to UTC (Assuming Input is IST for simplicity, or handle TZ)
    utc_dt = birth_dt - datetime.timedelta(hours=5, minutes=30)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    # Planets
    planet_map = {0:"Sun", 1:"Moon", 4:"Mars", 2:"Mercury", 5:"Jupiter", 3:"Venus", 6:"Saturn", 11:"Rahu"}
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    
    # Lagna
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lng, b'P')
    asc_deg = (ascmc[0] - ayanamsa) % 360
    lagna = zodiac[int(asc_deg // 30)]
    
    chart_data = f"Name: {name}\nBirth: {dt} {tm}\nCity: {city}\nLagna (Ascendant): {lagna}\n"
    
    for pid, pname in planet_map.items():
        try:
            pos = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL | swe.FLG_MOSEPH)[0][0]
            sign = zodiac[int(pos // 30) % 12]
            deg = pos % 30
            chart_data += f"{pname}: {sign} ({deg:.2f}°)\n"
        except: pass
        
    return chart_data

# --- 5. SIDEBAR (INPUTS) ---
with st.sidebar:
    st.header("📝 Birth Details")
    name = st.text_input("Name")
    dob = st.date_input("Date of Birth", value=datetime.date(1995,1,1), min_value=datetime.date(1900,1,1), max_value=datetime.date(2100,12,31))
    t_time = st.time_input("Time of Birth", value=datetime.time(10,30))
    city = st.text_input("City", "New Delhi, India")
    
    if st.button("Generate Kundali", type="primary"):
        with st.spinner("Calculating Planetary Positions..."):
            chart_text = calculate_chart(name, dob, t_time, city)
            st.session_state.chart_context = chart_text
            st.session_state.messages.append({"role": "assistant", "content": f"I have generated the chart for **{name}**. You can now ask me anything about your career, marriage, or health!"})
            st.success("Chart Ready!")

# --- 6. MAIN CHAT INTERFACE ---
st.title("☸️ TaraVaani Chat")

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat Input & Logic
if prompt := st.chat_input("Ask about your future..."):
    # 1. Show User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate AI Response
    with st.chat_message("assistant"):
        if st.session_state.chart_context:
            try:
                # Construct the Prompt
                full_prompt = f"""
                You are TaraVaani, an expert Vedic Astrologer. 
                Here is the user's birth chart details:
                {st.session_state.chart_context}
                
                User Question: {prompt}
                
                Answer based strictly on Vedic Astrology principles. Be helpful, mystical but practical. Keep it under 200 words.
                """
                
                # Call Gemini
                response = model.generate_content(full_prompt)
                bot_reply = response.text
                
                st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            
            except Exception as e:
                st.error(f"AI Connection Error: {str(e)}")
                st.info("Check if your GEMINI_API_KEY is correct in Streamlit Secrets.")
        else:
            st.warning("Please generate your Kundali in the sidebar first!")
