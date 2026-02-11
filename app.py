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

# --- EXTENDED INTERPRETATIONS (RICH TEXT) ---
def get_chart_interpretations(asc_sign_id):
    interpretations = {
        1: { # Aries
            "Personality": "Ruled by Mars, you possess an indomitable spirit and a natural drive to lead. You are courageous, impulsive, and often the first to initiate action. Your energy is boundless, but you may struggle with patience. You value independence above all and face challenges head-on, often inspiring others with your fearless approach to life.",
            "Physical": "You typically have a medium to athletic build with a strong, energetic constitution. Features are often sharp or distinct, possibly with a ruddy complexion. You may walk quickly and have an intense gaze. There is a vibrancy to your physical presence that commands attention.",
            "Career": "You thrive in competitive environments where initiative is rewarded. Excellent fields include military, police, surgery, engineering, or professional sports. You prefer roles where you can be your own boss or lead a team. Routine desk jobs may bore you; you need action and tangible results.",
            "Health": "You are prone to headaches, migraines, and high fevers due to the intense heat of Mars. Injuries to the head or face are common. Managing stress and anger is crucial for your well-being. Regular physical activity is essential to burn off excess energy and maintain balance.",
            "Rel": "In love, you are passionate, direct, and protective. You enjoy the chase and are often the initiator. However, you can be argumentative or self-centered at times. You need a partner who can match your energy but also has the patience to balance your impulsiveness."
        },
        2: { # Taurus
            "Personality": "Ruled by Venus, you are the embodiment of stability, patience, and endurance. You are grounded and practical, valuing security and comfort over risk. While you are incredibly reliable and loyal, you can also be quite stubborn and resistant to change. You have a deep appreciation for beauty, nature, and the finer things in life.",
            "Physical": "You tend to have a solid, sturdy, or well-proportioned build that exudes strength. A thick or prominent neck is a classic trait, along with large, expressive eyes and a pleasing face. Your movement is often deliberate and unhurried, reflecting your calm inner nature.",
            "Career": "You excel in professions that require patience and resource management. Banking, finance, agriculture, luxury goods, singing, or the culinary arts are excellent fits. You are a hard worker who builds wealth steadily. You prefer stable environments with clear long-term rewards.",
            "Health": "Your sensitive areas are the throat, neck, and thyroid. You may be prone to sore throats, tonsillitis, or thyroid imbalances. There is also a tendency to gain weight easily due to a love for good food, so maintaining a balanced diet and regular exercise routine is important.",
            "Rel": "You are a deeply loyal, sensual, and possessive partner. You seek a relationship that offers long-term security and physical affection. You are slow to fall in love, but once committed, you are in it for life. You express love through tangible gifts and physical touch."
        },
        3: { # Gemini
            "Personality": "Ruled by Mercury, you are quick-witted, adaptable, and intellectually curious. You love gathering information and communicating with others. You are charming and sociable, but your dual nature can make you indecisive or restless. You crave variety and mental stimulation, often juggling multiple interests at once.",
            "Physical": "You are likely to have a tall, slender, and agile frame. Your arms and hands may be prominent or expressive when you speak. You often look younger than your actual age due to your lively energy. Your eyes are quick and darting, always observing the environment.",
            "Career": "Your best careers involve communication, travel, and intellect. Journalism, writing, sales, marketing, teaching, or IT are natural fits. You dislike monotony and thrive in fast-paced environments where you can network and solve problems. Multi-tasking is your superpower.",
            "Health": "You are prone to issues related to the nervous system, lungs, and shoulders. Anxiety, restlessness, or respiratory infections like asthma or bronchitis can be common. It is vital for you to practice relaxation techniques to calm your active mind.",
            "Rel": "You view relationships as a meeting of minds. You need a partner who is intellectually stimulating and fun. You can be flirtatious and light-hearted, avoiding heavy emotional displays. Boredom is the enemy of your relationships; you need constant conversation and variety."
        },
        4: { # Cancer
            "Personality": "Ruled by the Moon, you are deeply emotional, intuitive, and nurturing. You have a strong attachment to home, family, and your roots. While you are incredibly caring and protective of loved ones, you can also be moody and sensitive to criticism. You have a hard shell but a very soft heart.",
            "Physical": "You generally have a rounder face with soft, pleasing features and expansive eyes. You may have a tendency to carry weight in the midsection or chest area. Your constitution is governed by fluids, so you might retain water easily. Your appearance often radiates a gentle, approachable vibe.",
            "Career": "You excel in caring professions or roles related to home and land. Nursing, psychology, teaching, real estate, hospitality, or human resources are great choices. You are a natural caretaker and work best in environments where you feel emotionally connected to your work.",
            "Health": "Your sensitive areas are the stomach, chest, and digestive system. You are prone to digestive upsets caused by emotional stress. Respiratory issues or chest congestion can also occur. Emotional well-being is directly linked to your physical health.",
            "Rel": "You crave deep emotional security and belonging in a relationship. You are a devoted and protective partner who mothers/fathers your significant other. However, you can be clingy or overly sensitive. You value loyalty above all else and seek a partner who wants to build a home.",
        },
        5: { # Leo
            "Personality": "Ruled by the Sun, you are born to lead and shine. You are confident, generous, and warm-hearted, with a natural flair for the dramatic. You love being the center of attention and have a strong sense of personal pride. While noble and loyal, you can also be arrogant or domineering if unchecked.",
            "Physical": "You tend to have a broad upper body, strong shoulders, and a majestic gait. Your head might be large or round, often with a prominent mane of hair. You have a commanding presence and a bright, sunny disposition that draws people to you naturally.",
            "Career": "You belong in leadership roles or the public eye. Politics, entertainment, management, government, or creative arts are ideal. You dislike taking orders and thrive where you can be the boss or the star. You need a career that offers recognition, status, and creative expression.",
            "Health": "The heart, spine, and upper back are your vulnerable areas. You may face issues related to blood pressure, heart palpitations, or back pain. It is essential to keep your ego in check to reduce stress on your heart. Regular cardio is beneficial.",
            "Rel": "In love, you are passionate, romantic, and extremely loyal. You treat your partner like royalty but expect the same adoration in return. You can be jealous if you feel ignored. You need a partner who appreciates your grandeur and is willing to let you shine.",
        },
        6: { # Virgo
            "Personality": "Ruled by Mercury, you are practical, analytical, and meticulous. You have a keen eye for detail and a strong desire to serve and improve things. You are intelligent and modest but can be prone to worry and over-thinking. Perfectionism is your strength and your weakness.",
            "Physical": "You typically have a slender, youthful, and neat appearance. Your features are often sharp or delicate, and you may look younger than your age. You usually pay great attention to hygiene and dress. Your eyes are observant and intelligent, missing nothing.",
            "Career": "You excel in jobs requiring precision, analysis, and service. Accounting, medicine, data analysis, editing, coding, or secretarial work are perfect. You are the person who fixes the details others miss. You prefer being a highly valued specialist rather than the figurehead.",
            "Health": "Your sensitive areas are the digestive system and intestines. You are prone to nervous tension which often manifests as stomach issues or allergies. Diet is critical for you; you thrive on a clean, regulated diet. Mental relaxation is necessary to prevent burnout.",
            "Rel": "You are a practical and devoted partner who shows love through acts of service. You may not be overly romantic in a dramatic way, but you are incredibly reliable. You can be critical of your partner, but it comes from a desire to help. You seek an intelligent and tidy mate.",
        },
        7: { # Libra
            "Personality": "Ruled by Venus, you are the diplomat of the zodiac. You value harmony, balance, and justice above all. You are charming, social, and refined, with a dislike for conflict. However, your desire to please everyone can make you indecisive or prone to superficiality. You thrive in partnership.",
            "Physical": "You are often blessed with a well-proportioned body and pleasing, symmetrical features. You may have a beautiful smile and dimples. Your appearance is usually graceful and stylish. You tend to age well and maintain a youthful charm throughout life.",
            "Career": "You excel in fields requiring negotiation, aesthetics, or public relations. Law, diplomacy, fashion design, interior decorating, or counseling are excellent fits. You work best in partnerships rather than alone. You need a harmonious and aesthetically pleasing workspace.",
            "Health": "The kidneys, lower back, and skin are your vulnerable areas. You may suffer from back pain or urinary tract issues. Balance is key for you—avoiding excess in food or drink is important to maintain your health and complexion.",
            "Rel": "You are in love with love. Relationships are central to your existence, and you hate being alone. You are a romantic, charming, and accommodating partner. However, you may struggle to be direct about your needs to avoid conflict. You need a partner who brings balance and peace.",
        },
        8: { # Scorpio
            "Personality": "Ruled by Mars and Ketu, you are intense, magnetic, and deeply secretive. You possess incredible willpower and emotional depth. You are transformative and resilient, able to rise from ashes. While fiercely loyal, you can be vindictive or jealous if betrayed. You see beneath the surface of everything.",
            "Physical": "You have a strong, sturdy build with a powerful physical presence. Your eyes are often piercing, hypnotic, and intense. You may have distinct eyebrows or a prominent nose. You exude a mysterious charisma that can be both intimidating and attractive.",
            "Career": "You thrive in careers involving research, transformation, or crisis management. Surgery, detective work, psychology, occult studies, mining, or research are ideal. You have the focus to solve deep mysteries and the courage to handle difficult truths.",
            "Health": "Your sensitive areas are the reproductive system and excretory organs. You may be prone to issues in these areas or hidden, hard-to-diagnose ailments. Your intense emotions can impact your health, so finding a healthy outlet for emotional release is vital.",
            "Rel": "Love for you is an all-or-nothing experience. You crave deep, soul-level intimacy and possessiveness. You are incredibly loyal and protective but expect absolute fidelity. Betrayal is rarely forgiven. You need a partner who can handle your emotional intensity and depth.",
        },
        9: { # Sagittarius
            "Personality": "Ruled by Jupiter, you are the eternal optimist and seeker of truth. You are adventurous, philosophical, and freedom-loving. You have a blunt honesty that can sometimes offend, but your intentions are usually noble. You love learning, traveling, and exploring the higher meaning of life.",
            "Physical": "You are likely to be tall and athletic with a strong frame. You may have a broad forehead and a jovial, open expression. You tend to walk with a confident, perhaps slightly careless, stride. There is a sense of nobility and friendliness in your appearance.",
            "Career": "You excel in fields related to wisdom, law, and expansion. Teaching, publishing, religion, law, travel, or import-export businesses are great fits. You dislike micromanagement and need a career that offers freedom, travel, and a sense of purpose.",
            "Health": "The hips, thighs, and liver are your vulnerable areas. You may be prone to sciatica, hip injuries, or liver issues caused by overindulgence. You tend to put on weight easily due to your love for the good life, so moderation is key.",
            "Rel": "You need a partner who is also your best friend and travel companion. You value freedom in relationships and dislike clinginess. You are honest and fun-loving but can be commitment-shy if you feel trapped. You seek a partner who shares your philosophical outlook.",
        },
        10: { # Capricorn
            "Personality": "Ruled by Saturn, you are ambitious, disciplined, and practical. You play the long game, willing to work harder than anyone else to achieve your goals. You can be reserved, serious, or pessimistic, but you possess a dry wit. You value tradition, structure, and respect.",
            "Physical": "You tend to have a lean, wiry build that endures well. Your features may be prominent or bony, with a serious or mature expression even in youth. You may have prominent knees. You often look better and healthier as you age, reversing the aging process.",
            "Career": "You are built for the corporate world, administration, and leadership. Management, government, construction, mining, or farming are suitable. You are a natural authority figure who climbs the ladder of success steadily. You value status and tangible achievements.",
            "Health": "Your sensitive areas are the knees, bones, joints, and skin. You may suffer from arthritis, knee injuries, or dry skin. Melancholy or depression can also affect your vitality. You need to ensure you get enough calcium and keep your joints moving.",
            "Rel": "You take relationships seriously and are cautious in love. You look for a partner who is responsible, ambitious, and respectable. You are not one for public displays of emotion but show love through loyalty and providing security. You are a dutiful and committed partner.",
        },
        11: { # Aquarius
            "Personality": "Ruled by Saturn and Rahu, you are innovative, unconventional, and humanitarian. You value intellectual freedom and are often ahead of your time. You can be friendly yet detached, valuing the group over the individual. You are stubborn about your ideals and love to break traditions.",
            "Physical": "You often have a tall, unique, or unusual appearance. Your features might be striking or unconventional. You may have a friendly but distant look in your eyes. There is often something 'electric' or distinct about your vibe that sets you apart from the crowd.",
            "Career": "You excel in fields involving technology, science, or social change. IT, aviation, astrology, scientific research, or social work are excellent. You work best in groups or organizations where you can implement progressive ideas. You need a role that allows for innovation.",
            "Health": "The ankles, calves, and circulatory system are your weak points. You may be prone to sprains, varicose veins, or cramping in the lower legs. Nervous disorders can also occur. It is important for you to keep your circulation moving.",
            "Rel": "You need a partner who respects your freedom and individuality. You are attracted to intelligence and uniqueness rather than pure emotion. You can be aloof or unpredictable in love. Friendship is the foundation of your romance; you need a mental connection first.",
        },
        12: { # Pisces
            "Personality": "Ruled by Jupiter, you are compassionate, imaginative, and deeply spiritual. You are a dreamer who feels the emotions of others. You can be impractical or escapist, preferring fantasy to reality. You are incredibly adaptable, artistic, and kind, often sacrificing your needs for others.",
            "Physical": "You tend to have a soft, fleshy, or gentle appearance. Your eyes are often large, dreamy, and watery. You may have smaller feet or hands. Your demeanor is usually calm and fluid, lacking sharp edges. You may struggle with maintaining high energy levels.",
            "Career": "You thrive in creative, healing, or spiritual professions. Music, film, photography, nursing, counseling, charity work, or spirituality are ideal. You dislike high-pressure, competitive environments. You need a career that allows you to use your intuition and empathy.",
            "Health": "Your sensitive areas are the feet and the lymphatic system. You may be prone to foot issues, swelling, or water retention. You are also sensitive to drugs and alcohol, so caution is needed. Sleep is your best medicine; you need plenty of it to recharge.",
            "Rel": "You are a hopeless romantic who seeks a soulmate connection. You are incredibly giving, forgiving, and empathetic in love. However, you can be prone to seeing partners through rose-colored glasses. You need a partner who grounds you without crushing your dreams.",
        }
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
    d_in = st.date_input("DOB", value=datetime.date(1993, 4, 23), min_value=datetime.date(1900,1,1), format="DD/MM/YYYY")
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
        
    # 2. CHARTS TAB
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
            
    # 3. DASHA TAB (Cascading Tables)
    with tab3:
        d_system = st.radio("Dasha System:", ["Vimshottari", "Yogini (Coming Soon)"], horizontal=True)
        
        if "Vimshottari" in d_system:
            
            # --- LEVEL 1: MAHADASHA ---
            st.markdown("### 1. Mahadasha")
            md_list = calculate_vimshottari_structure(d['JD'], d['BirthDate'])
            
            # Display MD Table
            md_data = []
            for m in md_list:
                md_data.append({"Lord": m['Lord'], "Start": m['Start'].strftime('%d-%b-%Y'), "End": m['End'].strftime('%d-%b-%Y'), "Duration": f"{m['FullYears']} Years"})
            st.table(pd.DataFrame(md_data))
            
            # Selector for Level 2
            md_options = [f"{m['Lord']} ({m['Start'].strftime('%Y')}-{m['End'].strftime('%Y')})" for m in md_list]
            sel_md_idx = st.selectbox("Select Mahadasha to view Antardashas:", range(len(md_list)), format_func=lambda x: md_options[x])
            sel_md = md_list[sel_md_idx]
            
            st.divider()
            
            # --- LEVEL 2: ANTARDASHA ---
            st.markdown(f"### 2. Antardasha (under {sel_md['Lord']})")
            ad_list = get_sub_periods(sel_md['Lord'], sel_md['Start'], sel_md['FullYears'])
            
            # Display AD Table
            ad_data = []
            for a in ad_list:
                ad_data.append({"Lord": a['Lord'], "Start": a['Start'].strftime('%d-%b-%Y'), "End": a['End'].strftime('%d-%b-%Y')})
            st.table(pd.DataFrame(ad_data))
            
            # Selector for Level 3
            ad_options = [f"{a['Lord']} (ends {a['End'].strftime('%d-%b-%Y')})" for a in ad_list]
            sel_ad_idx = st.selectbox("Select Antardasha to view Pratyantardashas:", range(len(ad_list)), format_func=lambda x: ad_options[x])
            sel_ad = ad_list[sel_ad_idx]
            
            st.divider()
            
            # --- LEVEL 3: PRATYANTARDASHA ---
            st.markdown(f"### 3. Pratyantardasha (under {sel_ad['Lord']})")
            pd_list = get_sub_periods(sel_ad['Lord'], sel_ad['Start'], sel_ad['Duration'])
            
            pd_data = []
            for p in pd_list:
                pd_data.append({"Lord": p['Lord'], "Start": p['Start'].strftime('%d-%b-%Y'), "End": p['End'].strftime('%d-%b-%Y')})
            st.table(pd.DataFrame(pd_data))
            
            # Selector for Level 4
            pd_options = [f"{p['Lord']} (ends {p['End'].strftime('%d-%b-%Y')})" for p in pd_list]
            sel_pd_idx = st.selectbox("Select Pratyantardasha to view Sookshma:", range(len(pd_list)), format_func=lambda x: pd_options[x])
            sel_pd = pd_list[sel_pd_idx]
            
            st.divider()

            # --- LEVEL 4: SOOKSHMA ---
            st.markdown(f"### 4. Sookshma Dasha (under {sel_pd['Lord']})")
            sd_list = get_sub_periods(sel_pd['Lord'], sel_pd['Start'], sel_pd['Duration'])
            
            sd_data = []
            for s in sd_list:
                sd_data.append({"Lord": s['Lord'], "Start": s['Start'].strftime('%d-%b-%Y'), "End": s['End'].strftime('%d-%b-%Y')})
            st.table(pd.DataFrame(sd_data))
            
            # Selector for Level 5
            sd_options = [f"{s['Lord']} (ends {s['End'].strftime('%d-%b')})" for s in sd_list]
            sel_sd_idx = st.selectbox("Select Sookshma to view Prana:", range(len(sd_list)), format_func=lambda x: sd_options[x])
            sel_sd = sd_list[sel_sd_idx]
            
            st.divider()

            # --- LEVEL 5: PRANA ---
            st.markdown(f"### 5. Prana Dasha (under {sel_sd['Lord']})")
            pn_list = get_sub_periods(sel_sd['Lord'], sel_sd['Start'], sel_sd['Duration'])
            
            pn_data = []
            for p in pn_list:
                pn_data.append({"Lord": p['Lord'], "Start": p['Start'].strftime('%d-%b %H:%M'), "End": p['End'].strftime('%d-%b %H:%M')})
            st.table(pd.DataFrame(pn_data))
            
            # Selector for Level 6
            pn_options = [f"{p['Lord']} (ends {p['End'].strftime('%d-%b %H:%M')})" for p in pn_list]
            sel_pn_idx = st.selectbox("Select Prana to view Deha:", range(len(pn_list)), format_func=lambda x: pn_options[x])
            sel_pn = pn_list[sel_pn_idx]

            st.divider()

            # --- LEVEL 6: DEHA ---
            st.markdown(f"### 6. Deha Dasha (under {sel_pn['Lord']})")
            dd_list = get_sub_periods(sel_pn['Lord'], sel_pn['Start'], sel_pn['Duration'])
            
            dd_data = []
            for d_item in dd_list:
                dd_data.append({"Lord": d_item['Lord'], "Start": d_item['Start'].strftime('%d-%b %H:%M'), "End": d_item['End'].strftime('%d-%b %H:%M')})
            st.table(pd.DataFrame(dd_data))

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
                print(f"API Error: {e}")
                st.warning("✨ The cosmic channels are momentarily quiet. Please try again in a few moments. 🙏")

else:
    st.title("☸️ TaraVaani")
    st.info("👈 Enter details to generate chart.")
