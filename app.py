import streamlit as st
import swisseph as swe
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from opencage.geocoder import OpenCageGeocode
import requests

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="wide")

# Custom CSS for UI
st.markdown("""
<style>
    .header-box { 
        background-color: #1e3a29; 
        padding: 15px; 
        border-radius: 10px; 
        color: #90EE90; 
        font-size: 18px; 
        font-weight: bold; 
        margin-bottom: 20px; 
        text-align: center;
    }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stChatInput { position: fixed; bottom: 0; padding-bottom: 15px; z-index: 1000; background: #0E1117; }
</style>
""", unsafe_allow_html=True)

# --- 2. FIREBASE CONNECTION ---
if not firebase_admin._apps:
    try:
        raw_key = st.secrets["FIREBASE_SERVICE_ACCOUNT"]["private_key"].replace("\\n", "\n")
        cred_info = {
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
        }
        firebase_admin.initialize_app(credentials.Certificate(cred_info))
    except Exception:
        pass

db = firestore.client()

# --- 3. API SETUP ---
try:
    geocoder = OpenCageGeocode(st.secrets["OPENCAGE_API_KEY"])
except Exception:
    geocoder = None

# --- 4. SESSION STATE ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = "suman_naskar_admin"
if 'current_data' not in st.session_state:
    st.session_state.current_data = None

# --- 5. CALCULATOR ENGINE ---
def get_gana_yoni(nak):
    data = {
        "Ashwini": ("Deva", "Horse"), "Bharani": ("Manushya", "Elephant"),
        "Krittika": ("Rakshasa", "Goat"), "Rohini": ("Manushya", "Snake"),
        "Mrigashira": ("Deva", "Snake"), "Ardra": ("Manushya", "Dog"),
        "Punarvasu": ("Deva", "Cat"), "Pushya": ("Deva", "Goat"),
        "Ashlesha": ("Rakshasa", "Cat"), "Magha": ("Rakshasa", "Rat"),
        "Purva Phalguni": ("Manushya", "Rat"), "Uttara Phalguni": ("Manushya", "Cow"),
        "Hasta": ("Deva", "Buffalo"), "Chitra": ("Rakshasa", "Tiger"),
        "Swati": ("Deva", "Buffalo"), "Vishakha": ("Rakshasa", "Tiger"),
        "Anuradha": ("Deva", "Deer"), "Jyeshtha": ("Rakshasa", "Deer"),
        "Mula": ("Rakshasa", "Dog"), "Purva Ashadha": ("Manushya", "Monkey"),
        "Uttara Ashadha": ("Manushya", "Mongoose"), "Shravana": ("Deva", "Monkey"),
        "Dhanishta": ("Rakshasa", "Lion"), "Shatabhisha": ("Rakshasa", "Horse"),
        "Purva Bhadrapada": ("Manushya", "Lion"),
        "Uttara Bhadrapada": ("Manushya", "Cow"), "Revati": ("Deva", "Elephant")
    }
    return data.get(nak, ("Unknown", "Unknown"))

