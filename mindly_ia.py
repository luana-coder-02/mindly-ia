import streamlit as st
import json
import re
import requests
import uuid
from datetime import datetime
from mistralai.client import MistralClient

ADMIN_MODE = st.query_params.get("admin") == "true"
MAX_HISTORY = 8
LOG_FILE = "chat_log.json"

MISTRAL_API_KEY = st.secrets.get("mistralapi")
if not MISTRAL_API_KEY:
    st.error("Error: La clave 'mistralapi' no está configurada en los secretos de Streamlit.")
    st.stop()

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GIST_ID = st.secrets.get("GIST_ID", "")
GIST_FILENAME = "chat_log.json"

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
    
    # Opción 1: Solo basado en la variable ADMIN_MODE
    return True
    
    # Opción 2: Con contraseña (descomenta para usar)
    # if 'admin_authenticated' not in st.session_state:
    #     st.session_state.admin_authenticated = False
    # 
    # if not st.session_state.admin_authenticated:
    #     with st.sidebar:
    #         st.markdown("### 🔐 Acceso de Administrador")
    #         password = st.text_input("Contraseña:", type="password")
    #         if st.button("Iniciar Sesión"):
    #             if password == ADMIN_PASSWORD:
    #                 st.session_state.admin_authenticated = True
    #                 st.rerun()
    #             else:
    #                 st.error("Contraseña incorrecta")
    #         return False
    # 
    # return True

# ==== PERSONALIZACIÓN DE ESTILOS ====
def load_custom_css():
    st.markdown("""
    <style>
    /* [TODOS LOS ESTILOS CSS ANTERIORES - MANTENGO LOS MISMOS] */
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
    
    .main {
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
    
    .stChatMessage {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 15px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        font-family: 'Inter', sans-serif;
        border-left: 4px solid transparent;
    }
    
    [data-testid="user-message"] {
        background: linear-gradient(135deg, var(--gentle-blue) 0%, #E1F5FE 100%);
        border-left-color: var(--accent-color);
    }
    
    [data-testid="assistant-message"] {
        background: linear-gradient(135deg, var(--gentle-purple) 0%, #F3E5F5 100%);
        border-left-color: var(--secondary-color);
    }
    
    .stChatInputContainer {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 25px;
        padding: 0.5rem;
        margin-top: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        border: 2px solid rgba(107, 115, 255, 0.3);
    }
    
    .stChatInputContainer:focus-within {
        border-color: var(--primary-color);
        box-shadow: 0 4px 20px rgba(107, 115, 255, 0.3);
    }
    
    .stSpinner {
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
    
    .css-1d391kg {
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
    
    @media (max-width: 600px) {
        .block-container {
            padding: 1rem !important;
            margin-top: 1rem !important;
            border-radius: 10px !important;
        }

        .stButton > button {
            font-size: 18px !important;
            padding: 1rem 2rem !important;
        }

        .stChatInputContainer textarea {
            font-size: 18px !important;
            min-height: 50px !important;
        }

        h1 {
            font-size: 2rem !important;
            margin-bottom: 1rem !important;
        }

        .subtitle {
            font-size: 1rem !important;
            margin-bottom: 1.5rem !important;
        }

        .main > div[role="main"] {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        .stChatMessage {
            font-size: 17px !important;
            padding: 0.8rem !important;
            margin: 0.4rem 0 !important;
        }
    }
    
    /* Indicador de modo administrador */
    /* Estilos para historial de conversaciones */
    .conversation-item {
        background: rgba(255, 255, 255, 0.8);
        border-radius: 8px;
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-left: 3px solid var(--accent-color);
        transition: all 0.2s ease;
    }
    
    .conversation-item:hover {
        background: rgba(255, 255, 255, 0.95);
        transform: translateX(2px);
    }
    
    .conversation-meta {
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin-top: 0.2rem;
    }
    
    /* Indicador de modo administrador */
    .admin-indicator {
        position: fixed;
        top: 10px;
        right: 10px;
        background: rgba(39, 174, 96, 0.9);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 500;
        z-index: 1000;
    }
    
    .gist-section {
        background: rgba(39, 174, 96, 0.1);
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid var(--success-color);
        margin: 1rem 0;
    }
    
    .gist-info {
        background: rgba(52, 152, 219, 0.1);
        border-radius: 8px;
        padding: 0.8rem;
        border-left: 3px solid var(--accent-color);
    }
    </style>
    """, unsafe_allow_html=True)

# ==== Cargar historial de logs ====
try:
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        chat_log = json.load(f)
except FileNotFoundError:
    chat_log = []

# ===== INICIALIZACIÓN DE VARIABLES DE SESIÓN (CAMBIO #1) =====
# MOVER AQUÍ - AL PRINCIPIO, DESPUÉS DE CARGAR LOS ARCHIVOS
if 'history' not in st.session_state:
    st.session_state.history = []

