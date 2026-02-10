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

# --- 2. MOBILE-FIRST CSS (Aggressive Padding Removal) ---
st.markdown("""
<style>
    /* RESET STREAMLIT PADDING */
    .stApp { background-color: #121212; color: #E0E0E0; }
    
    /* Remove the huge gap at the top of the app */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    
    /* TOP HEADER (Fixed Pink Bar) */
    .top-header {
        position: sticky; top: 0; z-index: 999;
        background-color: #F8BBD0; color: #880E4F;
        padding: 15px 20px;
        margin: 0 -0.5rem; /* Stretch to edges */
        display: flex; justify-content: space-between; align-items: center;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    
    /* HERO SECTION (Red Background) */
    .red-section {
        background-color: #C62828; /* Deep Red */
        margin: 20px 0; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 15px rgba(198, 40, 40, 0.4);
    }
    .hero-btn-container {
        display: flex; gap: 15px;
    }
    .hero-btn {
        flex: 1; background: rgba(255,255,255,0.1); 
        padding: 15px; border-radius: 12px; text-align: center;
        border: 1px solid rgba(255,255,255,0.3); cursor: pointer;
    }
    .hero-btn:active { background: rgba(255,255,255,0.3); }

    /* PROFILE SECTION (Purple Background) */
    .purple-section {
        background: linear-gradient(135deg, #7B1FA2 0%, #4A148C 100%);
        padding: 15px; border-radius: 15px; margin-bottom: 20px;
        overflow-x: auto; white-space: nowrap;
        box-shadow: 0 4px 15px rgba(123, 31, 162, 0.4);
    }
    /* Hide scrollbar */
    .purple-section::-webkit-scrollbar { display: none; }
    
    .profile-pill {
        display: inline-block; background-color: rgba(0,0,0,0.2); 
        color: white; padding: 10px 20px; border-radius: 20px; margin-right: 10px;
        border: 1px solid rgba(255,255,255,0.2); text-align: center;
        min-width: 80px;
    }

    /* BOTTOM NAV (Fixed Footer) */
    .bottom-nav {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #212121; border-top: 1px solid #333;
        padding: 10px 0; display: flex; justify-content: space-around;
        z-index: 999; padding-bottom: 20px; /* Safe area for modern phones */
    }

    /* INPUTS */
    div[data-baseweb="input"] { background-color: #2D2D2D !important; border: none; border-radius: 10px; color: white; }
    div[data-baseweb="select"] > div { background-color: #2D2D2D !important; border-radius: 10px; }
    
    /* Hide Elements */
    #MainMenu, footer, header {visibility: hidden;}
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
    swe.set_sid_mode(swe.SIDM_LAHIRI) # Default
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

    # Full Chart String
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
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #F8BBD0;'>☸️ TaraVaani</h1>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div style="background:#1E1E1E; padding:20px; border-radius:15px;">', unsafe_allow_html=True)
        name = st.text_input("Full Name")
        gender = st.selectbox("Gender", ["Male", "Female"])
        
        # Date & Time (Side by Side)
        c1, c2 = st.columns(2)
        dob = c1.date_input("Date", datetime.date(1995,1,1), min_value=datetime.date(1900,1,1), max_value=datetime.date(2100,12,31), format="DD/MM/YYYY")
        
        # Time Inputs (Hour & Min)
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
                
                # Safe Time Object Creation
                final_time = datetime.time(int(hr), int(mn))
                
                chart = calculate_chart(name, gender, dob, final_time, city)
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
        
        # A. RED HERO SECTION (Horoscope & Matching)
        st.markdown('<div class="red-section">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:white; margin-top:0;">Daily Services</h4>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="hero-btn">🌅<br><b>Horoscope</b></div>', unsafe_allow_html=True)
            if st.button("Read", key="d_h"): st.session_state.show_daily = True
        with c2:
            st.markdown('<div class="hero-btn">💞<br><b>Matching</b></div>', unsafe_allow_html=True)
            st.button("Match", key="k_m")
        st.markdown('</div>', unsafe_allow_html=True)

        # B. PURPLE PROFILE LIST (Only if > 1 profile)
        if len(profs) > 1:
            st.markdown('<div class="purple-section">', unsafe_allow_html=True)
            cols = st.columns(len(profs))
            for i, p in enumerate(profs):
                is_act = (p['Name'] == st.session_state.active_profile['Name'])
                sty = "primary" if is_act else "secondary"
                if cols[i].button(p['Name'].split()[0], key=f"prof_{i}", type=sty):
                    st.session_state.active_profile = p
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # C. DATA TABS
        if st.session_state.active_profile:
            p = st.session_state.active_profile
            st.subheader(f"📜 {p['Name']}")
            
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
                        res = model.generate_content(f"Analyze: {p['Full_Chart']} for {q}")
                        st.write(res.text)

        # Daily Modal
        if st.session_state.get('show_daily'):
            with st.expander("Today's Forecast", expanded=True):
                st.info("A great day for spiritual growth.")
                if st.button("Close"): 
                    st.session_state.show_daily = False
                    st.rerun()

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
                ans = model.generate_content(final_q).text
                st.write(ans)
                st.session_state.msgs.append({"role":"assistant", "content":ans})

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
    st.markdown('<div style="height:80px"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    def act(page): return "primary" if st.session_state.page_view == page else "secondary"
    
    if c1.button("🏠 Home", use_container_width=True, type=act("Home")): st.session_state.page_view="Home"; st.rerun()
    if c2.button("💬 Chat", use_container_width=True, type=act("Chat")): st.session_state.page_view="Chat"; st.rerun()
    if c3.button("👤 Profile", use_container_width=True, type=act("Profile")): st.session_state.page_view="Profile"; st.rerun()
