import streamlit as st
import google.generativeai as genai
import datetime
import requests
import io
from PIL import Image

# --- 1. CONFIGURAÇÕES ---
# Substitua pela sua chave do Google AI Studio
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

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
    prompt_enc = requests.utils.quote(prompt)
    seed = datetime.datetime.now().microsecond
    
    # Lista de motores: 1. IA (Pollinations) | 2. Fotos Reais (Unsplash/LoremFlickr)
    urls = [
        f"https://image.pollinations.ai/prompt/{prompt_enc}?width=1024&height=1024&seed={seed}&nologo=true&model=flux",
        f"https://loremflickr.com/1024/1024/{prompt_enc.split('%20')[-1]}" # Busca por palavra-chave se IA falhar
    ]
    
    for url in urls:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
                return r.content
        except:
            continue
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
st.image("sophos.png", width=70) # Ajuste a largura conforme necessário

# Exibe histórico do chat selecionado
for msg in st.session_state.historico_chats[st.session_state.chat_ativo]:
    # Define o ícone: se for assistente usa a logo, se for usuário usa outro ou deixa padrão
    icone = "logo_sophos.png" if msg["role"] == "assistant" else "user_icon.png"
    
    with st.chat_message(msg["role"], avatar=icone):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        else:
            st.image(msg["content"])

# Entrada do usuário
if prompt := st.chat_input("Como posso te ajudar?"):
    # Salva e exibe pergunta
    st.session_state.historico_chats[st.session_state.chat_ativo].append({"role": "user", "content": prompt, "type": "text"})
    with st.chat_message("user", avatar="user_icon.png"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="logo_sophos.png"):
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
