import streamlit as st
import uuid

# Diccionario de perfiles con mensajes base
system_messages = {
    "Adultos": "Eres un asistente empático que brinda apoyo emocional a adultos.",
    "Adolescentes": "Eres un compañero comprensivo para adolescentes que buscan orientación.",
    "Niños": "Eres un amigo amable que ayuda a los niños a entender sus emociones."
}

# Simulación de respuesta del asistente
def chat(prompt, history, perfil):
    # En una versión real, acá iría la llamada a la API
    return f"Gracias por compartir eso. ¿Querés que exploremos cómo te sentís respecto a eso?"

# Función principal
def main():
    st.set_page_config(page_title="Mindly", page_icon="🧠", layout="centered")

    if "history" not in st.session_state:
        st.session_state.history = []
    if "current_profile" not in st.session_state:
        st.session_state.current_profile = "Adultos"

    st.title("🧠 Mindly")
    st.markdown("Tu compañero de bienestar mental. Conversaciones empáticas y apoyo emocional.")

    # Selector de perfil
    st.selectbox("Elegí tu perfil:", options=list(system_messages.keys()), key="current_profile")

    # Botón para nueva conversación
    if st.button("🗑️ Nueva conversación"):
        st.session_state.history = []

    # Mensaje inicial si no hay historial
    if len(st.session_state.history) == 0:
        st.chat_message("assistant").markdown("¡Hola! ¿En qué puedo ayudarte hoy?")

    # Mostrar historial
    for i in range(0, len(st.session_state.history), 2):
        st.chat_message("user").markdown(st.session_state.history[i]["content"])
        if i + 1 < len(st.session_state.history):
            st.chat_message("assistant").markdown(st.session_state.history[i + 1]["content"])

    # Input del usuario
    if prompt := st.chat_input("💬 Escribí lo que estás pensando..."):
        st.session_state.history.append({"role": "user", "content": prompt})

        respuesta = chat(prompt, st.session_state.history, st.session_state.current_profile)
        st.session_state.history.append({"role": "assistant", "content": respuesta})

        st.chat_message("assistant").markdown(respuesta)

if __name__ == "__main__":
    main()
