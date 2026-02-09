import streamlit as st
import google.generativeai as genai
import datetime
import requests
import io
from PIL import Image

# --- 1. CONFIGURAÇÕES ---
# Substitua pela sua chave do Google AI Studio
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    POLLINATIONS_API_KEY = st.secrets["POLLINATIONS_APY_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except KeyError:
    st.error("Erro: A chave GOOGLE_API_KEY não foi configurada nos Secrets do Streamlit.")
    st.error("Erro: A chave POLLINATIONS_API_KEY não foi configurada nos Secrets do Streamlit")

# --- 2. FUNÇÃO DE IA ---
@st.cache_resource
def carregar_modelo():
    try:
        return genai.GenerativeModel(model_name="gemini-2.5-flash")
    except Exception as e:
        st.error(f"Erro ao carregar Gemini: {e}")
        return None

model_gemini = carregar_modelo()

# --- 3. GERENCIAMENTO DE ESTADO (MULTI-CHAT) ---
if "historico_chats" not in st.session_state:
    st.session_state.historico_chats = {} 

if "chat_ativo" not in st.session_state:
    st.session_state.chat_ativo = None

def criar_novo_chat():
    # Nomeia o chat com a hora atual para o histórico
    novo_id = f"Conversa {datetime.datetime.now().strftime('%H:%M:%S')}"
    st.session_state.historico_chats[novo_id] = []
    st.session_state.chat_ativo = novo_id

if not st.session_state.chat_ativo:
    criar_novo_chat()

# --- 4. FUNÇÃO RESILIENTE DE IMAGEM (ANTI-RATE LIMIT) ---
def buscar_imagem(prompt):
    prompt_limpo = prompt.lower().replace("crie", "").replace("gere", "").strip()
    prompt_enc = requests.utils.quote(prompt_limpo)
    
    # URL da API (verifique na documentação deles se o endpoint mudou, 
    # geralmente é algo como /generate ou similar)
    url = f"https://image.pollinations.ai/prompt/{prompt_enc}"
    
    # Cabeçalhos com a sua chave secreta
    headers = {
        "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Parâmetros adicionais que costumam pedir em APIs com Key
    params = {
        "model": "flux",
        "width": 1024,
        "height": 1024,
        "nologo": True
    }

    try:
        # Fazendo a requisição passando os headers com a Key
        r = requests.get(url, headers=headers, params=params, timeout=30)
        
        if r.status_code == 200:
            return r.content
        elif r.status_code == 401:
            st.error("Erro de Autenticação: Verifique sua Pollinations Key.")
        else:
            st.error(f"Erro na API: Status {r.status_code}")
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        
    return None
    
# --- 5. INTERFACE STREAMLIT ---
st.set_page_config(page_title="Sophos", layout="wide", page_icon="logo_sophos.png")

# Estilo CSS para melhorar o visual
st.markdown("""
    <style>
    /* Cor do botão principal */
    div.stButton > button:first-child {
        background-color: #6A0DAD; /* Roxo vibrante */
        color: white;
        border-radius: 10px;
        border: none;
        transition: all 0.3s ease;
    }

    /* Efeito de passar o mouse (Hover) */
    div.stButton > button:first-child:hover {
        background-color: #8A2BE2; /* Roxo mais claro ao passar o mouse */
        color: white;
        border: none;
    }

    /* Cor do botão quando clicado */
    div.stButton > button:first-child:active {
        background-color: #4B0082;
        color: white;
    }
    
    /* Cor da borda do chat_input ao clicar (Foco) */
    .stChatInput:focus-within {
        border-color: #6A0DAD !important;
        box-shadow: 0 0 10px rgba(106, 13, 173, 0.5) !important;
    }

    /* Opcional: Cor do ícone de enviar (setinha) dentro do input */
    .stChatInput button svg {
        fill: #FA8072 !important;
    }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Seus Chats")
    if st.button("➕ Iniciar Nova Conversa", use_container_width=True, type="primary"):
        criar_novo_chat()
        st.rerun()
    
    st.divider()
    st.subheader("Histórico Recente")
    for chat_id in reversed(list(st.session_state.historico_chats.keys())):
        tipo = "primary" if chat_id == st.session_state.chat_ativo else "secondary"
        if st.button(chat_id, key=chat_id, use_container_width=True, type=tipo):
            st.session_state.chat_ativo = chat_id
            st.rerun()

    st.divider()
    if st.button("🗑️ Apagar Tudo"):
        st.session_state.historico_chats = {}
        st.session_state.chat_ativo = None
        st.rerun()

# --- 6. ÁREA DE MENSAGENS ---
st.image("Projeto_IA/sophos.png", width=70) # Ajuste a largura conforme necessário

# Exibe histórico do chat selecionado
for msg in st.session_state.historico_chats[st.session_state.chat_ativo]:
    # Define o ícone: se for assistente usa a logo, se for usuário usa outro ou deixa padrão
    icone = "Projeto_IA/logo_sophos.png" if msg["role"] == "assistant" else "Projeto_IA/user_icon.png"
    
    with st.chat_message(msg["role"], avatar=icone):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        else:
            st.image(msg["content"])

# Entrada do usuário
if prompt := st.chat_input("Como posso te ajudar?"):
    # Salva e exibe pergunta
    st.session_state.historico_chats[st.session_state.chat_ativo].append({"role": "user", "content": prompt, "type": "text"})
    with st.chat_message("user", avatar="Projeto_IA/user_icon.png"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="Projeto_IA/logo_sophos.png"):
        # LÓGICA DE IMAGEM
        if any(p in prompt.lower() for p in ["crie", "gere", "desenhe", "foto", "imagem"]):
            with st.spinner("🎨 Sophos desenhando..."):
                img_data = buscar_imagem(prompt)
                if img_data:
                    st.image(img_data)
                    st.session_state.historico_chats[st.session_state.chat_ativo].append(
                        {"role": "assistant", "content": img_data, "type": "image"}
                    )
                else:
                    st.error("Servidores de imagem ocupados. Tente um prompt mais simples.")
        
        # LÓGICA DE TEXTO
        else:
            try:
                response = model_gemini.generate_content(prompt)
                st.markdown(response.text)
                st.session_state.historico_chats[st.session_state.chat_ativo].append(
                    {"role": "assistant", "content": response.text, "type": "text"}
                )
            except Exception as e:

                st.error(f"Erro no Sophos: {e}")



