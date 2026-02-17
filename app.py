
import streamlit as st
import google.generativeai as genai

st.title("🔑 API Key Diagnostic")

# 1. Configure the API
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("No API Key found!")
    st.stop()

# 2. Ask Google: "What models can I see?"
st.write("Checking available models for your API Key...")
try:
    model_list = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            model_list.append(m.name)
            
    st.success(f"Found {len(model_list)} models!")
    st.write(model_list)
    
    # 3. The Verdict
    if 'models/gemini-1.5-flash' in model_list:
        st.write("✅ Flash is available! (The issue was code/library)")
    else:
        st.error("❌ Flash is MISSING from your key's permission list.")
        st.info("💡 FIX: You must create a NEW API Key in a fresh Google AI Studio project.")
        
except Exception as e:
    st.error(f"Error: {e}")
