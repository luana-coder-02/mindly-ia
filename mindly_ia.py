import streamlit as st
import requests

MISTRAL_API_KEY = st.secrets.get("mistralapi")

# Configuración básica
st.set_page_config(page_title="Mindly", layout="centered")
st.title("🧘 Mindly – Tu espacio de bienestar")

# Estado de sesión
if "messages" not in st.session_state:
    st.session_state.messages = []

# Entrada del usuario
user_input = st.chat_input("¿Cómo te sentís hoy?")

# Mostrar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Función para llamar a Mistral
def get_mistral_response(prompt, api_key):
    # La variable que se usa aquí debe ser el parámetro 'api_key'
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return "Ups... algo falló, pero estoy acá para vos. Podés volver a intentarlo o simplemente respirar un momento."

# Procesar entrada
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        # Se obtiene la clave directamente aquí
        api_key = st.secrets.get("mistralapi", "")
        # Se pasa la clave a la función correctamente
        response = get_mistral_response(user_input, api_key)
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
