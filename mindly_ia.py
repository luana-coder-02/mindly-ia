import streamlit as st
import json
import re
import requests
import uuid
from datetime import datetime
from functools import lru_cache
import html
    

# --- 1. Configuración inicial y variables globales ---
ADMIN_MODE = st.query_params.get("admin") == "true"
MAX_HISTORY = 8
MAX_PROMPT_LENGTH = 1000
LOG_FILE = "chat_log.json"

MISTRAL_API_KEY = st.secrets.get("mistralapi")
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GIST_ID = st.secrets.get("GIST_ID", "")
GIST_FILENAME = "chat_log.json"

if not MISTRAL_API_KEY:
    st.error("Error: La clave 'mistralapi' no está configurada en los secretos de Streamlit.")
    st.stop()

# --- 2. Definición de clases y funciones de ayuda ---
class GistManager:
    def __init__(self, token, gist_id=None):
        self.token = token
        self.gist_id = gist_id
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.com"
        }
    
    def crear_gist(self, filename, content, description="Chat logs de Mindly"):
        data = {
            "description": description,
            "public": False,
            "files": {
                filename: {
                    "content": content
                }
            }
        }
        response = requests.post("https://api.github.com/gists", headers=self.headers, json=data)
        if response.status_code == 201:
            gist_data = response.json()
            self.gist_id = gist_data["id"]
            return True, gist_data["id"], gist_data["html_url"]
        else:
            return False, None, response.json()
    
    def actualizar_gist(self, filename, content):
        if not self.gist_id:
            return False, "No hay Gist ID configurado"
        data = {
            "files": {
                filename: {
                    "content": content
                }
            }
        }
        response = requests.patch(f"https://api.github.com/gists/{self.gist_id}", headers=self.headers, json=data)
        if response.status_code == 200:
            return True, response.json()["html_url"]
        else:
            return False, response.json()
    
    def obtener_gist(self):
        if not self.gist_id:
            return False, "No hay Gist ID configurado"
        response = requests.get(f"https://api.github.com/gists/{self.gist_id}", headers=self.headers)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.json()
    
    def subir_logs(self, logs_data):
        content = json.dumps(logs_data, ensure_ascii=False, indent=2)
        if self.gist_id:
            success, result = self.actualizar_gist("chat_log.json", content)
            return success, result
        else:
            success, gist_id, url = self.crear_gist("chat_log.json", content)
            if success:
                st.session_state.gist_id = gist_id
            return success, url if success else gist_id

def verificar_admin():
    """Verifica si el usuario actual es administrador"""
    return ADMIN_MODE

