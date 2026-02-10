import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from opencage.geocoder import OpenCageGeocode
import time

# --- 1. APP CONFIGURATION ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="centered", initial_sidebar_state="collapsed")

# --- 2. MOBILE-FIRST CSS (Force Side-by-Side) ---
st.markdown("""
<style>
    /* RESET */
    .stApp { background-color: #121212; color: #E0E0E0; font-family: sans-serif; }
    
    /* Remove Top Padding */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    
    /* HEADER */
    .top-header {
        position: sticky; top: 0; z-index: 999;
        background-color: #F8BBD0; color: #880E4F;
        padding: 15px 20px; margin: 0 -0.5rem;
        display: flex; justify-content: space-between; align-items: center;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    
    /* HERO GRID (FORCE SIDE BY SIDE) */
    .hero-grid {
        display: flex; gap: 10px; margin: 20px 0; width: 100%;
    }
    .hero-col {
        flex: 1; /* Forces equal width */
        min-width: 0; /* Prevents overflow */
    }
    .hero-card {
        background: linear-gradient(135deg, #D32F2F 0%, #B71C1C 100%);
        padding: 15px 5px; border-radius: 15px; text-align: center;
        color: white; height: 100%;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        box-shadow: 0 4px 10px rgba(211, 47, 47, 0.4);
    }
    .hero-icon { font-size: 28px; margin-bottom: 5px; }
    .hero-text { font-size: 13px; font-weight: bold; line-height: 1.2; }

    /* PROFILE SCROLL */
    .profile-scroll {
        display: flex; overflow-x: auto; gap: 10px; padding: 10px 5px;
        scrollbar-width: none; background: #2c0e3a; border-radius: 10px;
    }
    .profile-scroll::-webkit-scrollbar { display: none; }
    
    /* INPUTS */
    div[data-baseweb="input"] { background-color: #2D2D2D !important; border-radius: 10px; border: none; color: white; }
    div[data-baseweb="select"] > div { background-color: #2D2D2D !important; border-radius: 10px; }
    
    /* BOTTOM NAV */
    .bottom-nav-spacer { height: 80px; }
    
    /* Hide Elements */
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Button Tweaks */
    .stButton > button { border-radius: 10px; height: 3em; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 3. DATABASE & API ---
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
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except: pass

# --- 4. SESSION STATE ---
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'onboarding_complete' not in st.session_state: st.session_state.onboarding_complete = False
if 'active_profile' not in st.session_state: st.session_state.active_profile = None 
if 'page_view' not in st.session_state: st.session_state.page_view = "Home"
if 'wallet' not in st.session_state: st.session_state.wallet = 0

# --- 5. CALCULATOR ---
def calculate_chart(name, gender, dt, tm, city):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    try:
        res = geocoder.geocode(city)
        lat, lng = res[0]['geometry']['lat'], res[0]['geometry']['lng']
    except: lat, lng = 22.57, 88.36 
    
    birth_dt = datetime.datetime.combine(dt, tm)
    utc_dt = birth_dt - datetime.timedelta(hours=5, minutes=30)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lng, b'P')
    asc_deg = (ascmc[0] - ayanamsa) % 360
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lagna = zodiac[int(asc_deg // 30)]
    
    moon_pos = swe.calc_ut(jd, 1, swe.FLG_SIDEREAL | swe.FLG_MOSEPH)[0][0]
    moon_sign = zodiac[int(moon_pos // 30) % 12]
    
    nak_idx = int(moon_pos / (360/27)) % 27
    naks = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    nakshatra = naks[nak_idx]

    chart_str = ""
    planets = {0:"Sun", 1:"Moon", 4:"Mars", 2:"Mercury", 5:"Jupiter", 3:"Venus", 6:"Saturn", 11:"Rahu"}
    for pid, p_name in planets.items():
        try:
            p_pos = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL | swe.FLG_MOSEPH)[0][0]
            p_sign = zodiac[int(p_pos // 30) % 12]
            p_deg = p_pos % 30
            chart_str += f"{p_name}: {p_sign} ({p_deg:.2f}°)\n"
        except: pass
        
    return {"Name": name, "Gender": gender, "Lagna": lagna, "Rashi": moon_sign, "Nakshatra": nakshatra, "Full_Chart": chart_str, "Date": str(dt)}

@st.cache_data(ttl=2)
def get_profs(uid):
    try:
        docs = db.collection("users").document(uid).collection("profiles").stream()
        return [d.to_dict() for d in docs]
    except: return []

# --- 6. ONBOARDING ---
if not st.session_state.onboarding_complete:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #F8BBD0;'>☸️ TaraVaani</h1>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div style="background:#1E1E1E; padding:20px; border-radius:15px;">', unsafe_allow_html=True)
        name = st.text_input("Full Name")
        gender = st.selectbox("Gender", ["Male", "Female"])
        
        c1, c2 = st.columns(2)
        dob = c1.date_input("Date", datetime.date(1995,1,1), min_value=datetime.date(1900,1,1), max_value=datetime.date(2100,12,31), format="DD/MM/YYYY")
        
        with c2:
            st.write("Time")
            hc, mc = st.columns(2)
            hr = hc.number_input("Hr", 0, 23, 10, label_visibility="collapsed")
            mn = mc.number_input("Min", 0, 59, 30, label_visibility="collapsed")
        
        city = st.text_input("City", "New Delhi, India")
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("Start Journey 🚀", type="primary"):
            if name:
                uid = f"{name}_{int(time.time())}"
                st.session_state.user_id = uid
                chart = calculate_chart(name, gender, dob, datetime.time(hr, mn), city)
                db.collection("users").document(uid).collection("profiles").document(name).set(chart)
                st.session_state.active_profile = chart
                st.session_state.onboarding_complete = True
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 7. MAIN APP ---
else:
    profs = get_profs(st.session_state.user_id)
    if not st.session_state.active_profile and profs: st.session_state.active_profile = profs[0]
    
    # TOP HEADER
    st.markdown(f"""
    <div class="top-header">
        <div style="font-size:22px;">☰</div>
        <div>TaraVaani</div>
        <div style="background:white; padding:5px 12px; border-radius:15px; font-size:12px; font-weight:800;">
            ₹{st.session_state.wallet}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- HOME VIEW ---
    if st.session_state.page_view == "Home":
        
        # A. HERO SECTION (Custom Side-by-Side Grid)
        # We render HTML for looks, and buttons below for action
        st.markdown("""
        <div class="hero-grid">
            <div class="hero-col">
                <div class="hero-card">
                    <div class="hero-icon">🌅</div>
                    <div class="hero-text">Daily<br>Horoscope</div>
                </div>
            </div>
            <div class="hero-col">
                <div class="hero-card">
                    <div class="hero-icon">💞</div>
                    <div class="hero-text">Kundali<br>Matching</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Invisible Buttons to capture clicks on the grid areas
        b1, b2 = st.columns(2)
        if b1.button("Read Horoscope"): st.session_state.show_daily = True
        if b2.button("Check Matching"): pass

        # B. PROFILE SCROLL (Only if > 1 profile)
        if len(profs) > 1:
            st.markdown('<p style="color:#888; font-size:12px; margin: 15px 0 5px 5px;">SWITCH PROFILE</p>', unsafe_allow_html=True)
            st.markdown('<div class="profile-scroll">', unsafe_allow_html=True)
            # Use standard Streamlit columns to hold buttons
            p_cols = st.columns(len(profs))
            for i, p in enumerate(profs):
                is_act = (p['Name'] == st.session_state.active_profile['Name'])
                sty = "primary" if is_act else "secondary"
                if p_cols[i].button(p['Name'].split()[0], key=f"prof_{i}", type=sty):
                    st.session_state.active_profile = p
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # C. DATA TABS
        if st.session_state.active_profile:
            p = st.session_state.active_profile
            st.markdown(f"<h3 style='margin-top:10px;'>{p['Name']}</h3>", unsafe_allow_html=True)
            
            t1, t2, t3, t4, t5 = st.tabs(["Basic", "Charts", "KP", "Dasha", "Report"])
            
            with t1:
                c1, c2 = st.columns(2)
                c1.metric("Lagna", p['Lagna'])
                c2.metric("Rashi", p['Rashi'])
                st.divider()
                c1.metric("Nakshatra", p['Nakshatra'])
                c2.caption(f"📅 {p['Date']}")
            
            with t2: st.code(p['Full_Chart'])
            with t3: st.info("KP Coming Soon")
            with t4: st.info("Dasha Coming Soon")
            with t5:
                q = st.selectbox("Topic", ["Life", "Career", "Love"])
                if st.button("Ask AI"):
                    with st.spinner("..."):
                        try:
                            res = model.generate_content(f"Analyze: {p['Full_Chart']} for {q}")
                            st.write(res.text)
                        except: st.error("AI Busy")

        if st.session_state.get('show_daily'):
            with st.expander("Today's Forecast", expanded=True):
                st.info("Good fortune awaits!")
                if st.button("Close"): st.session_state.show_daily = False; st.rerun()

    # --- CHAT VIEW ---
    elif st.session_state.page_view == "Chat":
        st.subheader("💬 AI Astrologer")
        if "msgs" not in st.session_state: st.session_state.msgs = []
        for m in st.session_state.msgs:
            with st.chat_message(m["role"]): st.write(m["content"])
            
        if user_in := st.chat_input("Ask question..."):
            st.session_state.msgs.append({"role":"user", "content":user_in})
            with st.chat_message("user"): st.write(user_in)
            with st.chat_message("assistant"):
                p = st.session_state.active_profile
                final_q = f"Context: {p['Name']}, {p['Lagna']} Lagna. Q: {user_in}"
                try:
                    ans = model.generate_content(final_q).text
                    st.write(ans)
                    st.session_state.msgs.append({"role":"assistant", "content":ans})
                except: st.error("AI Error")

    # --- PROFILE VIEW ---
    elif st.session_state.page_view == "Profile":
        st.subheader("👤 Settings")
        st.metric("Wallet", f"₹{st.session_state.wallet}")
        
        with st.expander("Add New Profile"):
            with st.form("add"):
                n = st.text_input("Name")
                g = st.selectbox("Gender", ["Male", "Female"])
                d = st.date_input("Date")
                c1, c2 = st.columns(2)
                h = c1.number_input("Hr", 0, 23)
                m = c2.number_input("Min", 0, 59)
                ci = st.text_input("City", "Mumbai")
                if st.form_submit_button("Add"):
                    ch = calculate_chart(n, g, d, datetime.time(h,m), ci)
                    db.collection("users").document(st.session_state.user_id).collection("profiles").document(n).set(ch)
                    st.success("Added!"); time.sleep(1); st.rerun()

    # --- BOTTOM NAV ---
    st.markdown('<div class="bottom-nav-spacer"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    def act(page): return "primary" if st.session_state.page_view == page else "secondary"
    
    if c1.button("🏠 Home", use_container_width=True, type=act("Home")): st.session_state.page_view="Home"; st.rerun()
    if c2.button("💬 Chat", use_container_width=True, type=act("Chat")): st.session_state.page_view="Chat"; st.rerun()
    if c3.button("👤 Profile", use_container_width=True, type=act("Profile")): st.session_state.page_view="Profile"; st.rerun()