if "gist_id" not in st.session_state:
    st.session_state.gist_id = GIST_ID

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = str(uuid.uuid4())[:8]

# CAMBIO #4 - Inicializar all_sessions_log con datos existentes
if 'all_sessions_log' not in st.session_state:
    st.session_state.all_sessions_log = user_sessions.copy()

# ==== Funciones para historial de usuario ====
def generar_session_id():
    """Genera un ID único para la sesión"""
    import uuid
    return str(uuid.uuid4())[:8]

def cargar_sesion_usuario(session_id):
    """Carga una sesión específica del usuario"""
    return user_sessions.get(session_id, {}).get("historia", [])

def eliminar_sesion_usuario(session_id):
    """Elimina una sesión del usuario"""
    if session_id in user_sessions:
        del user_sessions[session_id]
        with open(USER_SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_sessions, f, ensure_ascii=False, indent=2)
        # Sincronizar con session_state
        st.session_state.all_sessions_log = user_sessions.copy()

# ==== Funciones del chatbot ====
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

def guardar_log(usuario_msg, modelo_resp, intencion):
    entrada = {
        "timestamp": datetime.now().isoformat(),
        "usuario": usuario_msg,
        "respuesta": modelo_resp,
        "intencion": intencion
    }
    chat_log.append(entrada)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(chat_log, f, ensure_ascii=False, indent=2)

def chat(message, history):
    system_message = """
        Eres Mindly, un chatbot empático, accesible y profesional.
        Tu objetivo es ayudar a los usuarios a encontrar información clara y confiable sobre psicología.
        Responde de forma cercana, sin usar jerga técnica, y adapta tus respuestas según la intención del usuario.
        Si notas que alguien necesita apoyo emocional urgente, sugiérele que busque ayuda profesional inmediata.
        Utiliza siempre Markdown para dar formato a tus respuestas. Usa listas, negritas y encabezados para que la información sea clara y fácil de leer. Asegúrate de usar saltos de línea para separar las ideas.
    """
    messages = [{"role": "system", "content": system_message.strip()}]
    messages.extend(history[-MAX_HISTORY*2:])
    messages.append({"role": "user", "content": message})
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {st.secrets.get('mistralapi')}"
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

# Aplicar estilos personalizados
load_custom_css()

# Verificar si es administrador
is_admin = verificar_admin()

# Indicador visual de modo administrador (solo lo ves tú)
if is_admin:
    st.markdown("""
    <div class="admin-indicator">
        👑 Modo Administrador
    </div>
    """, unsafe_allow_html=True)

# Header con diseño mejorado
st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1>🧠 Mindly</h1>
        <p class="subtitle">Tu compañero de bienestar mental • Conversaciones empáticas y apoyo psicológico</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar con información adicional
# ----------------- INICIO DEL CÓDIGO DE LA BARRA LATERAL -----------------
with st.sidebar:
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

        # CAMBIO #2 - Usar los datos correctos para logs de admin
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

# ELIMINAR ESTA SECCIÓN - YA NO ES NECESARIA PORQUE SE MOVIÓ AL PRINCIPIO
# Las variables ya están inicializadas arriba

# Mensaje de bienvenida si no hay historial
if len(st.session_state.history) == 0:
    with st.chat_message("assistant"):
        st.markdown("""
        ¡Hola! Soy **Mindly**, tu compañero de bienestar mental. 🌟
        
        Estoy aquí para ayudarte con:
        - Manejo de emociones y estrés
        - Técnicas de relajación y mindfulness  
        - Información sobre psicología
        - Apoyo en momentos difíciles
        
        ¿En qué puedo ayudarte hoy?
        """)

# Mostrar historial
for i in range(0, len(st.session_state.history), 2):
    st.chat_message("user").markdown(st.session_state.history[i]["content"])
    if i+1 < len(st.session_state.history):
        st.chat_message("assistant").markdown(st.session_state.history[i+1]["content"])

# Input del usuario
if prompt := st.chat_input("💭 Comparte lo que está en tu mente..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.history.append({"role": "user", "content": prompt})
    
    with st.spinner("🧠 Mindly está reflexionando..."):
        respuesta_final = chat(prompt, st.session_state.history)
        st.chat_message("assistant").markdown(respuesta_final)
    
    st.session_state.history.append({"role": "assistant", "content": respuesta_final})
    intencion = detectar_intencion(prompt)
    guardar_log(prompt, respuesta_final, intencion)
    
    # Auto-guardar la sesión del usuario cada 3 mensajes
    if len(st.session_state.history) % 6 == 0:  # Cada 3 intercambios (6 mensajes)
        session_id = st.session_state.get('current_session_id', generar_session_id())
        guardar_sesion_usuario(session_id, st.session_state.history)
