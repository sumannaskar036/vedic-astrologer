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

# Custom CSS for Mobile-App Look
st.markdown("""
<style>
    /* Dark Mode Global */
    .stApp { background-color: #121212; color: #E0E0E0; }
    
    /* TOP HEADER (Wallet) */
    .top-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 15px; background-color: #1e1e1e; 
        border-bottom: 1px solid #333; margin-bottom: 10px;
    }
    .wallet-badge {
        background-color: #FFD700; color: #000; padding: 5px 10px;
        border-radius: 15px; font-weight: bold; font-size: 14px;
    }
    
    /* PROFILE RIBBON (Top of Home) */
    .profile-scroll {
        display: flex; overflow-x: auto; gap: 10px; padding: 10px 0;
        scrollbar-width: none; /* Hide scrollbar */
    }
    .mini-profile {
        background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
        color: white; padding: 10px; border-radius: 10px; 
        min-width: 100px; text-align: center; cursor: pointer;
        border: 1px solid rgba(255,255,255,0.2);
    }
    .mini-profile.active {
        border: 2px solid #FFD700; box-shadow: 0 0 10px #FFD700;
    }

    /* ACTION RIBBON (Horoscope/Matching) */
    .action-ribbon {
        display: flex; gap: 10px; margin: 20px 0;
    }
    .action-card {
        flex: 1; background-color: #D32F2F; color: white;
        padding: 20px; border-radius: 12px; text-align: center;
        font-weight: bold; cursor: pointer;
    }
    
    /* BOTTOM NAVIGATION (Sticky) */
    .bottom-nav {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #1e1e1e; border-top: 1px solid #333;
        padding: 10px 0; display: flex; justify-content: space-around;
        z-index: 9999;
    }
    .nav-btn {
        background: none; border: none; color: #888; 
        font-size: 12px; display: flex; flex-direction: column; align-items: center;
    }
    .nav-btn.active { color: #FFD700; }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- 2. FIREBASE & API SETUP ---
if not firebase_admin._apps:
    try:
        raw_key = st.secrets["FIREBASE_SERVICE_ACCOUNT"]["private_key"]
        fixed_key = raw_key.replace("\\n", "\n")
        cred_info = {
            "type": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["type"],
            "project_id": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"],
            "private_key_id": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["private_key_id"],
            "private_key": fixed_key,
            "client_email": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["client_email"],
            "client_id": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["client_id"],
            "auth_uri": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["auth_uri"],
            "token_uri": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["FIREBASE_SERVICE_ACCOUNT"]["client_x509_cert_url"],
            "universe_domain": "googleapis.com"
        }
        cred = credentials.Certificate(cred_info)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Database Error: {e}")
        st.stop()

db = firestore.client()

try:
    geocoder = OpenCageGeocode(st.secrets["OPENCAGE_API_KEY"])
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except: pass

# --- 3. SESSION STATE ---
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'user_phone' not in st.session_state: st.session_state.user_phone = None
if 'current_page' not in st.session_state: st.session_state.current_page = "Login"
if 'wallet_balance' not in st.session_state: st.session_state.wallet_balance = 0
if 'active_profile' not in st.session_state: st.session_state.active_profile = None # The profile currently shown on Home

# --- 4. CALCULATION ENGINE (Hidden Logic) ---
def calculate_chart(name, gender, dt, tm, city):
    # Simplified wrapper for brevity (Logic remains same as previous code)
    # Using Moshier + Lahiri default
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    # Geocode
    try:
        res = geocoder.geocode(city)
        lat, lng = res[0]['geometry']['lat'], res[0]['geometry']['lng']
    except:
        lat, lng = 22.57, 88.36 # Default Kolkata
    
    birth_dt = datetime.datetime.combine(dt, tm)
    utc_dt = birth_dt - datetime.timedelta(hours=5, minutes=30)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses(jd, lat, lng, b'P')
    asc_deg = (ascmc[0] - ayanamsa) % 360
    zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lagna = zodiac[int(asc_deg // 30)]
    
    # Get Moon Rashi
    moon_pos = swe.calc_ut(jd, 1, swe.FLG_SIDEREAL | swe.FLG_MOSEPH)[0][0]
    moon_sign = zodiac[int(moon_pos // 30) % 12]
    
    return {
        "Name": name, "Gender": gender, "Lagna": lagna, "Rashi": moon_sign,
        "Date": str(dt), "Time": str(tm), "City": city,
        "Lat": lat, "Lng": lng
    }

# --- 5. PAGE: LOGIN FLOW ---
if st.session_state.current_page == "Login":
    st.markdown("## 👋 Welcome to TaraVaani")
    st.info("Please Sign In to continue.")
    
    # 1. Google Sign In (Simulated Button)
    if st.button("🇬 Google Sign In"):
        st.session_state.login_step = 2
        st.rerun()

    if st.session_state.get('login_step') == 2:
        st.markdown("### 📱 Mobile Verification")
        phone = st.text_input("Enter Phone Number (+91)", "+91 ")
        if st.button("Send OTP (WhatsApp)"):
            with st.spinner("Sending OTP via WhatsApp..."):
                time.sleep(2) # Simulate API call
                st.success("OTP Sent to WhatsApp!")
                st.session_state.login_step = 3
                st.rerun()

    if st.session_state.get('login_step') == 3:
        otp = st.text_input("Enter OTP", type="password")
        if st.button("Verify & Create Profile"):
            if otp: # In real app, check if otp == sent_otp
                st.session_state.user_phone = phone
                st.session_state.login_step = 4
                st.rerun()

    if st.session_state.get('login_step') == 4:
        st.markdown("### 👤 Create Your Profile")
        with st.form("first_profile"):
            name = st.text_input("Name")
            gender = st.selectbox("Gender", ["Male", "Female"])
            dob = st.date_input("Birth Date", value=datetime.date(1990,1,1))
            t_hr = st.selectbox("Hour", range(24))
            t_min = st.selectbox("Minute", range(60))
            city = st.text_input("City", "Kolkata, India")
            
            if st.form_submit_button("Start TaraVaani 🚀"):
                # Save to Firebase
                user_id = f"{name}_{int(time.time())}"
                st.session_state.user_id = user_id
                
                chart_data = calculate_chart(name, gender, dob, datetime.time(t_hr, t_min), city)
                db.collection("users").document(user_id).collection("profiles").document(name).set(chart_data)
                
                # Auto Set Active Profile
                st.session_state.active_profile = chart_data
                st.session_state.current_page = "Home"
                st.rerun()

# --- 6. PAGE: HOME ---
elif st.session_state.current_page == "Home":
    # --- Top Header ---
    st.markdown(f"""
    <div class="top-header">
        <div style="font-size:20px;">☸️ <b>TaraVaani</b></div>
        <div class="wallet-badge">₹{st.session_state.wallet_balance}</div>
    </div>
    """, unsafe_allow_html=True)

    # --- Fetch Profiles ---
    try:
        docs = db.collection("users").document(st.session_state.user_id).collection("profiles").stream()
        all_profiles = [doc.to_dict() for doc in docs]
    except: all_profiles = []

    # Ensure active profile is valid
    if not st.session_state.active_profile and all_profiles:
        st.session_state.active_profile = all_profiles[0]

    # --- 1. Top Ribbon (Only if > 1 profile) ---
    if len(all_profiles) > 1:
        st.markdown("**Switch Profile:**")
        cols = st.columns(len(all_profiles))
        for i, p in enumerate(all_profiles):
            is_active = (p['Name'] == st.session_state.active_profile['Name'])
            btn_label = f"🟢 {p['Name']}" if is_active else p['Name']
            if cols[i].button(btn_label, key=f"top_prof_{i}"):
                st.session_state.active_profile = p
                st.rerun()

    # --- 2. Action Ribbon (Horoscope & Matching) ---
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="action-card">🌅<br>Daily Horoscope</div>', unsafe_allow_html=True)
        if st.button("Read Horoscope", key="btn_horo", use_container_width=True):
            st.session_state.show_horoscope = True
    with c2:
        st.markdown('<div class="action-card">❤️<br>Matching</div>', unsafe_allow_html=True)
        st.button("Check Match", key="btn_match", use_container_width=True)

    # --- Horoscope Logic (Pop-up style) ---
    if st.session_state.get('show_horoscope'):
        p = st.session_state.active_profile
        st.info(f"📅 **Daily Horoscope for {p['Name']} ({p['Rashi']})**")
        st.write("Today is a powerful day for career growth. Avoid arguments.")
        st.success("**Lucky Color:** Green | **Lucky No:** 5")
        if st.button("Close"): 
            st.session_state.show_horoscope = False
            st.rerun()

    # --- 3. Toggle Menu (Tabs) ---
    if st.session_state.active_profile:
        p = st.session_state.active_profile
        st.markdown(f"### 📜 Chart: {p['Name']}")
        
        t1, t2, t3, t4, t5 = st.tabs(["Basic", "Charts", "KP", "Dasha", "Report"])
        
        with t1:
            c1, c2 = st.columns(2)
            c1.metric("Lagna", p['Lagna'])
            c2.metric("Rashi", p['Rashi'])
            c1.metric("Gender", p['Gender'])
            c2.metric("City", p['City'])

        with t2:
            st.info("Chart Visualization Coming Soon") # Placeholder for graphical chart
            
        with t3: st.warning("KP System Calculation...")
        with t4: st.warning("Vimshottari Dasha Table...")
        
        with t5: # REPORT (AI)
            st.write("Ask Gemini about this chart:")
            q = st.selectbox("Topic", ["General", "Career", "Health"])
            if st.button("Generate AI Report"):
                prompt = f"Analyze Vedic chart for {p['Name']}, Lagna {p['Lagna']}, Rashi {p['Rashi']}. Tell about {q}."
                with st.spinner("TaraVaani is writing..."):
                    try:
                        res = model.generate_content(prompt)
                        st.write(res.text)
                    except: st.error("AI Error")

# --- 7. PAGE: CHAT (TaraVaani Agent) ---
elif st.session_state.current_page == "Chat":
    st.markdown("### 💬 Chat with TaraVaani")
    
    # Simple Chat Interface
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Namaste! I am TaraVaani. Ask me anything about your chart."}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about your future..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            # Context Aware Response
            p = st.session_state.active_profile
            full_prompt = f"User: {p['Name']}, Rashi: {p['Rashi']}. Question: {prompt}. Answer as Vedic Astrologer."
            try:
                response = model.generate_content(full_prompt)
                bot_reply = response.text
                st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            except: st.error("Connection failed.")

# --- 8. PAGE: PROFILE & WALLET ---
elif st.session_state.current_page == "Profile":
    st.markdown("### 👤 My Profile")
    st.metric("Wallet Balance", f"₹{st.session_state.wallet_balance}")
    
    st.markdown("#### 💳 Recharge Wallet")
    c1, c2, c3 = st.columns(3)
    if c1.button("₹300"): 
        st.session_state.wallet_balance += 300
        st.balloons()
        st.rerun()
    if c2.button("₹500"): 
        st.session_state.wallet_balance += 500
        st.balloons()
        st.rerun()
    if c3.button("₹1000"): 
        st.session_state.wallet_balance += 1000
        st.balloons()
        st.rerun()
        
    st.divider()
    
    st.markdown("#### ➕ Add Family Member")
    with st.expander("Create New Kundali"):
        with st.form("new_family"):
            n = st.text_input("Name")
            g = st.selectbox("Gender", ["Male", "Female"])
            d = st.date_input("Date")
            t_h = st.selectbox("Hr", range(24))
            t_m = st.selectbox("Mn", range(60))
            ct = st.text_input("City", "Delhi")
            
            if st.form_submit_button("Add Member"):
                c_data = calculate_chart(n, g, d, datetime.time(t_h, t_m), ct)
                db.collection("users").document(st.session_state.user_id).collection("profiles").document(n).set(c_data)
                st.success(f"{n} added!")
                st.rerun()

    st.divider()
    st.markdown("#### 📜 Saved Kundalis")
    try:
        docs = db.collection("users").document(st.session_state.user_id).collection("profiles").stream()
        for doc in docs:
            d = doc.to_dict()
            st.text(f"• {d['Name']} ({d['Rashi']})")
    except: pass

# --- 9. BOTTOM NAVIGATION (Sticky Footer) ---
# Only show if logged in
if st.session_state.current_page != "Login":
    st.markdown("---") 
    st.markdown('<div style="margin-bottom: 60px;"></div>', unsafe_allow_html=True) # Spacer
    
    # We use columns to simulate buttons, but in a real mobile app this is a fixed footer
    # Using Streamlit columns at the very end of script
    c1, c2, c3 = st.columns(3)
    
    # Helper to styling active button
    def nav_style(page_name):
        return "primary" if st.session_state.current_page == page_name else "secondary"

    if c1.button("🏠 Home", use_container_width=True, type=nav_style("Home")):
        st.session_state.current_page = "Home"
        st.rerun()
    if c2.button("💬 Chat", use_container_width=True, type=nav_style("Chat")):
        st.session_state.current_page = "Chat"
        st.rerun()
    if c3.button("👤 Profile", use_container_width=True, type=nav_style("Profile")):
        st.session_state.current_page = "Profile"
        st.rerun()
