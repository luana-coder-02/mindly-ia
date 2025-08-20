import streamlit as st
import requests

# Configuración
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
HF_TOKEN = st.secrets["hf_token"]  # Asegurate de tener esto en .streamlit/secrets.toml

headers = {
    "Authorization": f"Bearer {hf_token}",
    "Content-Type": "application/json"
}

# Función para generar respuesta
def generar_respuesta(prompt):
    payload = {
        "inputs": prompt,
        "parameters": {
            "temperature": 0.7,
            "max_new_tokens": 256,
            "return_full_text": False
        }
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        output = response.json()
        return output[0]["generated_text"]
    except Exception as e:
        return "Ups... algo salió mal. Pero no te preocupes, estoy acá para ayudarte 💛"

# Interfaz Streamlit
st.set_page_config(page_title="Mindly", page_icon="🧠", layout="centered")
st.title("🧠 Mindly - Tu espacio de bienestar emocional")

user_input = st.text_area("¿Cómo te sentís hoy?", placeholder="Podés contarme lo que quieras...")

if st.button("Hablar con Mindly"):
    if user_input.strip():
        with st.spinner("Mindly está pensando..."):
            respuesta = generar_respuesta(user_input)
            st.markdown(f"**Mindly:** {respuesta}")
    else:
        st.warning("Por favor, escribí algo para comenzar 💬")
