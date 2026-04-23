import streamlit as st
import google.generativeai as genai
import datetime
import requests
import io
import os
from PIL import Image

# --- 1. CONFIGURAÇÕES ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Chave API não encontrada nos Secrets!")

@st.cache_resource
def carregar_modelo():
    return genai.GenerativeModel('gemini-1.5-flash')

model_gemini = carregar_modelo()

# --- 3. GERENCIAMENTO DE ESTADO ---
if "historico_chats" not in st.session_state:
    st.session_state.historico_chats = {} 

if "chat_ativo" not in st.session_state:
    st.session_state.chat_ativo = None

def criar_novo_chat():
    novo_id = f"Conversa {datetime.datetime.now().strftime('%H:%M:%S')}"
    st.session_state.historico_chats[novo_id] = []
    st.session_state.chat_ativo = novo_id

if not st.session_state.chat_ativo:
    criar_novo_chat()

# --- 4. FUNÇÃO DE IMAGEM ---
def buscar_imagem(prompt):
    prompt_enc = requests.utils.quote(prompt)
    seed = datetime.datetime.now().microsecond
    urls = [
        f"https://image.pollinations.ai/prompt/{prompt_enc}?width=1024&height=1024&seed={seed}&nologo=true&model=flux",
        f"https://loremflickr.com/1024/1024/{prompt_enc.split('%20')[-1]}"
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
                return r.content
        except:
            continue
    return None

# --- 5. INTERFACE ---
st.set_page_config(page_title="Sophos", layout="wide", page_icon="logo_sophos.png")

# CSS Otimizado
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #6A0DAD; color: white; border-radius: 10px; border: none; transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover { background-color: #8A2BE2; color: white; }
    .stChatInput:focus-within { border-color: #6A0DAD !important; box-shadow: 0 0 10px rgba(106, 13, 173, 0.5) !important; }
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
        if st.button(chat_id, key=f"btn_{chat_id}", use_container_width=True, type=tipo):
            st.session_state.chat_ativo = chat_id
            st.rerun()

    st.divider()
    if st.button("🗑️ Apagar Tudo", key="clear_all"):
        st.session_state.historico_chats = {}
        st.session_state.chat_ativo = None
        st.rerun()

# --- 6. ÁREA DE MENSAGENS ---
st.image("Projeto_IA/sophos.png", width=70)

chat_placeholder = st.container()

with chat_placeholder:
    for i, msg in enumerate(st.session_state.historico_chats[st.session_state.chat_ativo]):
        icone = "Projeto/IA/logo_sophos.png" if msg["role"] == "assistant" else "Projeto_IA/user_icon.png"
        
        with st.chat_message(msg["role"], avatar=icone):
            if msg["type"] == "text":
                st.markdown(msg["content"])
            else:
                st.image(msg["content"], caption=f"Gerada por Sophos - {i}", use_container_width=True)

# Entrada do usuário
if prompt := st.chat_input("Como posso te ajudar?"):
    st.session_state.historico_chats[st.session_state.chat_ativo].append({"role": "user", "content": prompt, "type": "text"})

    st.rerun()

# Lógica de Resposta (fora do bloco de input para estabilidade)
if st.session_state.historico_chats[st.session_state.chat_ativo] and st.session_state.historico_chats[st.session_state.chat_ativo][-1]["role"] == "user":
    ultima_msg = st.session_state.historico_chats[st.session_state.chat_ativo][-1]["content"]
    
    with st.chat_message("assistant", avatar="Projeto_IA/logo_sophos.png"):
        if any(p in ultima_msg.lower() for p in ["crie", "gere", "desenhe", "foto", "imagem"]):
            with st.spinner("🎨 Sophos desenhando..."):
                img_data = buscar_imagem(ultima_msg)
                if img_data:
                    st.image(img_data, use_container_width=True)
                    st.session_state.historico_chats[st.session_state.chat_ativo].append(
                        {"role": "assistant", "content": img_data, "type": "image"}
                    )
                else:
                    st.error("Servidores de imagem ocupados.")
        else:
            try:
                response = model_gemini.generate_content(ultima_msg)
                st.markdown(response.text)
                st.session_state.historico_chats[st.session_state.chat_ativo].append(
                    {"role": "assistant", "content": response.text, "type": "text"}
                )
            except Exception as e:
                st.error(f"Erro no Sophos: {e}")
    
    st.rerun()
