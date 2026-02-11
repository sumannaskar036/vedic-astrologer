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

def get_gana_yoni(nak):
    data = {
        "Ashwini": ("Deva", "Horse"), "Bharani": ("Manushya", "Elephant"), "Krittika": ("Rakshasa", "Goat"), "Rohini": ("Manushya", "Snake"), "Mrigashira": ("Deva", "Snake"), "Ardra": ("Manushya", "Dog"), "Punarvasu": ("Deva", "Cat"), "Pushya": ("Deva", "Goat"), "Ashlesha": ("Rakshasa", "Cat"), "Magha": ("Rakshasa", "Rat"), "Purva Phalguni": ("Manushya", "Rat"), "Uttara Phalguni": ("Manushya", "Cow"), "Hasta": ("Deva", "Buffalo"), "Chitra": ("Rakshasa", "Tiger"), "Swati": ("Deva", "Buffalo"), "Vishakha": ("Rakshasa", "Tiger"), "Anuradha": ("Deva", "Deer"), "Jyeshtha": ("Rakshasa", "Deer"), "Mula": ("Rakshasa", "Dog"), "Purva Ashadha": ("Manushya", "Monkey"), "Uttara Ashadha": ("Manushya", "Mongoose"), "Shravana": ("Deva", "Monkey"), "Dhanishta": ("Rakshasa", "Lion"), "Shatabhisha": ("Rakshasa", "Horse"), "Purva Bhadrapada": ("Manushya", "Lion"), "Uttara Bhadrapada": ("Manushya", "Cow"), "Revati": ("Deva", "Elephant")
    }
    return data.get(nak, ("Unknown", "Unknown"))

