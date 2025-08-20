import streamlit as st
import uuid
import requests
import re

st.secrets["mistralapi"]

# Diccionario de perfiles con system prompts breves
system_messages = {
    "Adultos": "Eres un asistente empático que brinda apoyo emocional a adultos.",
    "Adolescentes": "Eres un compañero comprensivo para adolescentes que buscan orientación.",
    "Niños": "Eres un amigo amable que ayuda a los niños a entender sus emociones."
}

# Función que llama a la API de Mistral
def chat(prompt, history, perfil):
    system_prompt = system_messages.get(perfil, "Eres un asistente empático.")
    trimmed_history = history[-6:]  # últimos 3 pares de mensajes

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(trimmed_history)
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "mistral-7b-instruct",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 512
    }

    headers = {
        "Authorization": f"Bearer {st.secrets['mistralapi']}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post("https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return "😕 Ups, hubo un problema al generar la respuesta. Intentá de nuevo más tarde."

# Función principal
def main():
    st.set_page_config(page_title="Mindly", page_icon="🧠", layout="centered")

    if "history" not in st.session_state:
        st.session_state.history = []
    if "current_profile" not in st.session_state:
        st.session_state.current_profile = "Adultos"

    st.title("🧠 Mindly")
    st.markdown("Tu compañero de bienestar mental. Conversaciones empáticas y apoyo emocional.")

    st.selectbox("Elegí tu perfil:", options=list(system_messages.keys()), key="current_profile")

    if st.button("🗑️ Nueva conversación"):
        st.session_state.history = []

    if len(st.session_state.history) == 0:
        st.chat_message("assistant").markdown("¡Hola! ¿En qué puedo ayudarte hoy?")

    for i in range(0, len(st.session_state.history), 2):
        st.chat_message("user").markdown(st.session_state.history[i]["content"])
        if i + 1 < len(st.session_state.history):
            st.chat_message("assistant").markdown(st.session_state.history[i + 1]["content"])

    if prompt := st.chat_input("💬 Escribí lo que estás pensando..."):
        st.session_state.history.append({"role": "user", "content": prompt})

        with st.spinner("🧠 Mindly está reflexionando..."):
            respuesta = chat(prompt, st.session_state.history, st.session_state.current_profile)

        st.session_state.history.append({"role": "assistant", "content": respuesta})
        st.chat_message("assistant").markdown(respuesta)

if __name__ == "__main__":
    main()
