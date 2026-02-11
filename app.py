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
    .interp-box { background-color: #0e1117; border: 1px solid #333; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    h3 { font-size: 1.2rem; font-weight: 600; margin-top: 1rem; }
    .status-guide { font-size: 0.9rem; color: #cccccc; }
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

# --- 3. TRANSLATION ENGINE ---
TRANSLATIONS = {
    "English": {"title": "TaraVaani", "gen_btn": "Generate Kundali", "tab_summary": "📝 Summary", "tab_kundalis": "🔮 Kundalis", "tab_kp": "⭐ KP System", "tab_charts": "📊 All Charts", "tab_dashas": "🗓️ Dashas", "tab_ai": "🤖 AI Prediction", "asc": "Ascendant", "mangalik_yes": "Yes (Mangalik)", "mangalik_no": "No", "bhav_chart": "Bhav Chalit Chart"},
}

def txt(key, lang):
    lang_dict = TRANSLATIONS.get("English")
    return lang_dict.get(key, key)

# --- 4. SESSION STATE ---
if 'user_id' not in st.session_state: st.session_state.user_id = "suman_naskar_admin"
if 'current_data' not in st.session_state: st.session_state.current_data = None

# --- 5. ASTROLOGY ENGINE ---

def get_kp_lords(deg):
    """Calculates Sign, Star (Nakshatra) and Sub Lord for KP"""
    lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    years = [7, 20, 6, 10, 7, 18, 16, 19, 17]
    zodiac_lords = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
    
    sign_idx = int(deg / 30)
    sign_lord = zodiac_lords[sign_idx % 12]
    
    nak_span = 13 + (20/60) 
    nak_idx_total = int(deg / nak_span)
    star_lord = lords[nak_idx_total % 9]
    
    deg_in_nak = deg - (nak_idx_total * nak_span)
    min_in_nak = deg_in_nak * 60
    
    curr_sub = nak_idx_total % 9
    acc_min = 0
    sub_lord = lords[curr_sub]
    
    for _ in range(9):
        period_min = (years[curr_sub] / 120) * 800
        if min_in_nak < (acc_min + period_min):
            sub_lord = lords[curr_sub]
            break
        acc_min += period_min
        curr_sub = (curr_sub + 1) % 9
        
    return sign_lord, star_lord, sub_lord

def calculate_varga_sign(deg, varga_num):
    """Calculates Varga Sign for 19 Charts"""
    sign_idx = int(deg / 30)
    deg_in_sign = deg % 30
    if varga_num == 1: return sign_idx + 1
    elif varga_num == 2:
        is_odd = (sign_idx % 2 == 0)
        is_first_half = (deg_in_sign < 15)
        if is_odd: return 5 if is_first_half else 4
        else: return 4 if is_first_half else 5
    elif varga_num == 3: return ((sign_idx + (int(deg_in_sign/10) * 4)) % 12) + 1
    elif varga_num == 4: return ((sign_idx + (int(deg_in_sign/7.5) * 3)) % 12) + 1
    elif varga_num == 7: 
        start = sign_idx if (sign_idx % 2 == 0) else (sign_idx + 6)
        return ((start + int(deg_in_sign/(30/7))) % 12) + 1
    elif varga_num == 9:
        if sign_idx in [0, 4, 8]: base = 0
        elif sign_idx in [1, 5, 9]: base = 9
        else: base = 6
        return ((base + int(deg_in_sign/(30/9))) % 12) + 1
    elif varga_num == 10:
        start = sign_idx if (sign_idx % 2 == 0) else (sign_idx + 8)
        return ((start + int(deg_in_sign/3)) % 12) + 1
    elif varga_num == 12: return ((sign_idx + int(deg_in_sign/2.5)) % 12) + 1
    # Harmonic fallback for higher vargas
    return (int(deg * varga_num / 30) % 12) + 1

def get_nakshatra_properties(nak_name, rashi_name, charan):
    ganas = {"Deva": ["Ashwini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Swati", "Anuradha", "Shravana", "Revati"], "Manushya": ["Bharani", "Rohini", "Ardra", "Purva Phalguni", "Uttara Phalguni", "Purva Ashadha", "Uttara Ashadha", "Purva Bhadrapada", "Uttara Bhadrapada"], "Rakshasa": ["Krittika", "Ashlesha", "Magha", "Chitra", "Vishakha", "Jyeshtha", "Mula", "Dhanishta", "Shatabhisha"]}
    gana = next((g for g, naks in ganas.items() if nak_name in naks), "Unknown")
    
    yonis = {"Horse": ["Ashwini", "Shatabhisha"], "Elephant": ["Bharani", "Revati"], "Goat": ["Krittika", "Pushya"], "Snake": ["Rohini", "Mrigashira"], "Dog": ["Ardra", "Mula"], "Cat": ["Punarvasu", "Ashlesha"], "Rat": ["Magha", "Purva Phalguni"], "Cow": ["Uttara Phalguni", "Uttara Bhadrapada"], "Buffalo": ["Hasta", "Swati"], "Tiger": ["Chitra", "Vishakha"], "Deer": ["Anuradha", "Jyeshtha"], "Monkey": ["Purva Ashadha", "Shravana"], "Mongoose": ["Uttara Ashadha"], "Lion": ["Dhanishta", "Purva Bhadrapada"]}
    yoni = next((y for y, naks in yonis.items() if nak_name in naks), "Unknown")
    
    nadis = {"Adi (Vata)": ["Ashwini", "Ardra", "Punarvasu", "Uttara Phalguni", "Hasta", "Jyeshtha", "Mula", "Shatabhisha", "Purva Bhadrapada"], "Madhya (Pitta)": ["Bharani", "Mrigashira", "Pushya", "Purva Phalguni", "Chitra", "Anuradha", "Purva Ashadha", "Dhanishta", "Uttara Bhadrapada"], "Antya (Kapha)": ["Krittika", "Rohini", "Ashlesha", "Magha", "Swati", "Vishakha", "Uttara Ashadha", "Shravana", "Revati"]}
    nadi = next((n for n, naks in nadis.items() if nak_name in naks), "Unknown")
    
    rashi_props = {"Aries": ("Kshatriya", "Chatushpad", "Fire"), "Taurus": ("Vaishya", "Chatushpad", "Earth"), "Gemini": ("Shudra", "Manav", "Air"), "Cancer": ("Brahmin", "Jalchar", "Water"), "Leo": ("Kshatriya", "Vanchar", "Fire"), "Virgo": ("Vaishya", "Manav", "Earth"), "Libra": ("Shudra", "Manav", "Air"), "Scorpio": ("Brahmin", "Keet", "Water"), "Sagittarius": ("Kshatriya", "Manav/Chatushpad", "Fire"), "Capricorn": ("Vaishya", "Jalchar", "Earth"), "Aquarius": ("Shudra", "Manav", "Air"), "Pisces": ("Brahmin", "Jalchar", "Water")}
    varna, vashya, tatva = rashi_props.get(rashi_name, ("Unknown", "Unknown", "Unknown"))
    
    lords = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"}
    lord = lords.get(rashi_name, "Unknown")
    
    # Name Alphabet Logic
    name_map = {
        "Ashwini": ["Chu", "Che", "Cho", "La"], "Bharani": ["Li", "Lu", "Le", "Lo"], "Krittika": ["A", "I", "U", "E"],
        "Rohini": ["O", "Va", "Vi", "Vu"], "Mrigashira": ["Ve", "Vo", "Ka", "Ki"], "Ardra": ["Ku", "Gha", "Ng", "Chha"],
        "Punarvasu": ["Ke", "Ko", "Ha", "Hi"], "Pushya": ["Hu", "He", "Ho", "Da"], "Ashlesha": ["Di", "Du", "De", "Do"],
        "Magha": ["Ma", "Mi", "Mu", "Me"], "Purva Phalguni": ["Mo", "Ta", "Ti", "Tu"], "Uttara Phalguni": ["Te", "To", "Pa", "Pi"],
        "Hasta": ["Pu", "Sha", "Na", "Tha"], "Chitra": ["Pe", "Po", "Ra", "Ri"], "Swati": ["Ru", "Re", "Ro", "Ta"],
        "Vishakha": ["Ti", "Tu", "Te", "To"], "Anuradha": ["Na", "Ni", "Nu", "Ne"], "Jyeshtha": ["No", "Ya", "Yi", "Yu"],
        "Mula": ["Ye", "Yo", "Ba", "Bi"], "Purva Ashadha": ["Bu", "Dha", "Bha", "Dha"], "Uttara Ashadha": ["Bhe", "Bho", "Ja", "Ji"],
        "Shravana": ["Ju", "Je", "Jo", "Gha"], "Dhanishta": ["Ga", "Gi", "Gu", "Ge"], "Shatabhisha": ["Go", "Sa", "Si", "Su"],
        "Purva Bhadrapada": ["Se", "So", "Da", "Di"], "Uttara Bhadrapada": ["Du", "Tha", "Jha", "Da"], "Revati": ["De", "Do", "Cha", "Chi"]
    }
    sounds = name_map.get(nak_name, ["-", "-", "-", "-"])
    name_alpha = sounds[charan - 1] if 0 < charan <= 4 else "-"

    return {"Varna": varna, "Vashya": vashya, "Yoni": yoni, "Gana": gana, "Nadi": nadi, "SignLord": lord, "Tatva": tatva, "NameAlpha": name_alpha}

def calculate_panchang(jd, lat, lon, birth_dt, moon_pos):
    try:
        res = swe.rise_trans(jd - 1, 0, 0, lat, lon, 0)
        sunrise = swe.jdut1_to_utc(res[1][0], 1)
        sunset = swe.jdut1_to_utc(res[1][1], 1)
        sr_time = f"{int(sunrise[3]):02d}:{int(sunrise[4]):02d}:{int(sunrise[5]):02d}"
        ss_time = f"{int(sunset[3]):02d}:{int(sunset[4]):02d}:{int(sunset[5]):02d}"
    except: sr_time, ss_time = "Unknown", "Unknown"
    
    sun_pos = swe.calc_ut(jd, 0, swe.FLG_SIDEREAL)[0][0]
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

# --- THIS WAS THE MISSING FUNCTION CAUSING ERROR ---
def get_planet_status(planet, sign_name):
    # Standardize to Title Case for safety
    planet = planet.title()
    sign_name = sign_name.title()
    
    sign_map = {"Aries":1, "Taurus":2, "Gemini":3, "Cancer":4, "Leo":5, "Virgo":6, "Libra":7, "Scorpio":8, "Sagittarius":9, "Capricorn":10, "Aquarius":11, "Pisces":12}
    s_id = sign_map.get(sign_name, 0)
    
    if planet in ["Ascendant", "Uranus", "Neptune", "Pluto", "Rahu", "Ketu"]: return "--"
    
    own = {"Sun":[5], "Moon":[4], "Mars":[1,8], "Mercury":[3,6], "Jupiter":[9,12], "Venus":[2,7], "Saturn":[10,11]}
    exalted = {"Sun":1, "Moon":2, "Mars":10, "Mercury":6, "Jupiter":4, "Venus":12, "Saturn":7}
    debilitated = {"Sun":7, "Moon":8, "Mars":4, "Mercury":12, "Jupiter":10, "Venus":6, "Saturn":1}
    friends = {"Sun":[4,1,8,9,12], "Moon":[5,3,6], "Mars":[5,4,9,12], "Mercury":[5,2,7], "Jupiter":[5,4,1,8], "Venus":[3,6,10,11], "Saturn":[3,6,2,7]}
    enemies = {"Sun":[2,7,10,11], "Moon":[], "Mars":[3,6], "Mercury":[4], "Jupiter":[3,6,2,7], "Venus":[5,4], "Saturn":[5,4,1,8]}
    
    if s_id in own.get(planet, []): return "Own Sign"
    if exalted.get(planet) == s_id: return "Exalted"
    if debilitated.get(planet) == s_id: return "Debilitated"
    if s_id in friends.get(planet, []): return "Friendly"
    if s_id in enemies.get(planet, []): return "Enemy"
    return "Neutral"

# --- DETAILED INTERPRETATIONS ---
def get_detailed_interpretations(asc_sign_name):
    """Returns detailed text for Summary Tab based on Ascendant"""
    data = {
        "Aries": {
            "Gen": "As an Aries Ascendant, you are born under the sign of the Ram, ruled by Mars. This placement bestows upon you a dynamic, energetic, and pioneering spirit. You are a natural initiator who loves to start new projects.",
            "Pers": "You possess a strong will and a direct approach to life. You are courageous, confident, and enthusiastic. However, you can also be impulsive and impatient. You value independence highly and often prefer to lead rather than follow.",
            "Phys": "Physically, you tend to have a strong, athletic build with prominent features, often a distinct nose or eyebrows. You likely walk quickly and have an intense gaze. High energy levels are a hallmark of your constitution.",
            "Health": "You are prone to issues related to the head, such as migraines, headaches, or fevers. Stress management is crucial for you. Regular exercise is not just good for your body but essential for venting your excess mental energy.",
            "Career": "You thrive in competitive environments. Careers in the military, police, sports, engineering, or entrepreneurship suit you well. You need a role that offers autonomy and challenges rather than routine desk work.",
            "Rel": "In relationships, you are passionate and direct. You enjoy the chase and are often the one to initiate interest. You need a partner who can match your energy but also has the patience to handle your occasional outbursts."
        },
        # (Default text for other signs to prevent crashes - Ideally expand this list)
        "Taurus": {"Gen": "Ruled by Venus, stable and practical.", "Pers": "Patient and reliable.", "Phys": "Strong build.", "Health": "Throat issues.", "Career": "Finance/Arts.", "Rel": "Loyal."},
        "Gemini": {"Gen": "Ruled by Mercury, intellectual.", "Pers": "Witty and adaptable.", "Phys": "Slender.", "Health": "Nervous system.", "Career": "Media.", "Rel": "Fun-loving."},
        "Cancer": {"Gen": "Ruled by Moon, emotional.", "Pers": "Nurturing.", "Phys": "Soft features.", "Health": "Stomach.", "Career": "Caregiving.", "Rel": "Devoted."},
        "Leo": {"Gen": "Ruled by Sun, regal.", "Pers": "Proud and generous.", "Phys": "Broad shoulders.", "Health": "Heart.", "Career": "Leadership.", "Rel": "Passionate."},
        "Virgo": {"Gen": "Ruled by Mercury, analytical.", "Pers": "Perfectionist.", "Phys": "Neat.", "Health": "Digestion.", "Career": "Service.", "Rel": "Practical."},
        "Libra": {"Gen": "Ruled by Venus, balanced.", "Pers": "Diplomatic.", "Phys": "Attractive.", "Health": "Kidneys.", "Career": "Law/Arts.", "Rel": "Romantic."},
        "Scorpio": {"Gen": "Ruled by Mars, intense.", "Pers": "Secretive.", "Phys": "Piercing eyes.", "Health": "Reproductive.", "Career": "Research.", "Rel": "Possessive."},
        "Sagittarius": {"Gen": "Ruled by Jupiter, optimistic.", "Pers": "Philosophical.", "Phys": "Athletic.", "Health": "Hips/Liver.", "Career": "Teaching.", "Rel": "Adventurous."},
        "Capricorn": {"Gen": "Ruled by Saturn, disciplined.", "Pers": "Ambitious.", "Phys": "Bony.", "Health": "Joints.", "Career": "Business.", "Rel": "Serious."},
        "Aquarius": {"Gen": "Ruled by Saturn, innovative.", "Pers": "Humanitarian.", "Phys": "Unique.", "Health": "Ankles.", "Career": "Science.", "Rel": "Friendly."},
        "Pisces": {"Gen": "Ruled by Jupiter, spiritual.", "Pers": "Compassionate.", "Phys": "Soft.", "Health": "Feet.", "Career": "Healing.", "Rel": "Soulful."}
    }
    return data.get(asc_sign_name, data["Aries"])

def get_planet_positions(jd, lat, lon, birth_dt, lang):
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lon, b'P') 
    asc_deg = (ascmc[0] - ayanamsa) % 360
    
    planet_map = {0:"Sun", 1:"Moon", 4:"Mars", 2:"Mercury", 5:"Jupiter", 3:"Venus", 6:"Saturn", 11:"Rahu", 10:"Ketu"}
    raw_bodies = {}
    raw_bodies["Ascendant"] = asc_deg
    
    for pid, name in planet_map.items():
        if name == "Ketu":
            rahu_pos = swe.calc_ut(jd, 11, swe.FLG_SIDEREAL)[0][0]
            pos = (rahu_pos + 180) % 360
        else:
            pos = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]
        raw_bodies[name] = pos

    # --- VARGA CALCULATION ---
    varga_list = [1, 2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60]
    charts_data = {}
    
    for v in varga_list:
        chart_key = f"D{v}"
        charts_data[chart_key] = {i: [] for i in range(1, 13)}
        asc_varga_sign = calculate_varga_sign(raw_bodies["Ascendant"], v)
        for p_name, p_deg in raw_bodies.items():
            if p_name == "Ascendant": continue
            p_varga_sign = calculate_varga_sign(p_deg, v)
            house_num = ((p_varga_sign - asc_varga_sign) % 12) + 1
            charts_data[chart_key][house_num].append(p_name)
            
    charts_data["Chalit"] = charts_data["D1"] 
    
    # Sun & Moon Charts
    sun_sign = int(raw_bodies["Sun"] / 30) + 1
    sun_data = {i: [] for i in range(1, 13)}
    moon_sign = int(raw_bodies["Moon"] / 30) + 1
    moon_data = {i: [] for i in range(1, 13)}
    
    for p_name, p_deg in raw_bodies.items():
        if p_name == "Ascendant": continue
        p_sign = int(p_deg / 30) + 1
        sun_data[((p_sign - sun_sign) % 12) + 1].append(p_name)
        moon_data[((p_sign - moon_sign) % 12) + 1].append(p_name)
        
    charts_data["Sun"] = sun_data
    charts_data["Moon"] = moon_data

    # --- PLANET DETAILS (D1) + STATUS RESTORED ---
    planet_details = []
    nak_list = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
    zodiac_list = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    
    for p_name, p_deg in raw_bodies.items():
        sign_name = zodiac_list[int(p_deg / 30) % 12]
        nak_name = nak_list[int(p_deg / (360/27)) % 27]
        house_d1 = ((int(p_deg/30) - int(raw_bodies["Ascendant"]/30)) % 12) + 1
        
        # RESTORED: Status Calculation
        status = get_planet_status(p_name, sign_name)
        
        planet_details.append({
            "Planet": p_name, "Sign": sign_name, "Nakshatra": nak_name,
            "Degree": f"{int(p_deg%30)}°{int((p_deg%30%1)*60)}'", 
            "House": house_d1, "Status": status
        })

    # KP Data
    kp_planets = []
    kp_cusps = []
    for p_name, p_deg in raw_bodies.items():
        k_s, k_st, k_sb = get_kp_lords(p_deg)
        kp_planets.append({"Planet": p_name, "Sign Lord": k_s, "Star Lord": k_st, "Sub Lord": k_sb})

    for i in range(1, len(cusps)):
        if i > 12: break
        c_deg = cusps[i]
        c_s, c_st, c_sb = get_kp_lords(c_deg)
        kp_cusps.append({"Cusp": i, "Degree": f"{int(c_deg%30)}°", "Sign": zodiac_list[int(c_deg/30)%12], "Sign Lord": c_s, "Star Lord": c_st, "Sub Lord": c_sb})

    # Ruling Planets
    day_lords = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]
    ruling_planets = [
        {"Type": "Ascendant", "Sign Lord": kp_planets[0]['Sign Lord'], "Star Lord": kp_planets[0]['Star Lord'], "Sub Lord": kp_planets[0]['Sub Lord']},
        {"Type": "Moon", "Sign Lord": kp_planets[2]['Sign Lord'], "Star Lord": kp_planets[2]['Star Lord'], "Sub Lord": kp_planets[2]['Sub Lord']},
        {"Type": "Day Lord", "Sign Lord": day_lords[birth_dt.weekday()], "Star Lord": "-", "Sub Lord": "-"}
    ]

    moon_pos = raw_bodies["Moon"]
    is_mangalik = "Yes" if planet_details[2]['House'] in [1,4,7,8,12] else "No" 
    
    nak_deg = moon_pos % (360/27)
    charan = int(nak_deg / (360/27/4)) + 1
    
    # Calculate Paya (Footing)
    moon_house = ((int(moon_pos/30) - int(raw_bodies["Ascendant"]/30)) % 12) + 1
    if moon_house in [1, 6, 11]: paya = "Gold (Swarna)"
    elif moon_house in [2, 5, 9]: paya = "Silver (Rajat)"
    elif moon_house in [3, 7, 10]: paya = "Copper (Tamra)"
    else: paya = "Iron (Loha)"

    summary = {
        "Lagna": zodiac_list[int(raw_bodies["Ascendant"]/30) % 12],
        "Rashi": zodiac_list[int(moon_pos/30) % 12],
        "Nakshatra": nak_list[int(moon_pos / (360/27)) % 27],
        "Charan": charan,
        "Mangalik": is_mangalik,
        "Paya": paya,
        "Asc_Sign_ID": int(raw_bodies["Ascendant"] // 30) + 1,
        **calculate_panchang(jd, lat, lon, birth_dt, moon_pos),
        **get_detailed_interpretations(zodiac_list[int(raw_bodies["Ascendant"]/30) % 12]),
        **get_nakshatra_properties(nak_list[int(moon_pos / (360/27)) % 27], zodiac_list[int(moon_pos/30) % 12], charan)
    }

    return charts_data, planet_details, kp_planets, kp_cusps, ruling_planets, summary, raw_bodies

# --- VISUALIZATION ---
def draw_chart(house_planets, asc_sign, style="North", title="Chart"):
    fig, ax = plt.subplots(figsize=(3, 3))
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=8, fontweight='bold', pad=2)
    
    if style == "North":
        ax.plot([0, 1], [1, 0], 'k-', lw=1)
        ax.plot([0, 1], [0, 1], 'k-', lw=1)
        ax.plot([0, 0.5], [0.5, 0], 'k-', lw=1)
        ax.plot([0.5, 1], [0, 0.5], 'k-', lw=1)
        ax.plot([0.5, 1], [1, 0.5], 'k-', lw=1)
        ax.plot([0, 0.5], [0.5, 1], 'k-', lw=1)
        rect = patches.Rectangle((0, 0), 1, 1, linewidth=1, edgecolor='black', facecolor='none')
        ax.add_patch(rect)
        pos = {1: (0.5, 0.8), 2: (0.25, 0.85), 3: (0.15, 0.75), 4: (0.2, 0.5), 5: (0.15, 0.25), 6: (0.25, 0.15), 7: (0.5, 0.2), 8: (0.75, 0.15), 9: (0.85, 0.25), 10: (0.8, 0.5), 11: (0.85, 0.75), 12: (0.75, 0.85)}
        for h, (x, y) in pos.items():
            sign_num = ((asc_sign + h - 2) % 12) + 1
            ax.text(x, y-0.08, str(sign_num), fontsize=6, color='red', ha='center')
            if house_planets[h]:
                ax.text(x, y, "\n".join(house_planets[h]), fontsize=6, fontweight='bold', ha='center', va='center')
    else:
        for i in [0, 0.25, 0.5, 0.75, 1]:
            ax.plot([0, 1], [i, i], 'k-', lw=1)
            ax.plot([i, i], [0, 1], 'k-', lw=1)
        rect = patches.Rectangle((0.25, 0.25), 0.5, 0.5, color='white', zorder=10)
        ax.add_patch(rect)
        ax.text(0.5, 0.5, "Rashi", ha='center', va='center', fontsize=8, fontweight='bold', zorder=11)
        sign_pos = {1: (0.37, 0.87), 2: (0.62, 0.87), 3: (0.87, 0.87), 4: (0.87, 0.62), 5: (0.87, 0.37), 6: (0.87, 0.12), 7: (0.62, 0.12), 8: (0.37, 0.12), 9: (0.12, 0.12), 10: (0.12, 0.37), 11: (0.12, 0.62), 12: (0.12, 0.87)}
        for h, planets in house_planets.items():
            sign = ((asc_sign + h - 2) % 12) + 1
            x, y = sign_pos[sign]
            txt_p = "\n".join(planets)
            if h == 1: txt_p += "\n(Asc)"
            ax.text(x, y, txt_p, fontsize=6, fontweight='bold', ha='center', va='center')
    return fig

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("☸️ TaraVaani")
    lang_opt = st.selectbox("Language (AI Only)", ["English", "Hindi", "Bengali", "Marathi", "Tamil", "Telugu", "Kannada", "Gujarati", "Malayalam"])
    
    st.header("Create Profile")
    n_in = st.text_input("Name", "") 
    g_in = st.selectbox("Gender", ["Male", "Female"])
    d_in = st.date_input("Date of Birth", value=datetime.date(2000, 1, 1), min_value=datetime.date(1900, 1, 1), format="DD/MM/YYYY")
    c1, c2 = st.columns(2)
    hr_in = c1.selectbox("Hour", range(24), index=15)
    mn_in = c2.selectbox("Min", range(60), index=45)
    city_in = st.text_input("City", "Kolkata, India")
    
    if st.button("Generate Kundali", type="primary"):
        with st.spinner("Calculating 19 Charts..."):
            try:
                res = geocoder.geocode(city_in)
                if res:
                    lat, lng = res[0]['geometry']['lat'], res[0]['geometry']['lng']
                    birth_dt = datetime.datetime.combine(d_in, datetime.time(hr_in, mn_in))
                    utc_dt = birth_dt - datetime.timedelta(hours=5, minutes=30)
                    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
                    swe.set_sid_mode(swe.SIDM_LAHIRI)
                    
                    charts, p_dets, kp_p, kp_c, ruling, summ, raw_b = get_planet_positions(jd, lat, lng, birth_dt, lang_opt)
                    
                    st.session_state.current_data = {
                        "Name": n_in, "Gender": g_in, 
                        "Charts": charts, "Planet_Details": p_dets,
                        "KP_Planets": kp_p, "KP_Cusps": kp_c, "Ruling_Planets": ruling,
                        "Summary": summ, "Raw_Bodies": raw_b, "JD": jd, "BirthDate": d_in
                    }
                    st.rerun()
                else: st.error("City not found.")
            except Exception as e: st.error(f"Error: {e}")