def get_planet_positions(jd, lat, lon):
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lon, b'P') 
    asc_deg = (ascmc[0] - ayanamsa) % 360
    asc_sign = int(asc_deg // 30) + 1 

    planet_map = {0:"Sun", 1:"Moon", 4:"Mars", 2:"Merc", 5:"Jup", 3:"Ven", 6:"Sat", 11:"Rahu", 10:"Ketu"}
    house_planets = {i: [] for i in range(1, 13)}
    planet_details = []

    nak_list = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
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

    l_sign_name = zodiac_list[asc_sign-1]
    
    moon_data = next((p for p in planet_details if p['Name']=='Moon'), None)
    moon_sign = moon_data['SignName'] if moon_data else "Unknown"
    moon_nak = moon_data['Nakshatra'] if moon_data else "Unknown"
    
    gana, yoni = get_gana_yoni(moon_nak)
    
    summary = {
        "Lagna": l_sign_name,
        "Rashi": moon_sign,
        "Nakshatra": moon_nak,
        "Gana": gana,
        "Yoni": yoni,
        "Asc_Sign_ID": asc_sign 
    }

    return house_planets, asc_sign, planet_details, summary

# --- STATIC INTERPRETATIONS ---
def get_chart_interpretations(asc_sign_id):
    interpretations = {
        1: {"Personality": "Energetic, courageous, impatient, and direct. You are a natural leader but can be impulsive.", "Physical": "Medium height, athletic build, ruddy complexion, possibly a prominent head or face.", "Career": "Military, police, engineering, sports, or any field requiring initiative.", "Health": "Prone to headaches, fevers, and injuries to the head.", "Rel": "Passionate and protective, but may be argumentative."},
        2: {"Personality": "Reliable, patient, practical, and devoted. You love luxury and stability but can be stubborn.", "Physical": "Solid build, thick neck, attractive face, clear eyes.", "Career": "Banking, arts, cooking, farming, or luxury goods.", "Health": "Throat issues, thyroid problems, or weight gain.", "Rel": "Loyal and sensual, seeks long-term stability."},
        3: {"Personality": "Adaptable, outgoing, and intelligent. You love communication but can be indecisive.", "Physical": "Tall, slender, quick movements, expressive hands.", "Career": "Journalism, writing, sales, teaching, or IT.", "Health": "Respiratory issues, nervous system disorders, or arm injuries.", "Rel": "Fun-loving and flirtatious, needs intellectual stimulation."},
        4: {"Personality": "Emotional, intuitive, and nurturing. You are attached to home and family but can be moody.", "Physical": "Round face, soft features, tendency to gain weight in midsection.", "Career": "Nursing, teaching, real estate, hospitality, or history.", "Health": "Stomach issues, digestive problems, or chest congestion.", "Rel": "Deeply caring and protective, seeks emotional security."},
        5: {"Personality": "Confident, generous, and creative. You love attention and leading but can be arrogant.", "Physical": "Broad shoulders, majestic appearance, prominent chin or nose.", "Career": "Politics, entertainment, management, or government.", "Health": "Heart issues, back problems, or blood pressure.", "Rel": "Passionate and dramatic, needs admiration and loyalty."},
        6: {"Personality": "Analytical, meticulous, and practical. You are a perfectionist but can be overly critical.", "Physical": "Slender build, youthful appearance, sharp features.", "Career": "Accounting, medicine, editing, service, or coding.", "Health": "Digestive issues, intestinal problems, or nervous tension.", "Rel": "Practical and devoted, serves their partner but may nitpick."},
        7: {"Personality": "Diplomatic, charming, and social. You value harmony but can be indecisive.", "Physical": "Well-proportioned body, attractive smile, pleasing appearance.", "Career": "Law, fashion, design, diplomacy, or counseling.", "Health": "Kidney issues, lower back pain, or skin problems.", "Rel": "Romantic and partnership-oriented, hates being alone."},
        8: {"Personality": "Intense, secretive, and magnetic. You are determined but can be possessive.", "Physical": "Strong build, piercing eyes, prominent brows.", "Career": "Research, surgery, occult, detective work, or mining.", "Health": "Reproductive system issues, bladder problems, or hidden ailments.", "Rel": "Deeply emotional and loyal, but prone to jealousy."},
        9: {"Personality": "Optimistic, adventurous, and philosophical. You love freedom but can be blunt.", "Physical": "Tall, athletic, broad forehead, jovial expression.", "Career": "Teaching, publishing, religion, travel, or law.", "Health": "Hip/thigh injuries, liver issues, or weight gain.", "Rel": "Fun and adventurous, needs freedom in relationships."},
        10: {"Personality": "Disciplined, ambitious, and practical. You work hard but can be pessimistic.", "Physical": "Lean build, prominent knees, serious expression.", "Career": "Business, administration, construction, or mining.", "Health": "Knee problems, skin issues, or arthritis.", "Rel": "Responsible and committed, takes relationships seriously."},
        11: {"Personality": "Innovative, friendly, and humanitarian. You value intellect but can be detached.", "Physical": "Tall, unique features, possibly erratic movements.", "Career": "Technology, science, social work, or aviation.", "Health": "Ankle issues, circulation problems, or nervous disorders.", "Rel": "Friendly and unconventional, values friendship over romance."},
        12: {"Personality": "Compassionate, imaginative, and sensitive. You are spiritual but can be escapist.", "Physical": "Soft features, dreamy eyes, possibly shorter stature.", "Career": "Film, photography, spirituality, healing, or charity.", "Health": "Foot issues, lymphatic problems, or sleep disorders.", "Rel": "Idealistic and self-sacrificing, seeks a soul connection."}
    }
    return interpretations.get(asc_sign_id, {})

# --- VISUALIZATION ---
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

# --- DASHA ENGINE (6 LEVELS) ---
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
                    
                    house_planets, asc_sign, planet_details, summary = get_planet_positions(jd, lat, lng)
                    
                    st.session_state.current_data = {
                        "Name": n_in, "Gender": g_in, 
                        "House_Planets": house_planets, "Asc_Sign": asc_sign,
                        "Planet_Details": planet_details,
                        "Summary": summary,
                        "Full_Chart_Text": str(planet_details),
                        "JD": jd, "BirthDate": d_in
                    }
                    st.rerun()
                else: st.error("City not found.")
            except Exception as e: st.error(f"Error: {e}")

# --- 6. MAIN UI ---
if st.session_state.current_data:
    d = st.session_state.current_data
    
    # SAFETY: Ensure new structure exists
    if 'Summary' not in d or 'Gana' not in d['Summary']:
        st.warning("⚠️ Applying updates. Please click 'Generate Kundali' again.")
        st.stop()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Summary", "📊 Charts", "🗓️ Dashas", "🤖 AI Prediction"])
    
    # 1. SUMMARY TAB
    with tab1:
        st.markdown(f'<div class="header-box">Janma Kundali: {d["Name"]} 🙏</div>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Lagna", d['Summary']['Lagna'])
        c2.metric("Rashi", d['Summary']['Rashi'])
        c3.metric("Nakshatra", d['Summary']['Nakshatra'])
        c4.metric("Gana", d['Summary']['Gana'])
        c5.metric("Yoni", d['Summary']['Yoni'])
        st.divider()
        st.subheader("Planetary Positions")
        p_data = {p['Name']: f"{p['SignName']} ({p['Deg']:.2f}°)" for p in d['Planet_Details']}
        st.table(pd.DataFrame(p_data.items(), columns=["Planet", "Position"]))
        
    # 2. CHARTS TAB (With Interpretations)
    with tab2:
        c_type = st.selectbox("Select Chart Style:", ["North Indian (Diamond)", "South Indian (Square)"])
        
        if "North" in c_type:
            fig = draw_north_indian_chart(d['House_Planets'], d['Asc_Sign'])
            st.pyplot(fig)
        else:
            fig = draw_south_indian_chart(d['Planet_Details'])
            st.pyplot(fig)
            
        st.divider()
        st.subheader("Chart Analysis")
        interp = get_chart_interpretations(d['Summary']['Asc_Sign_ID'])
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**🌟 Personality:**\n{interp['Personality']}")
            st.markdown(f"**💪 Physical:**\n{interp['Physical']}")
            st.markdown(f"**❤️ Relationships:**\n{interp['Rel']}")
        with c2:
            st.markdown(f"**💼 Career:**\n{interp['Career']}")
            st.markdown(f"**🏥 Health:**\n{interp['Health']}")
            
    # 3. DASHA TAB (6 Levels)
    with tab3:
        d_system = st.radio("Dasha System:", ["Vimshottari", "Yogini (Coming Soon)"], horizontal=True)
        
        if "Vimshottari" in d_system:
            st.caption("Drill Down Sequence: Mahadasha → Antar → Pratyantar → Sookshma → Prana → Deha")
            
            # Level 1: MD
            md_list = calculate_vimshottari_structure(d['JD'], d['BirthDate'])
            md_names = [f"{m['Lord']} ({m['Start'].year}-{m['End'].year})" for m in md_list]
            sel_md_idx = st.selectbox("1. Mahadasha", range(len(md_list)), format_func=lambda x: md_names[x])
            sel_md = md_list[sel_md_idx]
            
            # Level 2: AD
            ad_list = get_sub_periods(sel_md['Lord'], sel_md['Start'], sel_md['FullYears'])
            ad_names = [f"{a['Lord']} (ends {a['End'].strftime('%Y-%m-%d')})" for a in ad_list]
            sel_ad_idx = st.selectbox("2. Antardasha", range(len(ad_list)), format_func=lambda x: ad_names[x])
            sel_ad = ad_list[sel_ad_idx]
            
            # Level 3: PD
            pd_list = get_sub_periods(sel_ad['Lord'], sel_ad['Start'], sel_ad['Duration'])
            pd_names = [f"{p['Lord']} (ends {p['End'].strftime('%Y-%m-%d')})" for p in pd_list]
            sel_pd_idx = st.selectbox("3. Pratyantardasha", range(len(pd_list)), format_func=lambda x: pd_names[x])
            sel_pd = pd_list[sel_pd_idx]
            
            # Level 4: Sookshma
            sd_list = get_sub_periods(sel_pd['Lord'], sel_pd['Start'], sel_pd['Duration'])
            sd_names = [f"{s['Lord']} (ends {s['End'].strftime('%d-%b')})" for s in sd_list]
            sel_sd_idx = st.selectbox("4. Sookshma Dasha", range(len(sd_list)), format_func=lambda x: sd_names[x])
            sel_sd = sd_list[sel_sd_idx]
            
            # Level 5: Prana
            pn_list = get_sub_periods(sel_sd['Lord'], sel_sd['Start'], sel_sd['Duration'])
            pn_names = [f"{p['Lord']} (ends {p['End'].strftime('%d-%b %H:%M')})" for p in pn_list]
            sel_pn_idx = st.selectbox("5. Prana Dasha", range(len(pn_list)), format_func=lambda x: pn_names[x])
            sel_pn = pn_list[sel_pn_idx]
            
            # Level 6: Deha (Table)
            st.markdown(f"**6. Deha Dasha (Final Level)** under {sel_pn['Lord']} Prana")
            dd_list = get_sub_periods(sel_pn['Lord'], sel_pn['Start'], sel_pn['Duration'])
            
            deha_data = [{"Lord": d['Lord'], "Ends": d['End'].strftime('%d-%b-%Y %H:%M')} for d in dd_list]
            st.table(pd.DataFrame(deha_data))

        else:
            st.info("Yogini Dasha Logic (Coming Update)")

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
