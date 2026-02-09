import streamlit as st
import google.generativeai as genai
import datetime
import requests
import io
from PIL import Image

# --- 1. CONFIGURAÇÕES ---
# Substitua pela sua chave do Google AI Studio
try:
    if "GOOGLE_API_KEY" in st.secrets and "POLLINATIONS_API_KEY" in st.secrets:
        GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
        POLLINATIONS_API_KEY = st.secrets["POLLINATIONS_API_KEY"]
        genai.configure(api_key=GOOGLE_API_KEY)
    else:
        faltando = []
        if "GOOGLE_API_KEY" not in st.secrets: faltando.append("GOOGLE_API_KEY")
        if "POLLINATIONS_API_KEY" not in st.secrets: faltando.append("POLLINATIONS_API_KEY")
        st.error(f"⚠️ Chaves faltando nos Secrets: {', '.join(faltando)}")
except Exception as e:
    st.error(f"Erro crítico ao carregar segredos 🤫: {e}")

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
    # 1. Limpeza do prompt
    for p in ["crie", "gere", "desenhe", "imagem", "foto", "de um", "uma"]:
        prompt = prompt.lower().replace(p, "")
    
    prompt_final = prompt.strip() or "nature landscape"
    # Codifica espaços como %20
    prompt_enc = requests.utils.quote(prompt_final)
    
    # 2. URL Identêntica à que você viu nos DOCS (gen.pollinations.ai)
    # Adicionamos um seed aleatório para evitar cache de erro
    import random
    seed = random.randint(0, 999999)
    url = f"https://gen.pollinations.ai/image/{prompt_enc}?model=flux&seed={seed}&nologo=true"
    
    # 3. Headers (A Key vai aqui)
    headers = {
        "Authorization": f"Bearer {st.secrets['POLLINATIONS_API_KEY']}"
    }
    
    try:
        # Request simples
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Se retornar imagem, sucesso
            if "image" in response.headers.get("Content-Type", ""):
                return response.content
            else:
                st.error("O servidor respondeu, mas não enviou uma imagem válida.")
        else:
            # Mostra o erro exato para diagnóstico
            st.error(f"Erro na API: {response.status_code} - {response.text}")
            
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        
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














