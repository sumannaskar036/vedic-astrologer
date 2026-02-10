import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from opencage.geocoder import OpenCageGeocode
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TaraVaani", page_icon="☸️", layout="centered", initial_sidebar_state="collapsed")

# --- 2. SESSION STATE ---
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'onboarding_complete' not in st.session_state: st.session_state.onboarding_complete = False
if 'active_profile' not in st.session_state: st.session_state.active_profile = None 
if 'page_view' not in st.session_state: st.session_state.page_view = "Home"
if 'wallet' not in st.session_state: st.session_state.wallet = 0
if 'chat_history' not in st.session_state: st.session_state.chat_history = []

# --- 3. SMART CSS ENGINE ---
# Base CSS (Always Active)
base_css = """
<style>
    .stApp { background-color: #121212; color: #E0E0E0; font-family: sans-serif; }
    
    /* Remove default Streamlit padding */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 8rem !important; /* Extra space for bottom nav + chat input */
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }

    /* Fixed Top Header */
    .top-header {
        position: sticky; top: 0; z-index: 50;
        background-color: #F8BBD0; color: #880E4F;
        padding: 15px 20px; margin: 0 -0.5rem 1rem -0.5rem;
        display: flex; justify-content: space-between; align-items: center;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    
    /* Input Fields styling */
    div[data-baseweb="input"] { background-color: #2D2D2D !important; border: none; border-radius: 10px; color: white; }
    div[data-baseweb="select"] > div { background-color: #2D2D2D !important; border-radius: 10px; }
    
    /* Hide Defaults */
    #MainMenu, footer, header {visibility: hidden;}
</style>
"""
st.markdown(base_css, unsafe_allow_html=True)

# PAGE SPECIFIC CSS
if not st.session_state.onboarding_complete:
    # ONBOARDING CSS: Normal Red Buttons
    st.markdown("""
    <style>
        div.stButton > button[kind="primary"] {
            background-color: #D32F2F !important;
            border: none !important; border-radius: 10px !important;
            height: 50px !important; width: 100% !important;
            font-size: 16px !important; font-weight: bold !important;
            color: white !important;
        }
    </style>""", unsafe_allow_html=True)

elif st.session_state.page_view == "Home":
    # HOME CSS: Big Red Cards for Primary Buttons
    st.markdown("""
    <style>
        /* Force 2-Column Grid for Hero Cards */
        div[data-testid="column"] { width: 50% !important; flex: 1 1 50% !important; min-width: 50% !important; }
        
        /* Big Red Card Style */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #D32F2F 0%, #B71C1C 100%) !important;
            border: none !important; border-radius: 15px !important;
            height: 110px !important; width: 100% !important;
            font-size: 16px !important; font-weight: bold !important;
            color: white !important; white-space: pre-wrap !important;
            box-shadow: 0 4px 10px rgba(211, 47, 47, 0.4) !important;
            margin-bottom: 0px !important;
        }
        
        /* Secondary Pills */
        div.stButton > button[kind="secondary"] {
            background-color: #2D2D2D !important; border-radius: 20px !important;
            height: 35px !important; font-size: 12px !important;
            border: 1px solid #444 !important; color: #B0BEC5 !important;
        }
    </style>""", unsafe_allow_html=True)

else:
    # OTHER PAGES: Normal Buttons
    st.markdown("""
    <style>
        div.stButton > button {
            border-radius: 10px !important; height: 45px !important;
            font-weight: bold !important;
        }
    </style>""", unsafe_allow_html=True)


# --- 4. BACKEND SETUP ---
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

# --- 5. LOGIC FUNCTIONS ---
def calculate_chart(name, gender, dt, tm, city):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    try:
        res = geocoder.geocode(city)
        lat, lng = res[0]['geometry']['lat'], res[0]['geometry']['lng']
    except: lat, lng = 28.61, 77.20 
    
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
    if not uid: return []
    try:
        docs = db.collection("users").document(uid).collection("profiles").stream()
        return [d.to_dict() for d in docs]
    except: return []

