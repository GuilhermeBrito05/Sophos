import streamlit as st
import google.generativeai as genai
import datetime
import requests
import io
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
from streamlit_google_auth import Authenticate

# --- 1. CONFIGURAÇÃO DA PÁGINA (OBRIGATORIAMENTE O PRIMEIRO COMANDO) ---
st.set_page_config(page_title="Sophos AI", layout="wide", page_icon="🛡️")

# --- 2. INICIALIZAÇÃO DO FIREBASE ---
if not firebase_admin._apps:
    try:
        firebase_creds = dict(st.secrets["firebase_service_account"])
        firebase_creds["private_key"] = firebase_creds["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(firebase_creds)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erro ao configurar Firebase: {e}")
        st.stop()

db = firestore.client()

# --- 3. AUTENTICAÇÃO GOOGLE ---
# Certifique-se de ter 'google_oauth' configurado nos seus secrets/arquivos
auth_google = Authenticate(
    secret_credentials_path='google_oauth', 
    cookie_name='sophos_login_cookie',
    cookie_key=st.secrets.get("COOKIE_KEY", "chave_padrao_123"),
    redirect_uri='https://seu-app.streamlit.app'
)

auth_google.check_authentification()

# Tela de Login se não estiver conectado
if not st.session_state.get('connected'):
    st.title("🛡️ Bem-vindo ao Sophos AI")
    st.info("Para continuar, realize o login com sua conta Google.")
    auth_google.login()
    st.stop()

# Dados do usuário logado
user_info = st.session_state.get('user_info', {})
user_email = user_info.get('email')

# --- 4. CONFIGURAÇÃO DA IA (GEMINI) ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model_gemini = genai.GenerativeModel(model_name="gemini-1.5-flash")
except Exception as e:
    st.error(f"Erro ao configurar API do Gemini: {e}")
    st.stop()

# --- 5. GERENCIAMENTO DE ESTADO DO CHAT ---
if "historico_chats" not in st.session_state:
    st.session_state.historico_chats = {}

if "chat_ativo" not in st.session_state or st.session_state.chat_ativo is None:
    novo_id = f"Conversa {datetime.datetime.now().strftime('%H:%M:%S')}"
    st.session_state.historico_chats[novo_id] = []
    st.session_state.chat_ativo = novo_id

# --- 6. FUNÇÕES AUXILIARES ---

def registrar_mensagem(role, content, msg_type="text"):
    """Salva no estado local e tenta persistir no Firebase."""
    st.session_state.historico_chats[st.session_state.chat_ativo].append(
        {"role": role, "content": content, "type": msg_type}
    )
    
    try:
        doc_ref = db.collection('usuarios').document(user_email).collection('chats').document(st.session_state.chat_ativo)
        # Firebase não suporta salvar bytes brutos (imagens) facilmente em ArrayUnion, 
        # aqui salvamos apenas os metadados ou textos.
        if msg_type == "text":
            doc_ref.set({
                'mensagens': firestore.ArrayUnion([{
                    'role': role,
                    'content': content,
                    'type': msg_type,
                    'timestamp': datetime.datetime.now()
                }])
            }, merge=True)
    except Exception as e:
        print(f"Erro ao salvar no Firebase: {e}")

def buscar_imagem(prompt):
    """Gera imagem via API Pollinations."""
    prompt_enc = requests.utils.quote(prompt)
    seed = datetime.datetime.now().microsecond
    url = f"https://gen.pollinations.ai/image/{prompt_enc}?model=flux&seed={seed}&nologo=true"
    headers = {"Authorization": f"Bearer {st.secrets['POLLINATIONS_API_KEY']}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        st.error(f"Erro na geração de imagem: {e}")
    return None

# --- 7. INTERFACE (SIDEBAR) ---
with st.sidebar:
    st.image(user_info.get('picture', ""), width=50)
    st.write(f"Olá, **{user_info.get('name', 'Usuário')}**")
    if st.button("Sair"):
        auth_google.logout()
        st.rerun()

    st.divider()
    if st.button("➕ Nova Conversa", use_container_width=True, type="primary"):
        novo_id = f"Conversa {datetime.datetime.now().strftime('%H:%M:%S')}"
        st.session_state.historico_chats[novo_id] = []
        st.session_state.chat_ativo = novo_id
        st.rerun()

    st.subheader("Histórico")
    for chat_id in reversed(list(st.session_state.historico_chats.keys())):
        btn_type = "primary" if chat_id == st.session_state.chat_ativo else "secondary"
        if st.button(chat_id, key=f"btn_{chat_id}", use_container_width=True, type=btn_type):
            st.session_state.chat_ativo = chat_id
            st.rerun()

    st.divider()
    arquivo_upload = st.file_uploader("Anexar arquivo", type=["png", "jpg", "jpeg", "pdf", "txt"])

# --- 8. ÁREA PRINCIPAL DO CHAT ---
st.title("🛡️ Sophos Intelligence")

# Mostrar mensagens anteriores do chat ativo
for msg in st.session_state.historico_chats[st.session_state.chat_ativo]:
    with st.chat_message(msg["role"]):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        else:
            st.image(msg["content"])

# Entrada do Usuário
if prompt := st.chat_input("Como posso ajudar hoje?"):
    # 1. Mostrar e registrar pergunta do usuário
    with st.chat_message("user"):
        st.markdown(prompt)
    registrar_mensagem("user", prompt)

    # 2. Resposta do Assistente
    with st.chat_message("assistant"):
        # Lógica para Geração de Imagem
        if any(keyword in prompt.lower() for keyword in ["crie", "gere", "desenhe", "imagem"]):
            with st.spinner("🎨 Desenhando..."):
                # Refinamento de prompt opcional com Gemini
                prompt_refinado = model_gemini.generate_content(f"Create a detailed image prompt in English for: {prompt}").text
                img_data = buscar_imagem(prompt_refinado)
                if img_data:
                    st.image(img_data)
                    registrar_mensagem("assistant", img_data, "image")
                else:
                    st.error("Não consegui gerar a imagem.")
        
        # Lógica de Texto/Arquivo
        else:
            with st.spinner("Thinking..."):
                conteudo_envio = [prompt]
                if arquivo_upload:
                    bytes_data = arquivo_upload.read()
                    if arquivo_upload.type.startswith("image"):
                        img = Image.open(io.BytesIO(bytes_data))
                        conteudo_envio.append(img)
                    else:
                        conteudo_envio.append({"mime_type": arquivo_upload.type, "data": bytes_data})
                
                try:
                    response = model_gemini.generate_content(conteudo_envio)
                    st.markdown(response.text)
                    registrar_mensagem("assistant", response.text)
                except Exception as e:
                    st.error(f"Erro no processamento: {e}")

# --- 9. ESTILO CSS ---
st.markdown("""
    <style>
    .stChatInput:focus-within { border-color: #6A0DAD !important; }
    div.stButton > button:first-child { border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)
