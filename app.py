import streamlit as st
import google.generativeai as genai
import swisseph as swe
import datetime
import time

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="TaraVaani", 
    page_icon="☸️", 
    layout="centered"
)

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
        self.model = self._get_best_model()
        swe.set_sid_mode(swe.SIDM_LAHIRI)

    def _get_best_model(self):
        # Always try Flash first (Fastest + Highest Limits)
        return genai.GenerativeModel('gemini-1.5-flash')

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

        cusps, ascmc = swe.houses(jd, lat, lon, b'P')
        asc_