# --- 6. VIEW: ONBOARDING ---
qp = st.query_params
url_uid = qp.get("uid", None)

if not st.session_state.onboarding_complete and not url_uid:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #F8BBD0;'>☸️ TaraVaani</h1>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div style="background:#1E1E1E; padding:20px; border-radius:15px; margin-top:10px;">', unsafe_allow_html=True)
        
        tab_new, tab_log = st.tabs(["Create New", "Login"])
        
        with tab_new:
            name = st.text_input("Full Name", placeholder="e.g. Suman Naskar")
            gender = st.selectbox("Gender", ["Male", "Female"])
            dob = st.date_input("Date", value=datetime.date(1995, 1, 1), min_value=datetime.date(1900,1,1), max_value=datetime.date(2100,12,31), format="DD/MM/YYYY")
            
            c1, c2 = st.columns(2)
            hr = c1.selectbox("Hour", range(24), index=10)
            mn = c2.selectbox("Minute", range(60), index=30)
            
            city = st.text_input("City", "New Delhi, India")
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Button is RED and NORMAL size here due to CSS logic
            if st.button("Start Journey 🚀", type="primary"):
                if name:
                    uid = f"{name.replace(' ', '_')}_{int(time.time())}"
                    try:
                        chart = calculate_chart(name, gender, dob, datetime.time(hr, mn), city)
                        db.collection("users").document(uid).collection("profiles").document(name).set(chart)
                        st.session_state.user_id = uid
                        st.session_state.active_profile = chart
                        st.session_state.onboarding_complete = True
                        st.query_params["uid"] = uid
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

        with tab_log:
            uid_in = st.text_input("User ID (from URL)")
            if st.button("Login"):
                if uid_in:
                    st.session_state.user_id = uid_in
                    st.session_state.onboarding_complete = True
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 7. VIEW: MAIN APP ---
else:
    if url_uid and not st.session_state.user_id:
        st.session_state.user_id = url_uid
        st.session_state.onboarding_complete = True

    profs = get_profs(st.session_state.user_id)
    if not st.session_state.active_profile and profs: st.session_state.active_profile = profs[0]
    
    # TOP HEADER
    st.markdown(f"""
    <div class="top-header">
        <div style="font-size:20px;">☰</div>
        <div style="font-weight:bold;">TaraVaani</div>
        <div style="background:white; padding:5px 10px; border-radius:15px; font-size:12px; font-weight:800;">
            ₹{st.session_state.wallet}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- HOME PAGE ---
    if st.session_state.page_view == "Home":
        st.markdown("<br>", unsafe_allow_html=True)
        
        # HERO CARDS (Big Red due to CSS)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🌅\nHoroscope", key="h_btn", type="primary"): st.session_state.show_daily = True
        with c2:
            if st.button("💞\nMatching", key="m_btn", type="primary"): pass

        # PROFILE LIST
        if len(profs) > 1:
            st.markdown('<p style="color:#888; font-size:12px; margin: 15px 0 5px 5px;">SWITCH PROFILE</p>', unsafe_allow_html=True)
            st.markdown('<div style="display:flex; overflow-x:auto; gap:10px; padding-bottom:10px;">', unsafe_allow_html=True)
            cols = st.columns(len(profs))
            for i, p in enumerate(profs):
                is_act = (p['Name'] == st.session_state.active_profile['Name'])
                label = f"◉ {p['Name'].split()[0]}" if is_act else p['Name'].split()[0]
                if cols[i].button(label, key=f"p_{i}", type="secondary"):
                    st.session_state.active_profile = p
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # DATA AREA
        if st.session_state.active_profile:
            p = st.session_state.active_profile
            st.markdown(f"### {p['Name']}")
            t1, t2, t3, t4, t5 = st.tabs(["Basic", "Charts", "KP", "Dasha", "Report"])
            
            with t1:
                c1, c2 = st.columns(2)
                c1.metric("Lagna", p['Lagna'])
                c2.metric("Rashi", p['Rashi'])
                st.divider()
                c1.metric("Nakshatra", p['Nakshatra'])
                c2.caption(f"📍 {p.get('City', 'India')}")
            
            with t2: st.code(p['Full_Chart'])
            with t3: st.info("KP Coming Soon")
            with t4: st.info("Dasha Coming Soon")
            
            with t5:
                q = st.selectbox("Topic", ["Life", "Career", "Love"])
                if st.button("Ask AI", type="secondary"): # Secondary = Dark Pill
                    with st.spinner("Connecting..."):
                        try:
                            # SAFE CHECK FOR AI
                            if 'gemini-1.5-flash' in str(model):
                                res = model.generate_content(f"Analyze: {p['Full_Chart']} for {q}")
                                st.write(res.text)
                            else:
                                st.error("AI Key Missing")
                        except Exception as e: st.error("AI sleeping. Wake it up later.")

        if st.session_state.get('show_daily'):
            with st.expander("Today's Forecast", expanded=True):
                st.info("A powerful day for growth.")
                if st.button("Close"): st.session_state.show_daily = False; st.rerun()

    # --- CHAT PAGE ---
    elif st.session_state.page_view == "Chat":
        st.subheader("💬 AI Astrologer")
        
        # Chat History
        for m in st.session_state.chat_history:
            with st.chat_message(m["role"]): st.write(m["content"])
            
        # Chat Input
        if prompt := st.chat_input("Ask about your chart..."):
            st.session_state.chat_history.append({"role":"user", "content":prompt})
            with st.chat_message("user"): st.write(prompt)
            
            with st.chat_message("assistant"):
                try:
                    p = st.session_state.active_profile
                    # Handle if p is None (Fresh user, no profile yet)
                    if p:
                        ctx = f"Context: {p['Name']}, {p['Lagna']} Lagna. Q: {prompt}"
                        res = model.generate_content(ctx)
                        st.write(res.text)
                        st.session_state.chat_history.append({"role":"assistant", "content":res.text})
                    else:
                        st.error("Please create a profile first.")
                except: st.error("AI Error. Check API Key.")

    # --- PROFILE PAGE ---
    elif st.session_state.page_view == "Profile":
        st.subheader("👤 Settings")
        st.metric("Wallet", f"₹{st.session_state.wallet}")
        
        with st.expander("Add New Profile"):
            n = st.text_input("Name")
            g = st.selectbox("Gender", ["Male", "Female"])
            d = st.date_input("Date")
            c1, c2 = st.columns(2)
            h = c1.selectbox("Hr", range(24))
            m = c2.selectbox("Mn", range(60))
            ci = st.text_input("City", "Mumbai")
            
            if st.button("Add Profile"):
                ch = calculate_chart(n, g, d, datetime.time(h,m), ci)
                db.collection("users").document(st.session_state.user_id).collection("profiles").document(n).set(ch)
                st.success("Added!"); st.rerun()

    # --- BOTTOM NAV (STICKY & ABOVE CHAT) ---
    c1, c2, c3 = st.columns(3)
    
    # We use Custom CSS to define .bottom-nav but we need to inject buttons into it?
    # Streamlit doesn't support moving buttons into divs.
    # We just place them at the end. The spacing is handled by .block-container padding-bottom
    
    st.markdown("---")
    # Simple Text Buttons for Nav
    def nav_lbl(txt, view): return f"📍 {txt}" if st.session_state.page_view == view else txt

    if c1.button(nav_lbl("Home", "Home"), use_container_width=True): st.session_state.page_view="Home"; st.rerun()
    if c2.button(nav_lbl("Chat", "Chat"), use_container_width=True): st.session_state.page_view="Chat"; st.rerun()
    if c3.button(nav_lbl("Profile", "Profile"), use_container_width=True): st.session_state.page_view="Profile"; st.rerun()