def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&family=Inter:wght@300;400;500&display=swap');
    :root {
        --primary-color: #6B73FF;
        --secondary-color: #9B59B6;
        --accent-color: #3498DB;
        --background-soft: #F8F9FF;
        --text-primary: #2C3E50;
        --text-secondary: #5A6C7D;
        --success-color: #27AE60;
        --warning-color: #F39C12;
        --gentle-purple: #E8E4F3;
        --gentle-blue: #E3F2FD;
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }
    .block-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 2rem;
        margin-top: 2rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    h1 {
        font-family: 'Poppins', sans-serif;
        color: var(--primary-color);
        text-align: center;
        font-weight: 600;
        font-size: 2.5rem;
        margin-bottom: 1rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .subtitle {
        font-family: 'Inter', sans-serif;
        color: var(--text-secondary);
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 15px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        font-family: 'Inter', sans-serif;
        border-left: 4px solid transparent;
    }
    [data-testid="stUserChatMessage"] {
        background: linear-gradient(135deg, var(--gentle-blue) 0%, #E1F5FE 100%);
        border-left-color: var(--accent-color);
    }
    [data-testid="stChatMessage"] {
        background: linear-gradient(135deg, var(--gentle-purple) 0%, #F3E5F5 100%);
        border-left-color: var(--secondary-color);
    }
    [data-testid="stChatInput"] {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 25px;
        padding: 0.5rem;
        margin-top: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        border: 2px solid rgba(107, 115, 255, 0.3);
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: var(--primary-color);
        box-shadow: 0 4px 20px rgba(107, 115, 255, 0.3);
    }
    [data-testid="stSpinner"] {
        color: var(--primary-color);
    }
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1.5rem;
        font-family: 'Poppins', sans-serif;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(107, 115, 255, 0.4);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--gentle-purple) 0%, white 100%);
    }
    .stMarkdown {
        font-family: 'Inter', sans-serif;
        color: var(--text-primary);
        line-height: 1.6;
    }
    .stChatMessage:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        transition: all 0.3s ease;
    }
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    .main {
        animation: fadeInUp 0.8s ease-out;
    }
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--primary-color), var(--secondary-color));
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-color);
    }
    </style>
    """, unsafe_allow_html=True)

def generar_session_id():
    """Genera un ID único para la sesión"""
    return str(uuid.uuid4())[:8]

def cargar_sesion_usuario(session_id):
    """Carga una sesión específica del usuario"""
    return st.session_state.all_sessions_log.get(session_id, {}).get("history", [])

def guardar_sesion_usuario(session_id, history):
    """Guarda la conversación de la sesión actual en el log general."""
    session_data = {
        "timestamp": datetime.now().isoformat(),
        "history": history
    }
    st.session_state.all_sessions_log[session_id] = session_data
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.all_sessions_log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error al guardar el archivo: {e}")

def detectar_intencion(mensaje):
    mensaje = mensaje.lower()
    if re.search(r"\b(ansiedad|depresión|estrés|angustia|tristeza|miedo)\b", mensaje):
        return "consulta_emocional"
    elif re.search(r"\b(ayuda|consejo|apoyo|orientación|escuchar)\b", mensaje):
        return "solicitud_ayuda"
    elif re.search(r"\b(técnica|herramienta|ejercicio|estrategia|psicoterapia|mindfulness|respiración)\b", mensaje):
        return "consulta_tecnica"
    elif re.search(r"\b(urgente|crisis|emergencia)\b", mensaje):
        return "situacion_urgente"
    else:
        return "intencion_desconocida"

def clean_markdown(text: str) -> str:
    """Limpieza exhaustiva de Markdown"""
    text = re.sub(r'\n{2,}', '\n\n', text)  # Espacios entre párrafos
    text = re.sub(r'^\s*#+\s*(.+)', r'**\1**', text, flags=re.MULTILINE)  # Encabezados a negrita
    text = re.sub(r'^\s*?([•o*\-✓✔✔✅])\s?(.+)', r'- \2', text, flags=re.MULTILINE)  # Listas uniformes
    text = re.sub(r'([a-zA-ZáéíóúÁÉÍÓÚñÑ])\*\s?([a-zA-ZáéíóúÁÉÍÓÚñÑ])', r'\1\2', text) # Eliminar asteriscos en medio de palabras
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # Eliminar enlaces
    text = re.sub(r'`{3}.*?`{3}', '', text, flags=re.DOTALL)  # Eliminar bloques código
    return text.strip()

@lru_cache(maxsize=100)
def get_cached_response(prompt: str, profile: str) -> str:
    """Cache para preguntas frecuentes"""
    # La función chat se llama con un historial vacío para que el prompt sea la única clave de caché
    return chat(prompt, [], profile)

system_messages = {
    "Adultos": """
        Eres Mindly, un chatbot empático y profesional, experto en ayudar a adultos a encontrar información clara sobre psicología.
        Responde de forma cercana y sin jerga técnica.
        Si notas que alguien necesita apoyo emocional urgente, sugiérele que busque ayuda profesional inmediata.
        Utiliza siempre Markdown para dar formato a tus respuestas. Usa listas, negritas y encabezados para que la información sea clara y fácil de leer. Asegúrate de usar saltos de línea para separar las ideas.
    """,
    "Adolescentes": """
        Eres Mindly, un compañero de confianza para adolescentes. Hablas de forma sencilla y comprensible, ofreciendo apoyo y consejos sobre temas como el estrés escolar, la presión social y la ansiedad.
        Si notas que alguien necesita apoyo emocional urgente, sugiérele que busque ayuda profesional inmediata.
        Utiliza siempre Markdown para dar formato a tus respuestas. Usa listas, negritas y encabezados para que la información sea clara y fácil de leer. Asegúrate de usar saltos de línea para separar las ideas.
    """,
    "Padres": """
        Eres Mindly, un asistente para padres. Proporcionas información y estrategias para entender y apoyar el desarrollo emocional de sus hijos. Tu tono es profesional y calmado.
        Utiliza siempre Markdown para dar formato a tus respuestas. Usa listas, negritas y encabezados para que la información sea clara y fácil de leer. Asegúrate de usar saltos de línea para separar las ideas.
    """,
    "Profesionales": """
        Eres Mindly, un asistente avanzado para profesionales de la psicología. Tu conocimiento es profundo y puedes ofrecer información especializada, resúmenes de teorías o técnicas de terapia.
        Utiliza siempre Markdown para dar formato a tus respuestas. Usa listas, negritas y encabezados para que la información sea clara y fácil de leer. Asegúrate de usar saltos de línea para separar las ideas.
    """
}

@st.cache_data(show_spinner=False)
def chat(message, history, profile):
    system_message = system_messages.get(profile, system_messages["Adultos"])
    messages = [{"role": "system", "content": system_message.strip()}]
    messages.extend(history[-MAX_HISTORY*2:])
    messages.append({"role": "user", "content": message})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    payload = {
        "model": "mistral-large-latest",
        "messages": messages
    }

    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        response_data = response.json()
        respuesta_final = response_data["choices"][0]["message"]["content"]

        return clean_markdown(respuesta_final)

    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API de Mistral: {e}")
        return ""
    except KeyError:
        st.error("Error al procesar la respuesta de la API de Mistral.")
        return ""


# --- 3. Función principal de la aplicación ---
def main():
    if 'history' not in st.session_state:
        st.session_state.history = []
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = str(uuid.uuid4())[:8]
    if "current_profile" not in st.session_state:
        st.session_state.current_profile = "Adultos"
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            st.session_state.all_sessions_log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        st.session_state.all_sessions_log = {}

    st.set_page_config(
        page_title="Mindly - Chat de Psicología", 
        page_icon="🧠",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    load_custom_css()

    is_admin = verificar_admin()

    if is_admin:
        st.markdown("""
        <div class="admin-indicator">
            👑 Modo Administrador
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1>🧠 Mindly</h1>
            <p class="subtitle">Tu compañero de bienestar mental • Conversaciones empáticas y apoyo psicológico</p>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("### 👤 Elige tu perfil")
        st.session_state.current_profile = st.selectbox(
            "Elige tu perfil:",
            list(system_messages.keys()),
            index=list(system_messages.keys()).index(st.session_state.current_profile),
            label_visibility="collapsed"
        )
        st.markdown("### ℹ️ Sobre Mindly")
        st.markdown("""
        Mindly es tu asistente de bienestar mental, diseñado para:
        - 💬 Conversaciones empáticas
        - 🎯 Técnicas de manejo emocional  
        - 🔍 Información psicológica confiable
        - 🆘 Orientación en momentos difíciles

        **Recuerda:** En casos de emergencia, contacta servicios profesionales.
        """)

        st.markdown("---")
        st.markdown("### 💭 Conversación Actual")
        st.info("Para guardar la conversación, puedes usar el botón 'Guardar'. Los logs completos se almacenan para el administrador.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Nueva Conversación"):
                if st.session_state.history and len(st.session_state.history) > 0:
                    session_id = st.session_state.get('current_session_id', str(uuid.uuid4())[:8])
                    guardar_sesion_usuario(session_id, st.session_state.history)
                st.session_state.history = []
                st.session_state.current_session_id = str(uuid.uuid4())[:8]
                st.rerun()

        with col2:
            if st.button("Guardar"):
                if st.session_state.history and len(st.session_state.history) > 0:
                    session_id = st.session_state.get('current_session_id', str(uuid.uuid4())[:8])
                    guardar_sesion_usuario(session_id, st.session_state.history)
                    st.success("✅ Conversación guardada!")
                else:
                    st.warning("No hay nada que guardar")

        # Panel de administrador
        if is_admin:
            st.markdown("---")
            st.markdown("### 📊 Panel de Administrador")
            logs_para_mostrar = st.session_state.all_sessions_log
            if logs_para_mostrar:
                st.markdown(f"""
                <div class="gist-info">
                📈 <strong>Estadísticas actuales:</strong><br>
                • Total de sesiones: {len(logs_para_mostrar)}
                </div>
                """, unsafe_allow_html=True)
                if st.secrets.get("GITHUB_TOKEN"):
                    gist_manager = GistManager(
                        st.secrets.get("GITHUB_TOKEN"),
                        st.secrets.get("GIST_ID") or st.session_state.get('gist_id')
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Subir Logs"):
                            with st.spinner("Subiendo logs..."):
                                success, result = gist_manager.subir_logs(logs_para_mostrar)
                                if success:
                                    st.success(f"✅ Logs subidos exitosamente!")
                                    st.markdown(f"🔗 [Ver en GitHub]({result})")
                                else:
                                    st.error(f"❌ Error: {result}")
                    with col2:
                        if st.button("Descargar"):
                            st.download_button(
                                label="Descargar JSON",
                                data=json.dumps(logs_para_mostrar, ensure_ascii=False, indent=2),
                                file_name=f"mindly_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json"
                            )
                            st.success("✅ Descarga lista!")
                else:
                    st.info("🔑 Configura tu GitHub Token para usar Gist.")
            else:
                st.info("No hay logs de usuario para mostrar.")

    # Mostrar mensaje inicial
    if len(st.session_state.history) == 0:
        with st.chat_message("assistant"):
            st.markdown("""
            ¡Hola! Soy **Mindly**, tu compañero de bienestar mental. 🌟
            
            ¿En qué puedo ayudarte hoy?
            """)
            
            for i in range(0, len(st.session_state.history), 2):
    st.chat_message("user").markdown(st.session_state.history[i]["content"])
    
    if i + 1 < len(st.session_state.history):
        assistant_message = st.session_state.history[i + 1]["content"]
        
        with st.container():
            st.chat_message("assistant").markdown(assistant_message)
            
            col1, col2 = st.columns([0.8, 0.2])  # Ajusta el ancho de las columnas
            
            with col2:
                safe_message = html.escape(assistant_message)
                st.markdown(f"""
                    <script>
                    function copiarTexto() {{
                        navigator.clipboard.writeText(`{safe_message}`);
                        alert("✅ Texto copiado al portapapeles");
                    }}
                    </script>
                    <button onclick="copiarTexto()"
                            style="background-color:#6B73FF;color:white;border:none;padding:6px 12px;
                                   font-size:14px;border-radius:6px;cursor:pointer;">
                        📋 Copiar
                    </button>
                """, unsafe_allow_html=True)
                
    # Input del usuario
if prompt := st.chat_input("💭 Comparte lo que está en tu mente..."):
    if not prompt or not prompt.strip():
        st.warning("Por favor, ingresa un mensaje válido para continuar.")
        st.stop()

    prompt_to_api = prompt
    if len(prompt_to_api) > MAX_PROMPT_LENGTH:
        prompt_to_api = prompt_to_api[:MAX_PROMPT_LENGTH]
        st.warning(f"Tu mensaje ha sido acortado a {MAX_PROMPT_LENGTH} caracteres para optimizar la conversación.")

    st.chat_message("user").markdown(prompt)
    st.session_state.history.append({"role": "user", "content": prompt})

    # Lógica de caché condicional
    if len(prompt_to_api.strip()) < 100:
        with st.spinner("¡Mindly responde desde la memoria! 🚀"):
            respuesta_final = get_cached_response(prompt_to_api, st.session_state.current_profile)
    else:
        with st.spinner("🧠 Mindly está reflexionando..."):
            respuesta_final = chat(prompt_to_api, st.session_state.history, st.session_state.current_profile)

    st.chat_message("assistant").markdown(respuesta_final)
    st.session_state.history.append({"role": "assistant", "content": respuesta_final})

    session_id = st.session_state.get('current_session_id', generar_session_id())
    guardar_sesion_usuario(session_id, st.session_state.history)

if __name__ == "__main__":
    main()
