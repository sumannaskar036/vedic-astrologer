
import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime

# --- SECURITY: Get Key from Streamlit Secrets ---
try:
    SERVER_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("Secrets not found. Please set GEMINI_API_KEY in Streamlit Cloud.")
    st.stop()

# --- BACKEND LOGIC ---
class VedicAstrologerBot:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        except:
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            
        swe.set_sid_mode(swe.SIDM_LAHIRI)

    def _get_gana_yoni(self, nakshatra_name):
        data = {
            "Ashwini": ("Deva", "Horse"), "Bharani": ("Manushya", "Elephant"), "Krittika": ("Rakshasa", "Goat"),
            "Rohini": ("Manushya", "Snake"), "Mrigashira": ("Deva", "Snake"), "Ardra": ("Manushya", "Dog"),
            "Punarvasu": ("Deva", "Cat"), "Pushya": ("Deva", "Goat"), "Ashlesha": ("Rakshasa", "Cat"),
            "Magha": ("Rakshasa", "Rat"), "Purva Phalguni": ("Manushya", "Rat"), "Uttara Phalguni": ("Manushya", "Cow"),
            "Hasta": ("Deva", "Buffalo"), "Chitra": ("Rakshasa", "Tiger"), "Swati": ("Deva", "Buffalo"),
            "Vishakha": ("Rakshasa", "Tiger"), "Anuradha": ("Deva", "Deer"), "Jyeshtha": ("Rakshasa", "Deer"),
            "Mula": ("Rakshasa", "Dog"), "Purva Ashadha": ("Manushya", "Monkey"), "Uttara Ashadha": ("Manushya", "Mongoose"),
            "Shravana": ("Deva", "Monkey"), "Dhanishta": ("Rakshasa", "Lion"), "Shatabhisha": ("Rakshasa", "Horse"),
            "Purva Bhadrapada": ("Manushya", "Lion"), "Uttara Bhadrapada": ("Manushya", "Cow"), "Revati": ("Deva", "Elephant")
        }
        return data.get(nakshatra_name, ("Unknown", "Unknown"))

    def calculate_chart(self, name, dt, tm, lat, lon):
        local_dt = datetime.datetime.combine(dt, tm)
        utc_dt = local_dt - datetime.timedelta(hours=5, minutes=30)
        jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)

        # Vedic Lagna
        cusps, ascmc = swe.houses(jd, lat, lon, b'P')
        asc_vedic = (ascmc[0] - swe.get_ayanamsa_ut(jd)) % 360
        
        zodiac = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        nakshatras = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
                      "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
                      "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
                      "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
                      "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

        lagna_sign = zodiac[int(asc_vedic // 30)]
        
        planet_map = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
            "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, 
            "Rahu": swe.MEAN_NODE, "Ketu": swe.MEAN_NODE
        }
        
        results = []
        user_rashi = ""
        user_nak = ""

        for p, pid in planet_map.items():
            if p == "Ketu": 
                pos_rahu = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SIDEREAL)[0][0]
                pos = (pos_rahu + 180) % 360
            else:
                pos = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]
            
            sign = zodiac[int(pos // 30)]
            nak = nakshatras[int(pos / (360/27))]
            degree = pos % 30
            
            results.append(f"{p}: {sign} ({degree:.2f}°) | {nak}")
            
            if p == "Moon":
                user_rashi = sign
                user_nak = nak
                
        gana, yoni = self._get_gana_yoni(user_nak)
        self.user_stats = {"Name": name, "Lagna": lagna_sign, "Rashi": user_rashi, "Nakshatra": user_nak, "Gana": gana, "Yoni": yoni}
        self.chart_summary = "\n".join(results)

    def ask_ai(self, question, lang):
        prompt = f'''
        You are a divine Vedic Astrologer.
        USER IDENTITY: {self.user_stats}
        CHART DATA: {self.chart_summary}
        
        INSTRUCTIONS:
        1. Start with "Radhe Radhe {self.user_stats['Name']} 🙏"
        2. Speak ONLY in {lang}.
        3. Use the Chart Data to answer.
        4. Keep it under 150 words.
        '''
        response = self.model.generate_content(prompt + "\nUSER QUESTION: " + question)
        return response.text

# --- FRONTEND UI ---
st.set_page_config(page_title="Vedic AI Astrologer", page_icon="🕉️")

st.title("🕉️ Vedic AI Astrologer")
st.caption("Accurate Vedic Engine (Lahiri Ayanamsa)")

with st.sidebar:
    st.header("Janma Kundali Details")
    
    name = st.text_input("Name", "Suman")
    st.subheader("Birth Date & Time")
    dob = st.date_input("Date", datetime.date(1993, 4, 23), format="DD/MM/YYYY")
    
    c1, c2 = st.columns(2)
    with c1:
        hour = st.selectbox("Hour (0-23)", range(0, 24), index=15)
    with c2:
        minute = st.selectbox("Minute (0-59)", range(0, 60), index=45)
    tob = datetime.time(hour, minute)
    
    st.text("Location: Kolkata (Default)")
    
    lang = st.selectbox("Select Language", [
        "English", "Hindi (हिंदी)", "Bengali (বাংলা)", 
        "Marathi (मराठी)", "Punjabi (ਪੰਜਾਬੀ)", 
        "Kannada (ಕನ್ನಡ)", "Tamil (தமிழ்)", 
        "Telugu (తెలుగు)", "Odia (ଓଡ଼ିଆ)"
    ])
    
    if st.button("Generate Kundali"):
        if SERVER_API_KEY:
            with st.spinner("Calculating Vedic Positions..."):
                bot = VedicAstrologerBot(SERVER_API_KEY)
                bot.calculate_chart(name, dob, tob, 22.57, 88.36)
                st.session_state['bot'] = bot
                st.success("✅ Kundali Verified")
                st.markdown(f'''
                | **Attribute** | **Value** |
                | :--- | :--- |
                | **Lagna** | {bot.user_stats['Lagna']} |
                | **Rashi** | {bot.user_stats['Rashi']} |
                | **Nakshatra** | {bot.user_stats['Nakshatra']} |
                | **Gana** | {bot.user_stats['Gana']} |
                | **Yoni** | {bot.user_stats['Yoni']} |
                ''')
        else:
            st.error("Owner Error: API Key not set in secrets.")

# Chat Window
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

for msg in st.session_state['messages']:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input(f"Ask a question in {lang}..."):
    st.session_state['messages'].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    if 'bot' in st.session_state:
        with st.chat_message("assistant"):
            with st.spinner("Consulting the stars..."):
                response = st.session_state['bot'].ask_ai(prompt, lang)
                st.markdown(response)
                st.session_state['messages'].append({"role": "assistant", "content": response})
    else:
        st.error("Please Generate Kundali in the sidebar first!")
