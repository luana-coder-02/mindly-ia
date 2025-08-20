import streamlit as st
import json
import re
import requests
import uuid
from datetime import datetime
from mistralai.client import MistralClient

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

all_sessions_log = {}

try:
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        all_sessions_log = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    pass # The variable is already initialized to an empty dictionary, so we can pass.

if 'history' not in st.session_state:
    st.session_state.history = []

if "gist_id" not in st.session_state:
    st.session_state.gist_id = GIST_ID

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = str(uuid.uuid4())[:8]

if 'all_sessions_log' not in st.session_state:
    st.session_state.all_sessions_log = all_sessions_log

if "current_profile" not in st.session_state:
    st.session_state.current_profile = "Adultos"

class GistManager:
    def __init__(self, token, gist_id=None):
        self.token = token
        self.gist_id = gist_id
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
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
        response = requests.post(
            "https://api.github.com/gists",
            headers=self.headers,
            json=data
        )
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
        response = requests.patch(
            f"https://api.github.com/gists/{self.gist_id}",
            headers=self.headers,
            json=data
        )
        if response.status_code == 200:
            return True, response.json()["html_url"]
        else:
            return False, response.json()
    
    def obtener_gist(self):
        if not self.gist_id:
            return False, "No hay Gist ID configurado"
        response = requests.get(
            f"https://api.github.com/gists/{self.gist_id}",
            headers=self.headers
        )
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
    if not ADMIN_MODE:
        return False
    return True

def load_custom_css():
    st.markdown("""
    <style>
    /* ... (tu CSS personalizado) ... */
    </style>
    """, unsafe_allow_html=True)

# ==== Funciones para historial de usuario ====
def generar_session_id():
    """Genera un ID único para la sesión"""
    import uuid
    return str(uuid.uuid4())[:8]

def cargar_sesion_usuario(session_id):
    """Carga una sesión específica del usuario"""
    # Esta función está incompleta en tu código original, la mantengo así
    # pero recuerda que necesitarías una fuente de datos como `st.session_state.all_sessions_log`
    return st.session_state.all_sessions_log.get(session_id, {}).get("history", [])

def guardar_sesion_usuario(session_id, history):
    """Guarda la conversación de la sesión actual en el log general."""
    session_data = {
        "timestamp": datetime.now().isoformat(),
        "history": history
    }
    st.session_state.all_sessions_log[session_id] = session_data
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.all_sessions_log, f, ensure_ascii=False, indent=2)

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
        
@st.cache_data(show_spinner=False)
def chat(message, history):
    system_message = {
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
        
        respuesta_final = re.sub(r'🔹\s?', '\n- ', respuesta_final)
        respuesta_final = re.sub(r'(\n|\s)(Fundador:|En qué se enfoca:|Ejemplo:|Técnicas:)', r'\n\n\2', respuesta_final, flags=re.IGNORECASE)
        respuesta_final = respuesta_final.strip()
        
        return respuesta_final
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API de Mistral: {e}")
        return "Lo siento, tuve un problema técnico y no puedo responder en este momento."
    except KeyError:
        st.error("Error al procesar la respuesta de la API de Mistral.")
        return "Lo siento, la respuesta de la API no es válida."
        
# ==== Interfaz en Streamlit ====
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

with st.sidebar:
    st.markdown("### 👤 Elige tu perfil")
    st.session_state.current_profile = st.selectbox(
        "Elige tu perfil:",
        list(SYSTEM_MESSAGES.keys()),
        index=list(SYSTEM_MESSAGES.keys()).index(st.session_state.current_profile),
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

        if st.button("Cerrar Sesión Admin"):
            st.session_state.admin_authenticated = False
            st.rerun()

if len(st.session_state.history) == 0:
    with st.chat_message("assistant"):
        st.markdown("""
        ¡Hola! Soy **Mindly**, tu compañero de bienestar mental. 🌟
        
        ¿En qué puedo ayudarte hoy?
        """)

for i in range(0, len(st.session_state.history), 2):
    st.chat_message("user", avatar="👤").markdown(st.session_state.history[i]["content"])
    if i+1 < len(st.session_state.history):
        assistant_message = st.session_state.history[i+1]["content"]
        st.chat_message("assistant", avatar="🧠").markdown(assistant_message)
        st.text_input("Copiar al portapapeles:", assistant_message, label_visibility="collapsed")

if prompt := st.chat_input("💭 Comparte lo que está en tu mente..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.history.append({"role": "user", "content": prompt})
    
    with st.spinner("🧠 Mindly está reflexionando..."):
        respuesta_final = chat(prompt, st.session_state.history)
        st.chat_message("assistant").markdown(respuesta_final)
    
    st.session_state.history.append({"role": "assistant", "content": respuesta_final})
    intencion = detectar_intencion(prompt)
    
    session_id = st.session_state.get('current_session_id', generar_session_id())
    guardar_sesion_usuario(session_id, st.session_state.history)
