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
    .stExpander { border: 1px solid #333; border-radius: 5px; }
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

# --- 3. SESSION STATE ---
if 'user_id' not in st.session_state: st.session_state.user_id = "suman_naskar_admin"
if 'current_data' not in st.session_state: st.session_state.current_data = None

# --- 4. ASTROLOGY ENGINE ---

def get_planet_positions(jd):
    """Calculates planet positions"""
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, 0, 0, b'P') 
    asc_deg = (ascmc[0] - ayanamsa) % 360
    asc_sign = int(asc_deg // 30) + 1 

    planet_map = {0:"Sun", 1:"Moon", 4:"Mars", 2:"Merc", 5:"Jup", 3:"Ven", 6:"Sat", 11:"Rahu", 10:"Ketu"}
    house_planets = {i: [] for i in range(1, 13)}
    planet_details = []

    # Nakshatra List
    nak_list = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
    
    # Zodiac List
    zodiac_list = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

    for pid, name in planet_map.items():
        if name == "Ketu":
            rahu_pos = swe.calc_ut(jd, 11, swe.FLG_SIDEREAL)[0][0]
            pos = (rahu_pos + 180) % 360
        else:
            pos = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]
            
        sign = int(pos // 30) + 1 
        deg = pos % 30
        house_num = ((sign - asc_sign) % 12) + 1
        
        nak_idx = int(pos / (360/27)) % 27
        nak_name = nak_list[nak_idx]
        sign_name = zodiac_list[sign-1]
        
        house_planets[house_num].append(f"{name}") 
        planet_details.append({
            "Name": name, "Sign": sign, "SignName": sign_name, 
            "Deg": deg, "House": house_num, "Nakshatra": nak_name
        })

    # Add Lagna to details
    l_sign_name = zodiac_list[asc_sign-1]
    l_nak_idx = int(asc_deg / (360/27)) % 27
    l_nak = nak_list[l_nak_idx]
    
    # Basic Summary Data
    summary = {
        "Lagna": l_sign_name,
        "Lagna_Nak": l_nak,
        "Moon_Sign": next((p['SignName'] for p in planet_details if p['Name']=='Moon'), "Unknown"),
        "Moon_Nak": next((p['Nakshatra'] for p in planet_details if p['Name']=='Moon'), "Unknown"),
    }

    return house_planets, asc_sign, planet_details, summary

# --- CHART DRAWING FUNCTIONS ---
def draw_north_indian_chart(house_planets, asc_sign):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_aspect('equal')
    ax.axis('off')
    ax.plot([0, 1], [1, 0], 'k-', lw=2)
    ax.plot([0, 1], [0, 1], 'k-', lw=2)
    ax.plot([0, 0.5], [0.5, 0], 'k-', lw=2)
    ax.plot([0.5, 1], [0, 0.5], 'k-', lw=2)
    ax.plot([0.5, 1], [1, 0.5], 'k-', lw=2)
    ax.plot([0, 0.5], [0.5, 1], 'k-', lw=2)
    rect = patches.Rectangle((0, 0), 1, 1, linewidth=2, edgecolor='black', facecolor='none')
    ax.add_patch(rect)
    positions = {1: (0.5, 0.8), 2: (0.25, 0.85), 3: (0.15, 0.75), 4: (0.2, 0.5), 5: (0.15, 0.25), 6: (0.25, 0.15), 7: (0.5, 0.2), 8: (0.75, 0.15), 9: (0.85, 0.25), 10: (0.8, 0.5), 11: (0.85, 0.75), 12: (0.75, 0.85)}
    for house, (x, y) in positions.items():
        sign_num = ((asc_sign + house - 2) % 12) + 1
        ax.text(x, y-0.05, str(sign_num), fontsize=10, color='red', ha='center')
        planets = house_planets[house]
        if planets:
            p_text = "\n".join(planets)
            ax.text(x, y, p_text, fontsize=9, fontweight='bold', ha='center', va='center')
    return fig

def draw_south_indian_chart(planet_details):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_aspect('equal')
    ax.axis('off')
    for i in [0, 0.25, 0.5, 0.75, 1]:
        ax.plot([0, 1], [i, i], 'k-', lw=1)
        ax.plot([i, i], [0, 1], 'k-', lw=1)
    rect = patches.Rectangle((0.25, 0.25), 0.5, 0.5, color='white', zorder=10)
    ax.add_patch(rect)
    ax.text(0.5, 0.5, "Rashi", ha='center', va='center', fontsize=12, fontweight='bold', zorder=11)
    sign_pos = {1: (0.37, 0.87), 2: (0.62, 0.87), 3: (0.87, 0.87), 4: (0.87, 0.62), 5: (0.87, 0.37), 6: (0.87, 0.12), 7: (0.62, 0.12), 8: (0.37, 0.12), 9: (0.12, 0.12), 10: (0.12, 0.37), 11: (0.12, 0.62), 12: (0.12, 0.87)}
    sign_planets = {i: [] for i in range(1, 13)}
    for p in planet_details: sign_planets[p['Sign']].append(p['Name'])
    for sign, (x, y) in sign_pos.items():
        if sign_planets[sign]: ax.text(x, y, "\n".join(sign_planets[sign]), ha='center', va='center', fontsize=8, fontweight='bold')
    return fig

# --- DASHA CALCULATION ENGINE ---
def calculate_vimshottari(jd, birth_date):
    moon_pos = swe.calc_ut(jd, 1, swe.FLG_SIDEREAL)[0][0]
    nak_deg = (moon_pos * (27/360)) 
    nak_idx = int(nak_deg)
    balance_prop = 1 - (nak_deg - nak_idx)
    
    lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    years = [7, 20, 6, 10, 7, 18, 16, 19, 17]
    
    start_lord_idx = nak_idx % 9
    start_date = birth_date
    
    # Calculate Balance of first Dasha
    first_dur = years[start_lord_idx] * balance_prop
    
    dashas = []
    
    # 1. First Dasha (Balance)
    end_date = start_date + datetime.timedelta(days=first_dur*365.25)
    dashas.append({"Lord": lords[start_lord_idx], "Start": start_date, "End": end_date, "Duration": first_dur})
    current_date = end_date
    
    # 2. Subsequent Dashas
    for i in range(1, 9):
        idx = (start_lord_idx + i) % 9
        lord = lords[idx]
        dur = years[idx]
        end_date = current_date + datetime.timedelta(days=dur*365.25)
        dashas.append({"Lord": lord, "Start": current_date, "End": end_date, "Duration": dur})
        current_date = end_date
        
    return dashas

def calculate_antardasha(mahadasha_lord, start_date):
    # Standard Vimshottari Antardasha Proportions
    lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    years = [7, 20, 6, 10, 7, 18, 16, 19, 17]
    
    # Find index of Mahadasha Lord to start sub-cycle
    try:
        start_idx = lords.index(mahadasha_lord)
    except: return []

    sub_periods = []
    curr_date = start_date
    
    # Total duration of Mahadasha
    total_md_years = years[start_idx]
    
    # Antardasha follows same order, starting from MD lord
    for i in range(9):
        idx = (start_idx + i) % 9
        sub_lord = lords[idx]
        sub_years = years[idx]
        
        # Formula: MD Years * AD Years / 120
        ad_duration = (total_md_years * sub_years) / 120
        end_date = curr_date + datetime.timedelta(days=ad_duration*365.25)
        
        sub_periods.append({"SubLord": sub_lord, "End": end_date})
        curr_date = end_date
        
    return sub_periods

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("☸️ TaraVaani")
    lang_opt = st.selectbox("Language", ["English", "Hindi", "Bengali", "Marathi", "Tamil", "Telugu", "Kannada", "Gujarati", "Malayalam"])
    
    st.header("Profile")
    n_in = st.text_input("Name", "Suman Naskar")
    g_in = st.selectbox("Gender", ["Male", "Female"])
    d_in = st.date_input("DOB", value=datetime.date(1993, 4, 23), min_value=datetime.date(1900,1,1))
    c1, c2 = st.columns(2)
    hr_in = c1.selectbox("Hour", range(24), index=15)
    mn_in = c2.selectbox("Min", range(60), index=45)
    city_in = st.text_input("City", "Kolkata, India")
    
    with st.expander("⚙️ Advanced Settings"):
        ayanamsa_opt = st.selectbox("Calculation System", ["Lahiri (Standard)", "Raman (Traditional)", "KP (Krishnamurti)"])
    
    if st.button("Generate Kundali", type="primary"):
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
                    
                    house_planets, asc_sign, planet_details, summary = get_planet_positions(jd)
                    vim_dashas = calculate_vimshottari(jd, d_in)
                    
                    st.session_state.current_data = {
                        "Name": n_in, "Gender": g_in, 
                        "House_Planets": house_planets, "Asc_Sign": asc_sign,
                        "Planet_Details": planet_details,
                        "Summary": summary,
                        "Vim_Dashas": vim_dashas,
                        "Full_Chart_Text": str(planet_details) 
                    }
                    st.rerun()
                else: st.error("City not found.")
            except Exception as e: st.error(f"Error: {e}")

# --- 6. MAIN UI ---
if st.session_state.current_data:
    d = st.session_state.current_data
    
    # --- TAB ORDER: Summary -> Charts -> Dasha -> AI ---
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Summary", "📊 Charts", "🗓️ Dashas", "🤖 AI Prediction"])
    
    # 1. SUMMARY TAB
    with tab1:
        st.markdown(f'<div class="header-box">Janma Kundali: {d["Name"]} 🙏</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Lagna", d['Summary']['Lagna'])
        c2.metric("Lagna Nakshatra", d['Summary']['Lagna_Nak'])
        c3.metric("Moon Sign", d['Summary']['Moon_Sign'])
        c4.metric("Moon Nakshatra", d['Summary']['Moon_Nak'])
        
        st.divider()
        st.subheader("Planetary Positions")
        p_data = {p['Name']: f"{p['SignName']} ({p['Deg']:.2f}°)" for p in d['Planet_Details']}
        st.table(pd.DataFrame(p_data.items(), columns=["Planet", "Position"]))
        
    # 2. CHARTS TAB
    with tab2:
        c_type = st.radio("Select Chart Style:", ["North Indian (Diamond)", "South Indian (Square)"], horizontal=True)
        
        st.caption(f"Showing {c_type} Chart based on {d['Summary']['Lagna']} Lagna.")
        
        if "North" in c_type:
            fig = draw_north_indian_chart(d['House_Planets'], d['Asc_Sign'])
            st.pyplot(fig)
            st.info("ℹ️ **North Indian Chart:** Houses are fixed. The top diamond is always the 1st House (Lagna). The numbers represent the Zodiac Signs (1=Aries, 2=Taurus...).")
        else:
            fig = draw_south_indian_chart(d['Planet_Details'])
            st.pyplot(fig)
            st.info("ℹ️ **South Indian Chart:** Signs are fixed. The boxes represent Zodiac Signs starting from Aries (Top-2nd Box) moving clockwise. Lagna is marked as 'Asc' or derived from context.")
            
    # 3. DASHA TAB (Drill Down)
    with tab3:
        d_system = st.radio("Dasha System:", ["Vimshottari", "Yogini (Coming Soon)"], horizontal=True)
        
        if "Vimshottari" in d_system:
            st.subheader("Vimshottari Mahadasha (Click to Expand)")
            st.caption("Drill down to see Antardashas (Sub-periods)")
            
            for md in d['Vim_Dashas']:
                # Label for the Expander (Mahadasha)
                label = f"**{md['Lord']} Mahadasha** | {md['Start'].year} - {md['End'].year}"
                
                with st.expander(label):
                    # Calculate Antardashas on the fly for this MD
                    sub_periods = calculate_antardasha(md['Lord'], md['Start'])
                    
                    # Display as a clean list/table
                    if sub_periods:
                        sub_data = []
                        for sub in sub_periods:
                            sub_data.append({"Antardasha Lord": sub['SubLord'], "Ends On": sub['End'].strftime("%d-%b-%Y")})
                        st.table(pd.DataFrame(sub_data))
                    else:
                        st.write("Calculation detail unavailable.")
        else:
            st.warning("Yogini Dasha logic is being implemented in the next update!")

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
                st.error(f"AI Error: {e}")
                if "404" in str(e): st.warning("⚠️ Google Billing Check Pending. Use Free Key or wait 24h.")
else:
    st.title("☸️ TaraVaani")
    st.info("👈 Enter details to generate chart.")
