import streamlit as st
import json
import re
import requests
import os
from datetime import datetime
from mistralai import Mistral

# ==== CONFIGURACIÓN DE ADMINISTRADOR ====
# Admin mode se activa con /?admin=true en la URL
def verificar_admin():
    """Verifica si se accede con parámetro admin=true en la URL"""
    query_params = st.query_params
    return query_params.get("admin") == "true"

ADMIN_MODE = verificar_admin()

# ==== Configuración del chatbot ====
system_message = (
    "Eres Mindly, un chatbot empático, accesible y profesional. "
    "Tu objetivo es ayudar a los usuarios a encontrar información clara y confiable sobre psicología. "
    "Responde de forma cercana, sin usar jerga técnica, y adapta tus respuestas según la intención del usuario. "
    "Si notas que alguien necesita apoyo emocional urgente, sugiérele que busque ayuda profesional inmediata."
)

LOG_FILE = "chat_log.json"
MAX_HISTORY = 8

# Obtener API key de forma segura - buscar en ambos nombres posibles
MISTRAL_API_KEY = st.secrets.get("MISTRAL_API_KEY", 
                 st.secrets.get("mistralapi", 
                 os.getenv("MISTRAL_API_KEY", 
                 os.getenv("mistralapi", ""))))

# Verificar que existe la API key y no está vacía
if not MISTRAL_API_KEY or MISTRAL_API_KEY.strip() == "":
    st.error("❌ No se encontró la API key de Mistral o está vacía")
    st.info("💡 Configura MISTRAL_API_KEY en .streamlit/secrets.toml o como variable de entorno")
    
    # En modo admin, mostrar más detalles para debugging
    if ADMIN_MODE:
        st.warning("🔧 Debug Info (Solo Admin):")
        st.code(f"""
        secrets: {st.secrets.get("MISTRAL_API_KEY", "NO ENCONTRADO")}
        env: {os.getenv("MISTRAL_API_KEY", "NO ENCONTRADO")}
        """)
    st.stop()

# Verificar que la API key tiene un formato válido
if len(MISTRAL_API_KEY.strip()) < 20:  # Las API keys suelen ser largas
    st.error("❌ La API key parece ser demasiado corta o inválida")
    if ADMIN_MODE:
        st.code(f"API Key length: {len(MISTRAL_API_KEY)} characters")
    st.stop()

# Crear cliente de Mistral
try:
    client = Mistral(api_key=MISTRAL_API_KEY.strip())
except Exception as e:
    error_str = str(e)
    if "Illegal header value" in error_str:
        st.error("❌ Error: API key inválida o vacía")
        st.info("🔑 Verifica que tu MISTRAL_API_KEY esté correctamente configurada")
    else:
        st.error(f"❌ Error al conectar con Mistral: {error_str}")
    st.stop() 

# ==== CONFIGURACIÓN DE GIST ====
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GIST_ID = st.secrets.get("GIST_ID", "")

class GistManager:
    def __init__(self, token, gist_id=None):
        self.token = token
        self.gist_id = gist_id
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def crear_gist(self, filename, content, description="Chat logs de Mindly"):
        """Crear un nuevo Gist"""
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
        """Actualizar un Gist existente"""
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
        """Obtener contenido del Gist"""
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
        """Subir logs al Gist"""
        content = json.dumps(logs_data, ensure_ascii=False, indent=2)
        
        if self.gist_id:
            success, result = self.actualizar_gist("chat_log.json", content)
            return success, result
        else:
            success, gist_id, url = self.crear_gist("chat_log.json", content)
            if success:
                st.session_state.gist_id = gist_id
            return success, url if success else gist_id

# ==== Función para verificar acceso de administrador ====
# Removida - no necesaria para uso simple

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

def chat(message, history, system_prompt):
    try:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-MAX_HISTORY*2:])
        messages.append({"role": "user", "content": message})

        response = client.chat.complete(
            model="mistral-large-latest",
            messages=messages
        )

        return response.choices[0].message.content
    
    except Exception as e:
        # Manejo de errores más detallado
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return "❌ Error de autenticación: La API key parece ser incorrecta. Por favor verifica tu clave de Mistral."
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            return "⏳ Límite de solicitudes alcanzado. Por favor espera un momento antes de intentar de nuevo."
        elif "400" in error_msg or "bad request" in error_msg.lower():
            return "⚠️ Error en la solicitud. El mensaje puede ser demasiado largo o contener caracteres no válidos."
        elif "500" in error_msg or "internal server error" in error_msg.lower():
            return "🔧 Error del servidor de Mistral. Por favor intenta de nuevo en unos momentos."
        else:
            return f"❌ Error inesperado: {error_msg}. Por favor verifica tu conexión e intenta de nuevo."

