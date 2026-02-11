import streamlit as st
import swisseph as swe
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from opencage.geocoder import OpenCageGeocode
import google.generativeai as genai
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="wide")

st.markdown("""
<style>
    .header-box { background-color: #1e3a29; padding: 15px; border-radius: 10px; color: #90EE90; text-align: center; font-weight: bold; margin-bottom: 20px;}
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stSelectbox label { font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. FIREBASE & API SETUP ---
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
    except: pass

db = firestore.client()

try: geocoder = OpenCageGeocode(st.secrets["OPENCAGE_API_KEY"])
except: geocoder = None

try: genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except: pass

# --- 3. TRANSLATION ENGINE (ALL LANGUAGES) ---
TRANSLATIONS = {
    "English": {
        "title": "TaraVaani", "create_profile": "Create Profile", "name": "Name", "gender": "Gender", "dob": "Date of Birth", "tob": "Time", "city": "City", "gen_btn": "Generate Kundali",
        "tab_summary": "📝 Summary", "tab_charts": "🔮 Kundalis", "tab_dashas": "🗓️ Dashas", "tab_ai": "🤖 AI Prediction",
        "basic_details": "Basic Details", "panchang": "Panchang & Avakahada", "planets": "Planetary Positions", "chart_style": "Chart Style",
        "sun": "Sun", "moon": "Moon", "mars": "Mars", "merc": "Mercury", "jup": "Jupiter", "ven": "Venus", "sat": "Saturn", "rahu": "Rahu", "ketu": "Ketu", "asc": "Ascendant",
        "exalted": "Exalted", "debilitated": "Debilitated", "own": "Own Sign", "friendly": "Friendly", "neutral": "Neutral", "enemy": "Enemy",
        "mangalik_yes": "Yes (Mangalik)", "mangalik_no": "No"
    },
    "Hindi": {
        "title": "तारावाणी", "create_profile": "प्रोफाइल बनाएं", "name": "नाम", "gender": "लिंग", "dob": "जन्म तिथि", "tob": "समय", "city": "स्थान", "gen_btn": "कुंडली बनाएं",
        "tab_summary": "📝 सारांश", "tab_charts": "🔮 कुंडली", "tab_dashas": "🗓️ दशा", "tab_ai": "🤖 भविष्यफल",
        "basic_details": "मूल विवरण", "panchang": "पंचांग और अवकहड़ा", "planets": "ग्रह स्थिति", "chart_style": "चार्ट शैली",
        "sun": "सूर्य", "moon": "चंद्र", "mars": "मंगल", "merc": "बुध", "jup": "गुरु", "ven": "शुक्र", "sat": "शनि", "rahu": "राहु", "ketu": "केतु", "asc": "लग्न",
        "exalted": "उच्च", "debilitated": "नीच", "own": "स्वराशि", "friendly": "मित्र", "neutral": "सम", "enemy": "शत्रु",
        "mangalik_yes": "हाँ (मांगलिक)", "mangalik_no": "नहीं"
    },
    "Bengali": {
        "title": "তারাবাণী", "create_profile": "প্রোফাইল তৈরি করুন", "name": "নাম", "gender": "লিঙ্গ", "dob": "জন্ম তারিখ", "tob": "সময়", "city": "স্থান", "gen_btn": "কোষ্ঠী তৈরি করুন",
        "tab_summary": "📝 সারাংশ", "tab_charts": "🔮 কুষ্ঠি", "tab_dashas": "🗓️ দশা", "tab_ai": "🤖 ভবিষ্যৎবাণী",
        "basic_details": "মৌলিক বিবরণ", "panchang": "পঞ্চাঙ্গ ও অবকহদা", "planets": "গ্রহের অবস্থান", "chart_style": "চার্ট ধরণ",
        "sun": "রবি", "moon": "চন্দ্র", "mars": "মঙ্গল", "merc": "বুধ", "jup": "বৃহস্পতি", "ven": "শুক্র", "sat": "শনি", "rahu": "রাহু", "ketu": "কেতু", "asc": "লগ্ন",
        "exalted": "উচ্চ", "debilitated": "নীচ", "own": "স্বরাশি", "friendly": "মিত্র", "neutral": "সম", "enemy": "শত্রু",
        "mangalik_yes": "হ্যাঁ (মাঙ্গলিক)", "mangalik_no": "না"
    },
    "Marathi": {
        "title": "तारावाणी", "create_profile": "प्रोफाइल तयार करा", "name": "नाव", "gender": "लिंग", "dob": "जन्म तारीख", "tob": "वेळ", "city": "ठिकाण", "gen_btn": "कुंडली बनवा",
        "tab_summary": "📝 सारांश", "tab_charts": "🔮 कुंडली", "tab_dashas": "🗓️ दशा", "tab_ai": "🤖 भविष्य",
        "basic_details": "मूलभूत माहिती", "panchang": "पंचांग आणि अवकहडा", "planets": "ग्रह स्थिती", "chart_style": "चार्ट प्रकार",
        "sun": "सूर्य", "moon": "चंद्र", "mars": "मंगळ", "merc": "बुध", "jup": "गुरु", "ven": "शुक्र", "sat": "शनी", "rahu": "राहू", "ketu": "केतू", "asc": "लग्न",
        "exalted": "उच्च", "debilitated": "नीच", "own": "स्वराशी", "friendly": "मित्र", "neutral": "सम", "enemy": "शत्रू",
        "mangalik_yes": "हो (मांगलिक)", "mangalik_no": "नाही"
    },
    "Gujarati": {
        "title": "તારાવાણી", "create_profile": "પ્રોફાઇલ બનાવો", "name": "નામ", "gender": "લિંગ", "dob": "જન્મ તારીખ", "tob": "સમય", "city": "સ્થળ", "gen_btn": "કુંડળી બનાવો",
        "tab_summary": "📝 સારાંશ", "tab_charts": "🔮 કુંડળી", "tab_dashas": "🗓️ દશા", "tab_ai": "🤖 ભવિષ્યવાણી",
        "basic_details": "મૂળભૂત વિગતો", "panchang": "પંચાંગ", "planets": "ગ્રહ સ્થિતિ", "chart_style": "ચાર્ટ શૈલી",
        "sun": "સૂર્ય", "moon": "ચંદ્ર", "mars": "મંગળ", "merc": "બુધ", "jup": "ગુરુ", "ven": "શુક્ર", "sat": "શનિ", "rahu": "રાહુ", "ketu": "કેતુ", "asc": "લગ્ન",
        "exalted": "ઉચ્ચ", "debilitated": "નીચ", "own": "સ્વરાશિ", "friendly": "મિત્ર", "neutral": "સમ", "enemy": "શત્રુ",
        "mangalik_yes": "હા (માંગલિક)", "mangalik_no": "ના"
    },
    "Tamil": {
        "title": "தாரா வாணி", "create_profile": "சுயவிவரம்", "name": "பெயர்", "gender": "பாலினம்", "dob": "பிறந்த தேதி", "tob": "நேரம்", "city": "இடம்", "gen_btn": "ஜாதகம் கணி",
        "tab_summary": "📝 சுருக்கம்", "tab_charts": "🔮 கட்டம்", "tab_dashas": "🗓️ தசை", "tab_ai": "🤖 கணிப்பு",
        "basic_details": "அடிப்படை விவரங்கள்", "panchang": "பஞ்சாங்கம்", "planets": "கிரக நிலை", "chart_style": "கட்ட வகை",
        "sun": "சூரியன்", "moon": "சந்திரன்", "mars": "செவ்வாய்", "merc": "புதன்", "jup": "குரு", "ven": "சுக்கிரன்", "sat": "சனி", "rahu": "ராகு", "ketu": "கேது", "asc": "லக்னம்",
        "exalted": "உச்சம்", "debilitated": "நீசம்", "own": "ஆட்சி", "friendly": "நட்பு", "neutral": "சமம்", "enemy": "பகை",
        "mangalik_yes": "ஆம் (செவ்வாய் தோஷம்)", "mangalik_no": "இல்லை"
    },
    "Telugu": {
        "title": "తారావాణి", "create_profile": "ప్రొఫైల్", "name": "పేరు", "gender": "లింగం", "dob": "పుట్టిన తేదీ", "tob": "సమయం", "city": "ప్రాంతం", "gen_btn": "జాతకం పొందండి",
        "tab_summary": "📝 సారాంశం", "tab_charts": "🔮 చక్రం", "tab_dashas": "🗓️ దశ", "tab_ai": "🤖 జ్యోతిష్యం",
        "basic_details": "ప్రాథమిక వివరాలు", "panchang": "పంచాంగం", "planets": "గ్రహ స్థితి", "chart_style": "చక్రం రకం",
        "sun": "సూర్యుడు", "moon": "చంద్రుడు", "mars": "కుజుడు", "merc": "బుధుడు", "jup": "గురువు", "ven": "శుక్రుడు", "sat": "శని", "rahu": "రాహు", "ketu": "కేతు", "asc": "లగ్నం",
        "exalted": "ఉచ్ఛ", "debilitated": "నీచ", "own": "స్వక్షేత్రం", "friendly": "మిత్ర", "neutral": "సమ", "enemy": "శత్రు",
        "mangalik_yes": "అవును (కుజ దోషం)", "mangalik_no": "కాదు"
    },
    "Kannada": {
        "title": "ತಾರಾವಾಣಿ", "create_profile": "ಪ್ರೊಫೈಲ್", "name": "ಹೆಸರು", "gender": "ಲಿಂಗ", "dob": "ದಿನಾಂಕ", "tob": "ಸಮಯ", "city": "ಸ್ಥಳ", "gen_btn": "ಜಾತಕ ನೋಡಿ",
        "tab_summary": "📝 ಸಾರಾಂಶ", "tab_charts": "🔮 ಕುಂಡಲಿ", "tab_dashas": "🗓️ ದಶೆ", "tab_ai": "🤖 ಭವಿಷ್ಯ",
        "basic_details": "ಮೂಲ ವಿವರಗಳು", "panchang": "ಪಂಚಾಂಗ", "planets": "ಗ್ರಹ ಸ್ಥಿತಿ", "chart_style": "ಶೈಲಿ",
        "sun": "ಸೂರ್ಯ", "moon": "ಚಂದ್ರ", "mars": "ಮಂಗಳ", "merc": "ಬುಧ", "jup": "ಗುರು", "ven": "ಶುಕ್ರ", "sat": "ಶನಿ", "rahu": "ರಾಹು", "ketu": "ಕೇತು", "asc": "ಲಗ್ನ",
        "exalted": "ಉಚ್ಛ", "debilitated": "ನೀಚ", "own": "ಸ್ವಕ್ಷೇತ್ರ", "friendly": "ಮಿತ್ರ", "neutral": "ಸಮ", "enemy": "ಶತ್ರು",
        "mangalik_yes": "ಹೌದು (ಕುಜ ದೋಷ)", "mangalik_no": "ಇಲ್ಲ"
    },
    "Malayalam": {
        "title": "താരാവാണി", "create_profile": "പ്രൊഫൈൽ", "name": "പേര്", "gender": "ലിംഗം", "dob": "തീയതി", "tob": "സമയം", "city": "സ്ഥലം", "gen_btn": "ജാതകം",
        "tab_summary": "📝 സംഗ്രഹം", "tab_charts": "🔮 കുണ്ഡലി", "tab_dashas": "🗓️ ദശ", "tab_ai": "🤖 പ്രവചനം",
        "basic_details": "അടിസ്ഥാന വിവരങ്ങൾ", "panchang": "പഞ്ചാംഗം", "planets": "ഗ്രഹനില", "chart_style": "ശൈലി",
        "sun": "സൂര്യൻ", "moon": "ചന്ദ്രൻ", "mars": "ചൊവ്വ", "merc": "ബുധൻ", "jup": "വ്യാഴം", "ven": "ശുക്രൻ", "sat": "ശനി", "rahu": "രാഹു", "ketu": "കേതു", "asc": "ലഗ്നം",
        "exalted": "ഉച്ചം", "debilitated": "നീചം", "own": "സ്വക്ഷേത്രം", "friendly": "മിത്രം", "neutral": "സമം", "enemy": "ശത്രു",
        "mangalik_yes": "അതെ (ചൊവ്വാ ദോഷം)", "mangalik_no": "അല്ല"
    }
}

def txt(key, lang):
    """Retrives translated text"""
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["English"])
    return lang_dict.get(key, key)

# --- 4. SESSION STATE ---
if 'user_id' not in st.session_state: st.session_state.user_id = "suman_naskar_admin"
if 'current_data' not in st.session_state: st.session_state.current_data = None

# --- 5. ASTROLOGY ENGINE ---

def get_nakshatra_properties(nak_name, rashi_name):
    ganas = {"Deva": ["Ashwini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Swati", "Anuradha", "Shravana", "Revati"], "Manushya": ["Bharani", "Rohini", "Ardra", "Purva Phalguni", "Uttara Phalguni", "Purva Ashadha", "Uttara Ashadha", "Purva Bhadrapada", "Uttara Bhadrapada"], "Rakshasa": ["Krittika", "Ashlesha", "Magha", "Chitra", "Vishakha", "Jyeshtha", "Mula", "Dhanishta", "Shatabhisha"]}
    gana = next((g for g, naks in ganas.items() if nak_name in naks), "Unknown")
    yonis = {"Horse": ["Ashwini", "Shatabhisha"], "Elephant": ["Bharani", "Revati"], "Goat": ["Krittika", "Pushya"], "Snake": ["Rohini", "Mrigashira"], "Dog": ["Ardra", "Mula"], "Cat": ["Punarvasu", "Ashlesha"], "Rat": ["Magha", "Purva Phalguni"], "Cow": ["Uttara Phalguni", "Uttara Bhadrapada"], "Buffalo": ["Hasta", "Swati"], "Tiger": ["Chitra", "Vishakha"], "Deer": ["Anuradha", "Jyeshtha"], "Monkey": ["Purva Ashadha", "Shravana"], "Mongoose": ["Uttara Ashadha"], "Lion": ["Dhanishta", "Purva Bhadrapada"]}
    yoni = next((y for y, naks in yonis.items() if nak_name in naks), "Unknown")
    nadis = {"Adi (Vata)": ["Ashwini", "Ardra", "Punarvasu", "Uttara Phalguni", "Hasta", "Jyeshtha", "Mula", "Shatabhisha", "Purva Bhadrapada"], "Madhya (Pitta)": ["Bharani", "Mrigashira", "Pushya", "Purva Phalguni", "Chitra", "Anuradha", "Purva Ashadha", "Dhanishta", "Uttara Bhadrapada"], "Antya (Kapha)": ["Krittika", "Rohini", "Ashlesha", "Magha", "Swati", "Vishakha", "Uttara Ashadha", "Shravana", "Revati"]}
    nadi = next((n for n, naks in nadis.items() if nak_name in naks), "Unknown")
    rashi_props = {"Aries": ("Kshatriya", "Chatushpad"), "Taurus": ("Vaishya", "Chatushpad"), "Gemini": ("Shudra", "Manav"), "Cancer": ("Brahmin", "Jalchar"), "Leo": ("Kshatriya", "Vanchar"), "Virgo": ("Vaishya", "Manav"), "Libra": ("Shudra", "Manav"), "Scorpio": ("Brahmin", "Keet"), "Sagittarius": ("Kshatriya", "Manav/Chatushpad"), "Capricorn": ("Vaishya", "Jalchar"), "Aquarius": ("Shudra", "Manav"), "Pisces": ("Brahmin", "Jalchar")}
    varna, vashya = rashi_props.get(rashi_name, ("Unknown", "Unknown"))
    lords = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"}
    lord = lords.get(rashi_name, "Unknown")
    return {"Varna": varna, "Vashya": vashya, "Yoni": yoni, "Gana": gana, "Nadi": nadi, "SignLord": lord}

def calculate_panchang(jd, lat, lon, birth_dt):
    try:
        res = swe.rise_trans(jd - 1, 0, 0, lat, lon, 0)
        sunrise = swe.jdut1_to_utc(res[1][0], 1)
        sunset = swe.jdut1_to_utc(res[1][1], 1)
        sr_time = f"{int(sunrise[3]):02d}:{int(sunrise[4]):02d}:{int(sunrise[5]):02d}"
        ss_time = f"{int(sunset[3]):02d}:{int(sunset[4]):02d}:{int(sunset[5]):02d}"
    except: sr_time, ss_time = "Unknown", "Unknown"
    sun_pos = swe.calc_ut(jd, 0, swe.FLG_SIDEREAL)[0][0]
    moon_pos = swe.calc_ut(jd, 1, swe.FLG_SIDEREAL)[0][0]
    diff = (moon_pos - sun_pos) % 360
    tithi_num = int(diff / 12) + 1
    paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    tithi_name = f"{paksha} {tithi_num if tithi_num <= 15 else tithi_num - 15}"
    total = (moon_pos + sun_pos) % 360
    yoga_num = int(total / (13 + 20/60)) + 1
    yogas = ["Vishkumbha", "Priti", "Ayushman", "Saubhagya", "Sobhana", "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti"]
    yoga_name = yogas[yoga_num - 1] if 0 < yoga_num <= 27 else "Unknown"
    karan_num = int(diff / 6) + 1
    karan_name = f"Karana {karan_num}"
    ayanamsa = swe.get_ayanamsa_ut(jd)
    return {"Sunrise": sr_time, "Sunset": ss_time, "Tithi": tithi_name, "Yoga": yoga_name, "Karan": karan_name, "Ayanamsa": f"{ayanamsa:.2f}°"}

def get_navamsa_pos(deg):
    abs_deg = deg 
    sign_idx = int(abs_deg / 30) 
    deg_in_sign = abs_deg % 30
    nav_num = int(deg_in_sign / (30/9)) 
    moveable, fixed, dual = [0, 4, 8], [1, 5, 9], [2, 6, 10]
    if sign_idx in moveable: base = 0
    elif sign_idx in fixed: base = 9
    elif sign_idx in dual: base = 6
    else: base = 3
    nav_sign_idx = (base + nav_num) % 12
    return nav_sign_idx + 1

def get_planet_status(planet, sign_name):
    sign_map = {"Aries":1, "Taurus":2, "Gemini":3, "Cancer":4, "Leo":5, "Virgo":6, "Libra":7, "Scorpio":8, "Sagittarius":9, "Capricorn":10, "Aquarius":11, "Pisces":12}
    s_id = sign_map.get(sign_name, 0)
    if planet in ["Ascendant", "Uranus", "Neptune", "Pluto"]: return "--"
    
    own = {"Sun":[5], "Moon":[4], "Mars":[1,8], "Merc":[3,6], "Jup":[9,12], "Ven":[2,7], "Sat":[10,11], "Rahu":[], "Ketu":[]}
    exalted = {"Sun":1, "Moon":2, "Mars":10, "Merc":6, "Jup":4, "Ven":12, "Sat":7, "Rahu":2, "Ketu":8}
    debilitated = {"Sun":7, "Moon":8, "Mars":4, "Merc":12, "Jup":10, "Ven":6, "Sat":1, "Rahu":8, "Ketu":2}
    friends = {"Sun":[4,1,8,9,12], "Moon":[5,3,6], "Mars":[5,4,9,12], "Merc":[5,2,7], "Jup":[5,4,1,8], "Ven":[3,6,10,11], "Sat":[3,6,2,7], "Rahu":[3,6,2,7,10,11], "Ketu":[1,8,9,12]}
    enemies = {"Sun":[2,7,10,11], "Moon":[], "Mars":[3,6], "Merc":[4], "Jup":[3,6,2,7], "Ven":[5,4], "Sat":[5,4,1,8], "Rahu":[5,4,1], "Ketu":[5,4]}
    
    if s_id in own.get(planet, []): return "own"
    if exalted.get(planet) == s_id: return "exalted"
    if debilitated.get(planet) == s_id: return "debilitated"
    if s_id in friends.get(planet, []): return "friendly"
    if s_id in enemies.get(planet, []): return "enemy"
    return "neutral"

def get_planet_positions(jd, lat, lon, birth_dt, lang):
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lon, b'P') 
    asc_deg = (ascmc[0] - ayanamsa) % 360
    asc_sign = int(asc_deg // 30) + 1 
    asc_nav = get_navamsa_pos(asc_deg)

    planet_map = {0:"sun", 1:"moon", 4:"mars", 2:"merc", 5:"jup", 3:"ven", 6:"sat", 11:"rahu", 10:"ketu"}
    house_planets_d1 = {i: [] for i in range(1, 13)}
    house_planets_d9 = {i: [] for i in range(1, 13)}
    planet_details = []
    
    nak_list = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
    nak_lords = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"] * 3
    zodiac_list = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    sign_lords = ["Mars","Venus","Mercury","Moon","Sun","Mercury","Venus","Mars","Jupiter","Saturn","Saturn","Jupiter"]

    mars_house = 0

    for pid, code in planet_map.items():
        if code == "ketu":
            rahu_pos = swe.calc_ut(jd, 11, swe.FLG_SIDEREAL)[0][0]
            pos = (rahu_pos + 180) % 360
            speed = 0
        else:
            calc = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)
            pos = calc[0][0]
            speed = calc[0][3]
            
        sign = int(pos // 30) + 1 
        deg = pos % 30
        house_d1 = ((sign - asc_sign) % 12) + 1
        
        # Localized Planet Name for Chart
        p_name_local = txt(code, lang)
        house_planets_d1[house_d1].append(p_name_local)
        
        if code == "mars": mars_house = house_d1
        
        nav_sign = get_navamsa_pos(pos)
        house_d9 = ((nav_sign - asc_nav) % 12) + 1
        house_planets_d9[house_d9].append(p_name_local)
        
        nak_idx = int(pos / (360/27)) % 27
        nak_name = nak_list[nak_idx]
        nak_lord = nak_lords[nak_idx]
        sign_name = zodiac_list[sign-1]
        sign_lord = sign_lords[sign-1]
        
        is_retro = "Retro" if speed < 0 else "Direct"
        status_key = get_planet_status(code, sign_name) # returns key like 'exalted'
        status_display = txt(status_key, lang) # Localized status
        
        planet_details.append({
            "Planet": p_name_local, "Sign": sign_name, "Sign Lord": sign_lord, 
            "Nakshatra": nak_name, "Naksh Lord": nak_lord, "Degree": f"{int(deg)}°{int((deg%1)*60)}'",
            "Retro": is_retro, "House": house_d1, "Status": status_display
        })

    l_sign_name = zodiac_list[asc_sign-1]
    
    # Ascendant Row
    planet_details.insert(0, {
        "Planet": txt("asc", lang), "Sign": l_sign_name, "Sign Lord": sign_lords[asc_sign-1],
        "Nakshatra": nak_list[int(asc_deg/(360/27)%27)], "Naksh Lord": nak_lords[int(asc_deg/(360/27)%27)],
        "Degree": f"{int(asc_deg%30)}°{int((asc_deg%30%1)*60)}'", "Retro": "--", "House": 1, "Status": "--"
    })

    # Mangalik Logic
    is_mangalik = txt("mangalik_yes", lang) if mars_house in [1, 4, 7, 8, 12] else txt("mangalik_no", lang)
    
    # Moon for Panchang
    moon_pos = swe.calc_ut(jd, 1, swe.FLG_SIDEREAL)[0][0]
    moon_sign_idx = int(moon_pos // 30)
    moon_nak_idx = int(moon_pos / (360/27)) % 27
    
    summary = {
        "Lagna": l_sign_name,
        "Rashi": zodiac_list[moon_sign_idx],
        "Nakshatra": nak_list[moon_nak_idx],
        "Charan": 1, 
        "Mangalik": is_mangalik,
        **calculate_panchang(jd, lat, lon, birth_dt),
        **get_nakshatra_properties(nak_list[moon_nak_idx], zodiac_list[moon_sign_idx]),
        "Asc_Sign_ID": asc_sign 
    }

    return house_planets_d1, house_planets_d9, asc_sign, asc_nav, planet_details, summary

# --- VISUALIZATION ---
def draw_chart(house_planets, asc_sign, style="North", title="Lagna Chart"):
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=10, fontweight='bold', pad=10)
    
    if style == "North":
        ax.plot([0, 1], [1, 0], 'k-', lw=1.5)
        ax.plot([0, 1], [0, 1], 'k-', lw=1.5)
        ax.plot([0, 0.5], [0.5, 0], 'k-', lw=1.5)
        ax.plot([0.5, 1], [0, 0.5], 'k-', lw=1.5)
        ax.plot([0.5, 1], [1, 0.5], 'k-', lw=1.5)
        ax.plot([0, 0.5], [0.5, 1], 'k-', lw=1.5)
        rect = patches.Rectangle((0, 0), 1, 1, linewidth=1.5, edgecolor='black', facecolor='none')
        ax.add_patch(rect)
        pos = {1: (0.5, 0.8), 2: (0.25, 0.85), 3: (0.15, 0.75), 4: (0.2, 0.5), 5: (0.15, 0.25), 6: (0.25, 0.15), 7: (0.5, 0.2), 8: (0.75, 0.15), 9: (0.85, 0.25), 10: (0.8, 0.5), 11: (0.85, 0.75), 12: (0.75, 0.85)}
        for h, (x, y) in pos.items():
            sign_num = ((asc_sign + h - 2) % 12) + 1
            ax.text(x, y-0.08, str(sign_num), fontsize=8, color='red', ha='center')
            if house_planets[h]:
                # Use a font that supports generic unicode, but Matplotlib default is okay for many
                ax.text(x, y, "\n".join(house_planets[h]), fontsize=7, fontweight='bold', ha='center', va='center')
    else:
        for i in [0, 0.25, 0.5, 0.75, 1]:
            ax.plot([0, 1], [i, i], 'k-', lw=1)
            ax.plot([i, i], [0, 1], 'k-', lw=1)
        rect = patches.Rectangle((0.25, 0.25), 0.5, 0.5, color='white', zorder=10)
        ax.add_patch(rect)
        ax.text(0.5, 0.5, "Rashi", ha='center', va='center', fontsize=10, fontweight='bold', zorder=11)
        sign_pos = {1: (0.37, 0.87), 2: (0.62, 0.87), 3: (0.87, 0.87), 4: (0.87, 0.62), 5: (0.87, 0.37), 6: (0.87, 0.12), 7: (0.62, 0.12), 8: (0.37, 0.12), 9: (0.12, 0.12), 10: (0.12, 0.37), 11: (0.12, 0.62), 12: (0.12, 0.87)}
        for h, planets in house_planets.items():
            sign = ((asc_sign + h - 2) % 12) + 1
            x, y = sign_pos[sign]
            txt = "\n".join(planets)
            if h == 1: txt += "\n(Asc)"
            ax.text(x, y, txt, fontsize=7, fontweight='bold', ha='center', va='center')
    return fig

# --- DASHA ENGINE ---
def calculate_vimshottari_structure(jd, birth_date):
    moon_pos = swe.calc_ut(jd, 1, swe.FLG_SIDEREAL)[0][0]
    nak_deg = (moon_pos * (27/360)) 
    nak_idx = int(nak_deg)
    balance_prop = 1 - (nak_deg - nak_idx)
    lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    years = [7, 20, 6, 10, 7, 18, 16, 19, 17]
    start_lord_idx = nak_idx % 9
    dashas = []
    curr_date = birth_date
    first_dur = years[start_lord_idx] * balance_prop
    dashas.append({"Lord": lords[start_lord_idx], "Start": curr_date, "End": curr_date + datetime.timedelta(days=first_dur*365.25), "FullYears": years[start_lord_idx]})
    curr_date = dashas[0]['End']
    for i in range(1, 9):
        idx = (start_lord_idx + i) % 9
        dur = years[idx]
        dashas.append({"Lord": lords[idx], "Start": curr_date, "End": curr_date + datetime.timedelta(days=dur*365.25), "FullYears": dur})
        curr_date = dashas[-1]['End']
    return dashas

def get_sub_periods(lord_name, start_date, level_years):
    lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    years = [7, 20, 6, 10, 7, 18, 16, 19, 17]
    try: start_idx = lords.index(lord_name)
    except: return []
    subs = []
    curr = start_date
    for i in range(9):
        idx = (start_idx + i) % 9
        sub_lord = lords[idx]
        sub_years = years[idx]
        duration_years = (level_years * sub_years) / 120
        end_date = curr + datetime.timedelta(days=duration_years*365.25)
        subs.append({"Lord": sub_lord, "Start": curr, "End": end_date, "Duration": duration_years, "FullYears": sub_years})
        curr = end_date
    return subs

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("☸️ TaraVaani")
    
    # UI LANGUAGE SELECTION
    lang_opt = st.selectbox("Language", ["English", "Hindi", "Bengali", "Marathi", "Tamil", "Telugu", "Kannada", "Gujarati", "Malayalam"])
    
    st.header(txt("create_profile", lang_opt))
    n_in = st.text_input(txt("name", lang_opt), "Suman Naskar")
    g_in = st.selectbox(txt("gender", lang_opt), ["Male", "Female"])
    d_in = st.date_input(txt("dob", lang_opt), value=datetime.date(1993, 4, 23), min_value=datetime.date(1900,1,1), format="DD/MM/YYYY")
    c1, c2 = st.columns(2)
    hr_in = c1.selectbox("Hour", range(24), index=15)
    mn_in = c2.selectbox("Min", range(60), index=45)
    city_in = st.text_input(txt("city", lang_opt), "Kolkata, India")
    
    with st.expander("⚙️ Advanced Settings"):
        ayanamsa_opt = st.selectbox("Calculation System", ["Lahiri (Standard)", "Raman (Traditional)", "KP (Krishnamurti)"])
    
    if st.button(txt("gen_btn", lang_opt), type="primary"):
        with st.spinner("Calculating..."):
            try:
                res = geocoder.geocode(city_in)
                if res:
                    lat, lng = res[0]['geometry']['lat'], res[0]['geometry']['lng']
                    birth_dt = datetime.datetime.combine(d_in, datetime.time(hr_in, mn_in))
                    utc_dt = birth_dt - datetime.timedelta(hours=5, minutes=30)
                    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
                    if "Lahiri" in ayanamsa_opt: swe.set_sid_mode(swe.SIDM_LAHIRI)
                    elif "Raman" in ayanamsa_opt: swe.set_sid_mode(swe.SIDM_RAMAN)
                    elif "KP" in ayanamsa_opt: swe.set_sid_mode(5)
                    
                    # Pass Language to Planet Calculator
                    hp_d1, hp_d9, asc_s, asc_n, p_dets, summ = get_planet_positions(jd, lat, lng, birth_dt, lang_opt)
                    
                    st.session_state.current_data = {
                        "Name": n_in, "Gender": g_in, 
                        "House_Planets_D1": hp_d1, "House_Planets_D9": hp_d9,
                        "Asc_Sign_D1": asc_s, "Asc_Sign_D9": asc_n,
                        "Planet_Details": p_dets, "Summary": summ,
                        "Full_Chart_Text": str(p_dets), "JD": jd, "BirthDate": d_in
                    }
                    st.rerun()
                else: st.error("City not found.")
            except Exception as e: st.error(f"Error: {e}")

# --- 6. MAIN UI ---
if st.session_state.current_data:
    d = st.session_state.current_data
    
    if 'House_Planets_D1' not in d:
        st.warning("⚠️ Update applied. Click 'Generate' again.")
        st.stop()
    
    tab1, tab2, tab3, tab4 = st.tabs([txt("tab_summary", lang_opt), txt("tab_charts", lang_opt), txt("tab_dashas", lang_opt), txt("tab_ai", lang_opt)])
    
    # 1. SUMMARY TAB
    with tab1:
        st.markdown(f'<div class="header-box">{d["Name"]} 🙏</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(txt("basic_details", lang_opt))
            st.write(f"**{txt('name', lang_opt)}:** {d['Name']}")
            st.write(f"**Date:** {d['BirthDate'].strftime('%d %B %Y')}")
            st.write(f"**Place:** {city_in}")
            if d['Summary']['Sunrise'] != "Unknown": st.write(f"**Sunrise:** {d['Summary']['Sunrise']}")
            if d['Summary']['Sunset'] != "Unknown": st.write(f"**Sunset:** {d['Summary']['Sunset']}")
            st.write(f"**Ayanamsa:** {d['Summary']['Ayanamsa']}")
        with c2:
            st.subheader(txt("panchang", lang_opt))
            st.write(f"**Lagna:** {d['Summary']['Lagna']}")
            st.write(f"**Rashi:** {d['Summary']['Rashi']}")
            st.write(f"**Nakshatra:** {d['Summary']['Nakshatra']}")
            st.write(f"**Mangalik:** {d['Summary']['Mangalik']}")
            st.write(f"**Varna:** {d['Summary']['Varna']}")
            st.write(f"**Yoni:** {d['Summary']['Yoni']}")
            st.write(f"**Gana:** {d['Summary']['Gana']}")
            st.write(f"**Nadi:** {d['Summary']['Nadi']}")
            st.write(f"**Tithi:** {d['Summary']['Tithi']}")
            st.write(f"**Yoga:** {d['Summary']['Yoga']}")
    
    # 2. KUNDALIS TAB
    with tab2:
        c_type = st.selectbox(txt("chart_style", lang_opt), ["North Indian", "South Indian"])
        c1, c2 = st.columns(2)
        style_code = "North" if "North" in c_type else "South"
        with c1:
            fig1 = draw_chart(d['House_Planets_D1'], d['Asc_Sign_D1'], style_code, "Lagna Chart (D1)")
            st.pyplot(fig1)
        with c2:
            fig9 = draw_chart(d['House_Planets_D9'], d['Asc_Sign_D9'], style_code, "Navamsa Chart (D9)")
            st.pyplot(fig9)
            
        st.divider()
        st.subheader(txt("planets", lang_opt))
        df = pd.DataFrame(d['Planet_Details'])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # 3. DASHA TAB
    with tab3:
        st.markdown("### Vimshottari Dasha")
        md_list = calculate_vimshottari_structure(d['JD'], d['BirthDate'])
        md_data = [{"Lord": m['Lord'], "Start": m['Start'].strftime('%d-%b-%Y'), "End": m['End'].strftime('%d-%b-%Y')} for m in md_list]
        st.dataframe(pd.DataFrame(md_data), use_container_width=True)
        
        # Selectors logic remains similar but could be translated if needed
        md_opts = [f"{m['Lord']} ({m['Start'].year}-{m['End'].year})" for m in md_list]
        sel_md_idx = st.selectbox("⬇️ Select Mahadasha:", range(len(md_list)), format_func=lambda x: md_opts[x])
        sel_md = md_list[sel_md_idx]
        
        st.divider()
        st.markdown(f"**Antardasha under {sel_md['Lord']}**")
        ad_list = get_sub_periods(sel_md['Lord'], sel_md['Start'], sel_md['FullYears'])
        ad_data = [{"Lord": a['Lord'], "Start": a['Start'].strftime('%d-%b-%Y'), "End": a['End'].strftime('%d-%b-%Y')} for a in ad_list]
        st.dataframe(pd.DataFrame(ad_data), use_container_width=True)
        
        ad_opts = [f"{a['Lord']} (ends {a['End'].strftime('%d-%b-%Y')})" for a in ad_list]
        sel_ad_idx = st.selectbox("⬇️ Select Antardasha:", range(len(ad_list)), format_func=lambda x: ad_opts[x])
        sel_ad = ad_list[sel_ad_idx]
        
        st.divider()
        st.markdown(f"**Pratyantardasha under {sel_ad['Lord']}**")
        pd_list = get_sub_periods(sel_ad['Lord'], sel_ad['Start'], sel_ad['Duration'])
        pd_data = [{"Lord": p['Lord'], "Start": p['Start'].strftime('%d-%b-%Y'), "End": p['End'].strftime('%d-%b-%Y')} for p in pd_list]
        st.dataframe(pd.DataFrame(pd_data), use_container_width=True)

    # 4. AI PREDICTION TAB
    with tab4:
        st.subheader(f"Ask TaraVaani ({lang_opt})")
        q_topic = st.selectbox("Topic", ["General Life", "Career", "Marriage", "Health", "Wealth"])
        if st.button("✨ Get Prediction"):
            prompt = f"""
            Act as Vedic Astrologer TaraVaani.
            User: {d['Name']} ({d['Gender']}).
            Planetary Positions: {d['Full_Chart_Text']}
            Question: Predict about {q_topic}.
            Start with "Radhe Radhe 🙏". Answer in {lang_opt}.
            """
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                print(f"API Error: {e}")
                st.warning("✨ The cosmic channels are momentarily quiet. Please try again in a few moments. 🙏")

else:
    st.title("☸️ TaraVaani")
    st.info("👈 Enter details to generate chart.")
