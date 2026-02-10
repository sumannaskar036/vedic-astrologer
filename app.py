import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from opencage.geocoder import OpenCageGeocode
import time

# --- 1. CONFIGURATION & CSS ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="wide")

# Custom CSS matching your "App Name.png" Drawing
st.markdown("""
<style>
    /* Global Dark Theme */
    .stApp { background-color: #121212; color: #E0E0E0; }
    
    /* 1. TOP HEADER (Pinkish/White) */
    .top-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 15px 15px; background-color: #F8BBD0; color: #880E4F;
        border-radius: 0 0 15px 15px; font-weight: bold; position: sticky; top: 0; z-index: 999;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    /* 2. HERO RIBBON (Red - Horoscope & Matching) */
    .hero-container {
        display: flex; gap: 15px; margin: 20px 0;
    }
    .hero-card {
        flex: 1; background: linear-gradient(135deg, #D32F2F 0%, #B71C1C 100%);
        padding: 20px; border-radius: 15px; text-align: center;
        color: white; box-shadow: 0 4px 10px rgba(211, 47, 47, 0.4);
        cursor: pointer; transition: transform 0.1s;
    }
    .hero-card:active { transform: scale(0.98); }
    .hero-icon { font-size: 30px; margin-bottom: 8px; }
    .hero-title { font-size: 16px; font-weight: 600; }

    /* 3. PROFILE RIBBON (Purple - Horizontal Scroll) */
    .profile-section-title { font-size: 14px; color: #B0BEC5; margin: 10px 0 5px 5px; }
    .profile-scroll-container {
        background: linear-gradient(90deg, #7B1FA2 0%, #4A148C 100%);
        padding: 15px; border-radius: 15px; overflow-x: auto; white-space: nowrap;
        scrollbar-width: none; margin-bottom: 20px;
    }
    .profile-pill {
        display: inline-block; background-color: rgba(255,255,255,0.15); color: white;
        padding: 10px 20px; border-radius: 12px; margin-right: 15px;
        text-align: center; min-width: 80px; cursor: pointer; border: 1px solid rgba(255,255,255,0.2);
    }
    .profile-pill.active {
        background-color: #FFD700; color: #3e2723; font-weight: bold; border: 2px solid white;
    }

    /* 4. TABS & DATA */
    .stTabs [data-baseweb="tab-list"] { 
        background-color: #3E2723; padding: 5px; border-radius: 10px; gap: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px; background-color: transparent; color: #D7CCC8; border-radius: 5px; flex: 1;
    }
    .stTabs [aria-selected="true"] {
        background-color: #D32F2F !important; color: white !important; font-weight: bold;
    }
    
    /* 5. BOTTOM NAV (Sticky) */
    .bottom-nav-spacer { height: 90px; }
    .bottom-nav {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #1F1F1F; border-top: 1px solid #333;
        padding: 10px 0; display: flex; justify-content: space-around; z-index: 9999;
    }

    /* Hide Streamlit Default UI */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. SETUP ---
if not firebase_admin._apps:
    try:
        # Handling potential newline issues in keys
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
    except: st.warning("Firebase Config Warning")

db = firestore.client()

try:
    geocoder = OpenCageGeocode(st.secrets["OPENCAGE_API_KEY"])
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except: pass

# --- 3. SESSION STATE ---
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'onboarding_complete' not in st.session_state: st.session_state.onboarding_complete = False
if 'wallet_balance' not in st.session_state: st.session_state.wallet_balance = 0
if 'active_profile' not in st.session_state: st.session_state.active_profile = None 
if 'page_view' not in st.session_state: st.session_state.page_view = "Home"

# --- 4. ENGINE ---
def calculate_chart_data(name, gender, dt, tm, city):
    # Setup Moshier for stability
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    # Geocoding (Simulated fallback if API fails)
    try:
        res = geocoder.geocode(city)
        lat, lng = res[0]['geometry']['lat'], res[0]['geometry']['lng']
    except: lat, lng = 28.61, 77.20 # Delhi fallback
    
    birth_dt = datetime.datetime.combine(dt, tm)
    utc_dt = birth_dt - datetime.timedelta(hours=5, minutes=30)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    # Calc Lagna
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lng, b'P')
    asc_deg = (ascmc[0] - ayanamsa) % 360
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lagna = zodiac[int(asc_deg // 30)]
    
    # Calc Rashi (Moon)
    moon_pos = swe.calc_ut(jd, 1, swe.FLG_SIDEREAL | swe.FLG_MOSEPH)[0][0]
    moon_sign = zodiac[int(moon_pos // 30) % 12]
    
    # Calc Nakshatra
    nak_list = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    nak_idx = int(moon_pos / (360/27)) % 27
    nakshatra = nak_list[nak_idx]
    
    # Calc Full Chart
    planet_map = {"Sun": 0, "Moon": 1, "Mars": 4, "Mercury": 2, "Jupiter": 5, "Venus": 3, "Saturn": 6, "Rahu": 11}
    chart_text = ""
    for p, pid in planet_map.items():
        try:
            pos = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL | swe.FLG_MOSEPH)[0][0]
            sign = zodiac[int(pos // 30) % 12]
            deg = pos % 30
            chart_text += f"{p}: {sign} ({deg:.2f}°)\n"
        except: pass

    return {
        "Name": name, "Gender": gender, "Lagna": lagna, "Rashi": moon_sign,
        "Nakshatra": nakshatra, "Date": str(dt), "Time": str(tm), "City": city,
        "Full_Chart": chart_text
    }

@st.cache_data(ttl=2) # Short cache for instant updates
def get_profiles(uid):
    try:
        docs = db.collection("users").document(uid).collection("profiles").stream()
        return [doc.to_dict() for doc in docs]
    except: return []

# --- 5. LOGIC: ONBOARDING VS MAIN APP ---

# === A. ONBOARDING SCREEN (First Launch) ===
if not st.session_state.onboarding_complete:
    st.markdown("<h1 style='text-align: center; color: #F8BBD0;'>☸️ TaraVaani</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Begin your Vedic Journey</h3>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div style="background-color: #1E1E1E; padding: 20px; border-radius: 15px;">', unsafe_allow_html=True)
        name = st.text_input("Your Name")
        gender = st.selectbox("Gender", ["Male", "Female"])
        dob = st.date_input("Date of Birth", value=datetime.date(1995, 1, 1))
        t = st.time_input("Time of Birth", value=datetime.time(10, 30))
        city = st.text_input("Place of Birth", "New Delhi, India")
        
        if st.button("✨ Create Profile & Enter", use_container_width=True, type="primary"):
            if name:
                # Create User ID & Save First Profile
                uid = f"{name.replace(' ', '_')}_{int(time.time())}"
                st.session_state.user_id = uid
                
                chart = calculate_chart_data(name, gender, dob, t, city)
                db.collection("users").document(uid).collection("profiles").document(name).set(chart)
                
                # Set States
                st.session_state.active_profile = chart
                st.session_state.onboarding_complete = True
                st.rerun()
            else:
                st.error("Please enter your name.")
        st.markdown('</div>', unsafe_allow_html=True)

# === B. MAIN APP ===
else:
    # Fetch all profiles
    profiles = get_profiles(st.session_state.user_id)
    if not st.session_state.active_profile and profiles:
        st.session_state.active_profile = profiles[0]

    # --- TOP HEADER ---
    st.markdown(f"""
    <div class="top-header">
        <div style="font-size:20px;">☰</div>
        <div style="font-size:18px;">TaraVaani</div>
        <div style="background:#FFF; color:#880E4F; padding:5px 10px; border-radius:15px; font-size:14px;">
            ₹{st.session_state.wallet_balance}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- PAGE ROUTING ---
    
    # 1. HOME PAGE
    if st.session_state.page_view == "Home":
        
        # HERO RIBBON (Red)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            <div class="hero-card">
                <div class="hero-icon">🔮</div>
                <div class="hero-title">Daily<br>Horoscope</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Daily", key="daily", use_container_width=True):
                st.session_state.show_daily = True
        with c2:
            st.markdown("""
            <div class="hero-card">
                <div class="hero-icon">💍</div>
                <div class="hero-title">Kundali<br>Matching</div>
            </div>
            """, unsafe_allow_html=True)
            st.button("Match", key="match", use_container_width=True)

        # PROFILE RIBBON (Purple) - Only if > 1 profile
        if len(profiles) > 1:
            st.markdown('<div class="profile-section-title">Select Profile:</div>', unsafe_allow_html=True)
            st.markdown('<div class="profile-scroll-container">', unsafe_allow_html=True)
            
            # We use columns to simulate the pills inside the container
            cols = st.columns(len(profiles))
            for i, p in enumerate(profiles):
                is_active = (p['Name'] == st.session_state.active_profile['Name'])
                style = "primary" if is_active else "secondary"
                # Using button inside columns for interaction
                if cols[i].button(p['Name'].split()[0], key=f"p_{i}", type=style):
                    st.session_state.active_profile = p
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # DATA TABS (Bottom)
        if st.session_state.active_profile:
            p = st.session_state.active_profile
            st.markdown(f"### 📜 {p['Name']}'s Details")
            
            t1, t2, t3, t4, t5 = st.tabs(["Basic", "Charts", "KP", "Dasha", "Report"])
            
            with t1:
                c1, c2 = st.columns(2)
                c1.metric("Lagna", p['Lagna'])
                c2.metric("Rashi", p['Rashi'])
                c1.metric("Nakshatra", p['Nakshatra'])
                c2.metric("Gender", p['Gender'])
            
            with t2:
                st.text(p['Full_Chart'])
            
            with t3: st.info("KP System Module")
            with t4: st.info("Dasha System Module")
            
            with t5: # AI Report
                st.caption("Ask TaraVaani AI")
                q = st.selectbox("Topic", ["General", "Career", "Love", "Health"])
                if st.button("Generate Report"):
                    prompt = f"Vedic Astrology analysis for {p['Name']}. Lagna: {p['Lagna']}, Rashi: {p['Rashi']}, Planets: {p['Full_Chart']}. Topic: {q}. Keep it short."
                    with st.spinner("Analyzing..."):
                        try:
                            res = model.generate_content(prompt)
                            st.write(res.text)
                        except: st.error("AI Error")

        # Daily Horoscope Modal logic
        if st.session_state.get('show_daily'):
             with st.expander("📅 Daily Forecast", expanded=True):
                 st.write("Today is favorable for new beginnings.")
                 st.success("Lucky Color: Red")
                 if st.button("Close"): 
                     st.session_state.show_daily = False
                     st.rerun()

    # 2. CHAT PAGE
    elif st.session_state.page_view == "Chat":
        st.title("💬 Chat with TaraVaani")
        
        # Simple Chat History
        if "chat_history" not in st.session_state: st.session_state.chat_history = []
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
        if prompt := st.chat_input("Ask about your chart..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant"):
                p = st.session_state.active_profile
                full_p = f"Context: {p['Name']}, {p['Lagna']} Lagna. Q: {prompt}"
                try:
                    r = model.generate_content(full_p)
                    st.markdown(r.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": r.text})
                except: st.error("Network Error")

    # 3. PROFILE PAGE (Settings)
    elif st.session_state.page_view == "Profile":
        st.title("👤 Settings")
        
        # Wallet
        st.markdown(f"## Balance: ₹{st.session_state.wallet_balance}")
        c1, c2, c3 = st.columns(3)
        if c1.button("+ ₹300"): st.session_state.wallet_balance += 300; st.rerun()
        if c2.button("+ ₹500"): st.session_state.wallet_balance += 500; st.rerun()
        if c3.button("+ ₹1000"): st.session_state.wallet_balance += 1000; st.rerun()
        
        st.divider()
        
        # Create New Kundali
        st.subheader("➕ Create New Kundali")
        with st.form("new_k"):
            n = st.text_input("Name")
            g = st.selectbox("Gender", ["Male", "Female"])
            d = st.date_input("Date")
            t = st.time_input("Time")
            c = st.text_input("City", "Mumbai")
            
            if st.form_submit_button("Create Profile"):
                chart = calculate_chart_data(n, g, d, t, c)
                db.collection("users").document(st.session_state.user_id).collection("profiles").document(n).set(chart)
                st.success(f"Added {n}!")
                time.sleep(1)
                st.rerun()
        
        st.divider()
        st.subheader("📜 Saved Profiles")
        for p in profiles:
            st.text(f"• {p['Name']} ({p['Rashi']})")

    # --- BOTTOM NAVIGATION ---
    st.markdown('<div class="bottom-nav-spacer"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    
    # Helper for active state
    def nav_type(page): return "primary" if st.session_state.page_view == page else "secondary"

    if c1.button("🏠 Home", use_container_width=True, type=nav_type("Home")):
        st.session_state.page_view = "Home"
        st.rerun()
    if c2.button("💬 Chat", use_container_width=True, type=nav_type("Chat")):
        st.session_state.page_view = "Chat"
        st.rerun()
    if c3.button("👤 Profile", use_container_width=True, type=nav_type("Profile")):
        st.session_state.page_view = "Profile"
        st.rerun()