# ==== Interfaz en Streamlit ====
st.set_page_config(
    page_title="Mindly - Chat de Psicología", 
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Aplicar estilos personalizados
load_custom_css()

# Indicador visual de modo administrador (solo cuando admin=true)
if ADMIN_MODE:
    st.markdown("""
    <div style="position: fixed; top: 10px; right: 10px; background: rgba(39, 174, 96, 0.9); 
         color: white; padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem; 
         font-weight: 500; z-index: 1000;">
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
    
    if st.button("🔄 Nueva Conversación"):
        st.session_state.history = []
        st.rerun()
    
    # === GESTIÓN DE LOGS (SOLO MODO ADMIN) ===
    if ADMIN_MODE and GITHUB_TOKEN:  # Solo mostrar si es admin Y hay token
        st.markdown("---")
        st.markdown("### 📊 Panel de Administrador")
        
        # Mostrar estadísticas de logs
        if chat_log:
            st.markdown(f"""
            <div class="gist-info">
            📈 <strong>Estadísticas:</strong><br>
            • Total conversaciones: {len(chat_log)}<br>
            • Última actualización: {chat_log[-1]['timestamp'][:19] if chat_log else 'N/A'}<br>
            • Modo: Admin activo 👑
            </div>
            """, unsafe_allow_html=True)
        
        # Configuración de Gist
        with st.expander("⚙️ Configurar Gist"):
            github_token_input = st.text_input(
                "GitHub Token", 
                value=GITHUB_TOKEN, 
                type="password",
                help="Token de acceso personal de GitHub"
            )
            gist_id_input = st.text_input(
                "Gist ID (opcional)", 
                value=GIST_ID,
                help="ID del Gist existente"
            )
        
        # Botones de acción para Gist
        gist_manager = GistManager(
            github_token_input or GITHUB_TOKEN, 
            gist_id_input or st.session_state.get('gist_id')
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("☁️ Subir Logs"):
                if chat_log:
                    with st.spinner("Subiendo..."):
                        success, result = gist_manager.subir_logs(chat_log)
                        if success:
                            st.success("✅ Logs subidos!")
                            st.markdown(f"🔗 [Ver Gist]({result})")
                        else:
                            st.error(f"❌ Error: {result}")
                else:
                    st.warning("No hay logs.")
        
        with col2:
            if st.button("📥 Descargar"):
                if gist_manager.gist_id:
                    with st.spinner("Descargando..."):
                        success, result = gist_manager.obtener_gist()
                        if success:
                            files = result.get('files', {})
                            if 'chat_log.json' in files:
                                content = files['chat_log.json']['content']
                                st.download_button(
                                    label="💾 Descargar JSON",
                                    data=content,
                                    file_name=f"mindly_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                    mime="application/json"
                                )
                        else:
                            st.error(f"❌ Error: {result}")
                else:
                    st.warning("Necesitas Gist ID.")
    
    elif ADMIN_MODE and not GITHUB_TOKEN:
        st.markdown("---")
        st.markdown("### 📊 Panel de Administrador")
        st.info("🔑 Configura tu GitHub Token en secrets.toml para gestionar logs")
        
        # Mostrar estadísticas básicas sin Gist
        if chat_log:
            st.markdown(f"""
            <div class="gist-info">
            📈 <strong>Estadísticas locales:</strong><br>
            • Total conversaciones: {len(chat_log)}<br>
            • Última actualización: {chat_log[-1]['timestamp'][:19] if chat_log else 'N/A'}<br>
            • Archivo: chat_log.json
            </div>
            """, unsafe_allow_html=True)

# Inicializar variables de sesión
if "history" not in st.session_state:
    st.session_state.history = []

if "gist_id" not in st.session_state:
    st.session_state.gist_id = GIST_ID

if "user_name" not in st.session_state:
    st.session_state.user_name = None

show_chat = False
system_message_personalized = system_message  # Por defecto, usamos el mensaje original

# Si no tenemos el nombre, lo pedimos
if not st.session_state.user_name:
    st.info("👋 ¡Hola! Para empezar, ¿cómo te gustaría que te llame?")
    name_input = st.text_input("Escribe tu nombre o un apodo aquí", key="name_input_key")
    
    # Si el usuario presiona Enter después de escribir el nombre...
    if name_input:
        st.session_state.user_name = name_input.strip()
        st.rerun() # Volvemos a ejecutar para limpiar el input y mostrar el chat
else:
    # Si ya tenemos el nombre, activamos la visualización del chat
    show_chat = True
    
    # Y modificamos el system_message para incluir el nombre
    system_message_personalized = (
        f"{system_message} "
        f"El nombre del usuario es {st.session_state.user_name}. "
        "Dirígete a él por su nombre cuando sea apropiado para crear una conexión más cercana y empática."
    )

# Mensaje de bienvenida si no hay historial
# Solo mostramos el chat si tenemos el nombre del usuario
if show_chat:
    if len(st.session_state.history) == 0:
        with st.chat_message("assistant"):
            # Mensaje de bienvenida personalizado con el nombre
            st.markdown(f"""
            ¡Hola, **{st.session_state.user_name}**! Soy **Mindly**, tu compañero de bienestar mental. 🌟
            
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
            try:
                # <<== MODIFICADO: Pasamos el mensaje de sistema personalizado
                respuesta_final = chat(prompt, st.session_state.history, system_message_personalized)
                st.chat_message("assistant").markdown(respuesta_final)
            except Exception as e:
                st.error(f"❌ Error al procesar tu mensaje: {str(e)}")
                respuesta_final = "Lo siento, hubo un problema al procesar tu mensaje. ¿Podrías intentarlo de nuevo?"
                st.chat_message("assistant").markdown(respuesta_final)
        
        st.session_state.history.append({"role": "assistant", "content": respuesta_final})
        intencion = detectar_intencion(prompt)
        guardar_log(prompt, respuesta_final, intencion)
