import streamlit as st
from huggingface_hub import InferenceClient

# Cargar la API Key desde secretos
HF_TOKEN = st.secrets.get("hf_token")

# Inicializar cliente de Hugging Face
client = InferenceClient("mistralai/Mistral-7B-Instruct-v0.1", token=HF_TOKEN)

# Interfaz de Mindly
st.title("🧠 Mindly - Tu espacio de escucha empática")

user_input = st.text_area("¿Cómo te sentís hoy?", placeholder="Podés contarme lo que quieras...")

if st.button("Hablar con Mindly") and user_input:
    with st.spinner("Mindly está pensando con cariño..."):
        response = client.text_generation(
            prompt=f"<|system|>Eres un asistente cálido y empático llamado Mindly.<|user|>{user_input}<|assistant|>",
            max_new_tokens=300,
            temperature=0.7,
            top_p=0.95
        )
        st.markdown("### 🌟 Mindly responde:")
        st.write(response)