def calculate_vedic_chart(name, gender, dt, tm, lat, lon, city, ayanamsa_mode="Lahiri (Standard)"):
    if "Lahiri" in ayanamsa_mode:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
    elif "Raman" in ayanamsa_mode:
        swe.set_sid_mode(swe.SIDM_RAMAN)
    elif "KP" in ayanamsa_mode:
        swe.set_sid_mode(5)

    birth_dt = datetime.datetime.combine(dt, tm)
    utc_dt = birth_dt - datetime.timedelta(hours=5, minutes=30)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute / 60)

    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    asc_deg = (ascmc[0] - ayanamsa) % 360

    zodiac = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
              "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    lagna_sign = zodiac[int(asc_deg // 30)]

    planet_map = {
        "Sun": 0, "Moon": 1, "Mars": 4, "Mercury": 2,
        "Jupiter": 5, "Venus": 3, "Saturn": 6, "Rahu": 11
    }

    nak_list = [
        "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
        "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni",
        "Uttara Phalguni","Hasta","Chitra","Swati","Vishakha",
        "Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha",
        "Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada",
        "Uttara Bhadrapada","Revati"
    ]

    results = []
    user_rashi, user_nak = "", ""

    for p, pid in planet_map.items():
        pos = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL | swe.FLG_MOSEPH)[0][0]
        sign = zodiac[int(pos // 30) % 12]
        deg = pos % 30
        nak = nak_list[int(pos / (360 / 27)) % 27]
        results.append(f"{p}: {sign} ({deg:.2f}°) | {nak}")
        if p == "Moon":
            user_rashi, user_nak = sign, nak

    gana, yoni = get_gana_yoni(user_nak)

    return {
        "Name": name,
        "Gender": gender,
        "Lagna": lagna_sign,
        "Rashi": user_rashi,
        "Nakshatra": user_nak,
        "Gana": gana,
        "Yoni": yoni,
        "City": city,
        "Full_Chart": "\n".join(results)
    }

# --- 6. SIDEBAR UI ---
with st.sidebar:
    st.title("☸️ TaraVaani")

    st.markdown("### 🗣️ AI Language")
    lang_opt = st.selectbox(
        "Select output language",
        ["English","Hindi","Bengali","Marathi","Tamil","Telugu","Kannada","Gujarati","Malayalam"],
        label_visibility="collapsed"
    )

    st.header("Create Profile")
    n_in = st.text_input("Full Name", "Suman Naskar")
    g_in = st.selectbox("Gender", ["Male","Female"])
    d_in = st.date_input("Date of Birth", datetime.date(1993,4,23), format="DD/MM/YYYY")

    c1, c2 = st.columns(2)
    with c1: hr_in = st.selectbox("Hour (24h)", range(24), index=15)
    with c2: mn_in = st.selectbox("Minute", range(60), index=45)

    city_in = st.text_input("Birth City", "Kolkata, India")

    with st.expander("⚙️ Advanced Settings"):
        ayanamsa_opt = st.selectbox(
            "Calculation System",
            ["Lahiri (Standard)","Raman (Traditional)","KP (Krishnamurti)"]
        )

    if st.button("Generate Kundali", type="primary"):
        with st.spinner("Calculating..."):
            res = geocoder.geocode(city_in)
            if res:
                lat, lon = res[0]["geometry"]["lat"], res[0]["geometry"]["lng"]
                chart = calculate_vedic_chart(
                    n_in, g_in, d_in,
                    datetime.time(hr_in, mn_in),
                    lat, lon, res[0]["formatted"], ayanamsa_opt
                )
                st.session_state.current_data = chart
                st.rerun()

# --- 7. MAIN UI ---
if st.session_state.current_data:
    d = st.session_state.current_data

    st.markdown(f'<div class="header-box">Janma Kundali: {d["Name"]} 🙏</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Lagna", d['Lagna'])
    c2.metric("Rashi", d['Rashi'])
    c3.metric("Nakshatra", d['Nakshatra'])
    c4.metric("Gana", d['Gana'])
    c5.metric("Yoni", d['Yoni'])

    st.divider()
    st.subheader("📜 Planetary Degrees")
    st.code(d['Full_Chart'], language="text")
    st.divider()

    st.subheader(f"🤖 Ask TaraVaani ({lang_opt})")
    q_topic = st.selectbox(
        "Choose a Topic",
        ["General Life Overview","Career & Success","Marriage & Relationships","Health & Vitality","Wealth & Finance"]
    )

    if st.button("✨ Get Prediction"):
        prompt = f"""
Act as Vedic Astrologer TaraVaani.
User: {d['Name']} ({d['Gender']}).
Chart:
- Lagna: {d['Lagna']}
- Rashi: {d['Rashi']}
- Nakshatra: {d['Nakshatra']}
- Planets: {d['Full_Chart']}

Question: Predict about {q_topic}.
IMPORTANT: Write response in {lang_opt} language.
Style: Mystic, positive, clear. Use bullet points.
"""

        url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"

        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": prompt}]
            }]
        }

        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            params={"key": st.secrets["GEMINI_API_KEY"]},
            json=payload,
            timeout=30
        )

        data = response.json()
        st.subheader("🔍 Gemini Raw Response")
        st.code(data, language="json")


else:
    st.title("☸️ TaraVaani")
    st.info("👈 Please enter birth details in the sidebar to begin.")

