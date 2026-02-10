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

# --- 2. MOBILE-FIRST CSS (Merged Buttons) ---
st.markdown("""
<style>
    /* 1. RESET & LAYOUT */
    .stApp { background-color: #121212; color: #E0E0E0; font-family: sans-serif; }
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 6rem !important; /* Space for bottom nav */
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    
    /* 2. TOP HEADER (Sticky) */
    .top-header {
        position: sticky; top: 0; z-index: 999;
        background-color: #F8BBD0; color: #880E4F;
        padding: 15px 20px; margin: 0 -0.5rem 1rem -0.5rem;
        display: flex; justify-content: space-between; align-items: center;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    
    /* 3. HERO BUTTONS (The Red Cards) */
    /* We target Primary Buttons to look like the Red Cards */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #D32F2F 0%, #B71C1C 100%) !important;
        border: none !important;
        border-radius: 15px !important;
        height: 110px !important; /* Tall Card */
        font-size: 16px !important;
        font-weight: bold !important;
        color: white !important;
        box-shadow: 0 4px 10px rgba(211, 47, 47, 0.4) !important;
        white-space: pre-wrap !important; /* Allow emoji on new line */
        line-height: 1.4 !important;
        transition: transform 0.1s;
    }
    div.stButton > button[kind="primary"]:active { transform: scale(0.96); }

    /* 4. PROFILE PILLS (Secondary Buttons) */
    /* We target Secondary Buttons for the profile list */
    div.stButton > button[kind="secondary"] {
        background-color: #2D2D2D !important;
        color: #E0E0E0 !important;
        border: 1px solid #444 !important;
        border-radius: 20px !important;
        height: 40px !important;
        font-size: 13px !important;
    }
    div.stButton > button[kind="secondary"]:focus {
        border-color: #FFD700 !important;
        color: #FFD700 !important;
    }

    /* 5. PROFILE SCROLL CONTAINER */
    .profile-scroll {
        display: flex; overflow-x: auto; gap: 10px; padding: 10px 5px;
        scrollbar-width: none; margin-bottom: 10px;
    }
    .profile-scroll::-webkit-scrollbar { display: none; }
    
    /* 6. BOTTOM NAV (Fixed Footer) */
    .bottom-nav-spacer { height: 80px; }
    
    /* INPUTS & TABS */
    div[data-baseweb="input"] { background-color: #2D2D2D !important; border: none; border-radius: 10px; color: white; }
    div[data-baseweb="select"] > div { background-color: #2D2D2D !important; border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { background-color: #1E1E1E; padding: 5px; border-radius: 10px; }
    .stTabs [aria-selected="true"] { background-color: #D32F2F !important; color: white !important; }
    
    /* Hide Defaults */
    #MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. DATABASE ---
if not firebase_admin._apps:
    try
    if c1.button("🏠 Home", use_container_width=True, type=act("Home")): st.session_state.page_view="Home"; st.rerun()
    if c2.button("💬 Chat", use_container_width=True, type=act("Chat")): st.session_state.page_view="Chat"; st.rerun()
    if c3.button("👤 Profile", use_container_width=True, type=act("Profile")): st.session_state.page_view="Profile"; st.rerun()