# --- 6. MAIN UI ---
if st.session_state.current_data:
    d = st.session_state.current_data
    
    if 'Charts' not in d or 'Paya' not in d['Summary']: 
        st.warning("⚠️ Upgrade Applied. Click 'Generate Kundali' again.")
        st.stop()
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📝 Summary", "🔮 Kundalis", "⭐ KP System", "📊 Charts (19)", "🗓️ Dashas", "🤖 AI Prediction"])
    
    # 1. SUMMARY (NEW LAYOUT)
    with tab1:
        st.markdown(f'<div class="header-box">{d["Name"]} 🙏</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Basic Details")
            st.write(f"**Name:** {d['Name']}")
            st.write(f"**Date:** {d['BirthDate'].strftime('%d %B %Y')}")
            st.write(f"**Place:** {city_in}")
            st.write(f"**Sunrise:** {d['Summary']['Sunrise']}")
            st.write(f"**Sunset:** {d['Summary']['Sunset']}")
            st.write(f"**Ayanamsa:** {d['Summary']['Ayanamsa']}")
            
        with c2:
            st.subheader("Avakahada (Astrological Details)")
            st.write(f"**Varna:** {d['Summary']['Varna']}")
            st.write(f"**Vashya:** {d['Summary']['Vashya']}")
            st.write(f"**Yoni:** {d['Summary']['Yoni']}")
            st.write(f"**Gan:** {d['Summary']['Gana']}")
            st.write(f"**Nadi:** {d['Summary']['Nadi']}")
            st.write(f"**Sign:** {d['Summary']['Rashi']}")
            st.write(f"**Sign Lord:** {d['Summary']['SignLord']}")
            st.write(f"**Nakshatra-Charan:** {d['Summary']['Nakshatra']} ({d['Summary']['Charan']})")

        st.divider()
        st.subheader("Panchang Details")
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            st.write(f"**Tithi:** {d['Summary']['Tithi']}")
            st.write(f"**Karan:** {d['Summary']['Karan']}")
            st.write(f"**Yog:** {d['Summary']['Yoga']}")
        with pc2:
            st.write(f"**Yunja:** {d['Summary']['Nadi']}")
            st.write(f"**Tatva:** {d['Summary']['Tatva']}")
            st.write(f"**Paya:** {d['Summary']['Paya']}")
        with pc3:
            st.write(f"**Name Alphabet:** {d['Summary']['NameAlpha']}")

        st.divider()
        st.subheader("Your Vedic Profile")
        st.markdown(f"**General:**\n{d['Summary']['Gen']}")
        st.markdown(f"**Personality:**\n{d['Summary']['Pers']}")
        st.markdown(f"**Physical Appearance:**\n{d['Summary']['Phys']}")
        st.markdown(f"**Health:**\n{d['Summary']['Health']}")
        st.markdown(f"**Career:**\n{d['Summary']['Career']}")
        st.markdown(f"**Relationships:**\n{d['Summary']['Rel']}")

    # 2. KUNDALIS
    with tab2:
        c_type = st.selectbox("Style:", ["North Indian", "South Indian"])
        style = "North" if "North" in c_type else "South"
        c1, c2 = st.columns(2)
        d1_asc_sign = int(d['Raw_Bodies']['Ascendant'] / 30) + 1
        d9_asc_sign = calculate_varga_sign(d['Raw_Bodies']['Ascendant'], 9)
        with c1: st.pyplot(draw_chart(d['Charts']['D1'], d1_asc_sign, style, "Lagna Chart (D1)"))
        with c2: st.pyplot(draw_chart(d['Charts']['D9'], d9_asc_sign, style, "Navamsa Chart (D9)"))
        
        st.divider()
        st.subheader("Planetary Details & Status")
        st.dataframe(pd.DataFrame(d['Planet_Details']), use_container_width=True)
        
        st.divider()
        with st.expander("📌 Planetary Status Guide (What does it mean?)", expanded=True):
            st.markdown("""
            * **Exalted (Ucha):** Planet is at peak power. Excellent results.
            * **Debilitated (Neecha):** Planet is weak. Results may be challenging.
            * **Own Sign (Swakshetra):** Planet is at home. Strong and comfortable.
            * **Friendly (Mitra):** Planet is in a friend's house. Good cooperation.
            * **Enemy (Shatru):** Planet is in an enemy's house. Uncomfortable/Agitated.
            """)

    # 3. KP SYSTEM
    with tab3:
        st.markdown("### Krishnamurti Paddhati (KP)")
        c1, c2 = st.columns(2)
        with c1: st.pyplot(draw_chart(d['Charts']['Chalit'], int(d['Raw_Bodies']['Ascendant'] / 30) + 1, "North", "Bhav Chalit"))
        with c2: 
            st.write("Ruling Planets")
            st.dataframe(pd.DataFrame(d['Ruling_Planets']), use_container_width=True)
        st.divider()
        c3, c4 = st.columns(2)
        with c3:
            st.write("KP Planets")
            st.dataframe(pd.DataFrame(d['KP_Planets']), use_container_width=True)
        with c4:
            st.write("KP Cusps")
            st.dataframe(pd.DataFrame(d['KP_Cusps']), use_container_width=True)

    # 4. CHARTS (ALL 19)
    with tab4:
        st.subheader("Shodashvarga & Divisional Charts")
        c_style_all = st.selectbox("All Charts Style:", ["North Indian", "South Indian"], key="c_all")
        style_all = "North" if "North" in c_style_all else "South"
        
        chart_list = [
            ("Lagna (D1)", "D1", 1), ("Hora (D2) - Wealth", "D2", 2), ("Drekkana (D3) - Siblings", "D3", 3),
            ("Chaturthamsha (D4) - Luck", "D4", 4), ("Saptamsa (D7) - Children", "D7", 7), ("Navamsa (D9) - Spouse", "D9", 9),
            ("Dasamsa (D10) - Career", "D10", 10), ("Dwadasamsa (D12) - Parents", "D12", 12), ("Shodasamsa (D16) - Vehicles", "D16", 16),
            ("Vimsamsa (D20) - Spiritual", "D20", 20), ("Chaturvimsamsa (D24) - Learning", "D24", 24), ("Saptavimsamsa (D27) - Strength", "D27", 27),
            ("Trimsamsa (D30) - Misfortune", "D30", 30), ("Khavedamsa (D40) - Auspicious", "D40", 40), ("Akshavedamsa (D45) - General", "D45", 45),
            ("Shastiamsa (D60) - Karma", "D60", 60), ("Chalit (Bhav)", "Chalit", 1), ("Sun Chart", "Sun", 1), ("Moon Chart", "Moon", 1)
        ]
        
        rows = [chart_list[i:i+3] for i in range(0, len(chart_list), 3)]
        for row in rows:
            cols = st.columns(3)
            for idx, (title, key, v_num) in enumerate(row):
                with cols[idx]:
                    if key == "Sun": asc_s = int(d['Raw_Bodies']['Sun'] / 30) + 1
                    elif key == "Moon": asc_s = int(d['Raw_Bodies']['Moon'] / 30) + 1
                    else: asc_s = calculate_varga_sign(d['Raw_Bodies']['Ascendant'], v_num)
                    st.pyplot(draw_chart(d['Charts'][key], asc_s, style_all, title))

    # 5. DASHAS
    with tab5:
        st.markdown("### Vimshottari Dasha Analysis")
        md_list = calculate_vimshottari_structure(d['JD'], d['BirthDate'])
        md_data = [{"Lord": m['Lord'], "Start": m['Start'].strftime('%d-%b-%Y'), "End": m['End'].strftime('%d-%b-%Y')} for m in md_list]
        st.dataframe(pd.DataFrame(md_data), use_container_width=True)
        
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
        
        # --- LEVEL 4: SOOKSHMA ---
        st.divider()
        
        pd_opts = [f"{p['Lord']} (ends {p['End'].strftime('%d-%b-%Y')})" for p in pd_list]
        sel_pd_idx = st.selectbox("⬇️ Select Pratyantar:", range(len(pd_list)), format_func=lambda x: pd_opts[x])
        sel_pd = pd_list[sel_pd_idx]
        
        st.markdown(f"**Sookshma Dasha under {sel_pd['Lord']}**")
        sd_list = get_sub_periods(sel_pd['Lord'], sel_pd['Start'], sel_pd['Duration'])
        sd_data = [{"Lord": s['Lord'], "Start": s['Start'].strftime('%d-%b'), "End": s['End'].strftime('%d-%b')} for s in sd_list]
        st.dataframe(pd.DataFrame(sd_data), use_container_width=True)
        
        sd_opts = [f"{s['Lord']} (ends {s['End'].strftime('%d-%b')})" for s in sd_list]
        sel_sd_idx = st.selectbox("⬇️ Select Sookshma:", range(len(sd_list)), format_func=lambda x: sd_opts[x])
        sel_sd = sd_list[sel_sd_idx]
        
        st.markdown(f"**Prana Dasha under {sel_sd['Lord']}**")
        pn_list = get_sub_periods(sel_sd['Lord'], sel_sd['Start'], sel_sd['Duration'])
        pn_data = [{"Lord": p['Lord'], "Start": p['Start'].strftime('%d-%b %H:%M'), "End": p['End'].strftime('%d-%b %H:%M')} for p in pn_list]
        st.dataframe(pd.DataFrame(pn_data), use_container_width=True)
        
        pn_opts = [f"{p['Lord']} (ends {p['End'].strftime('%d-%b %H:%M')})" for p in pn_list]
        sel_pn_idx = st.selectbox("⬇️ Select Prana:", range(len(pn_list)), format_func=lambda x: pn_opts[x])
        sel_pn = pn_list[sel_pn_idx]
        
        st.markdown(f"**Deha Dasha (Final) under {sel_pn['Lord']}**")
        dd_list = get_sub_periods(sel_pn['Lord'], sel_pn['Start'], sel_pn['Duration'])
        dd_data = [{"Lord": d['Lord'], "Start": d['Start'].strftime('%d-%b %H:%M'), "End": d['End'].strftime('%d-%b %H:%M')} for d in dd_list]
        st.dataframe(pd.DataFrame(dd_data), use_container_width=True)

    # 6. AI
    with tab6:
        st.subheader(f"Ask TaraVaani ({lang_opt})")
        q_topic = st.selectbox("Topic", ["General Life", "Career", "Marriage", "Health", "Wealth"])
        if st.button("✨ Get Prediction"):
            prompt = f"Act as Vedic Astrologer TaraVaani. User: {d['Name']} ({d['Gender']}). Planetary Positions: {str(d['Planet_Details'])}. Question: Predict about {q_topic}. Start with 'Radhe Radhe 🙏'. Answer in {lang_opt}."
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
