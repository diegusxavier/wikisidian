import streamlit as st
from pathlib import Path
from src.config import VAULT_PATH
from src.utils.file_handler import get_all_md_files, read_file_content
from src.core.embedder import VectorStore
from src.core.rag_cli import WikisidianChat

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Wikisidian", page_icon="🧠", layout="centered")
st.title("Wikisidian - Gestor de Conhecimento")

# ==========================================
# 2. INICIALIZAÇÃO DO MOTOR (CACHE)
# ==========================================
# O decorador @st.cache_resource é vital! O Streamlit recarrega a página a cada clique.
# O cache garante que o banco de dados e a IA sejam carregados apenas UMA VEZ.
@st.cache_resource
def iniciar_sistema():
    # Por enquanto, usamos o VAULT_PATH estático. Na próxima etapa, faremos isso ser dinâmico.
    if not VAULT_PATH or not VAULT_PATH.exists():
        return None
    
    arquivos_md = get_all_md_files(VAULT_PATH)
    vetor_db = VectorStore()
    vetor_db.sync_db(arquivos_md)
    
    conteudos = [read_file_content(f) for f in arquivos_md]
    vetor_db.add_notes(arquivos_md, conteudos) # Como você já mudou para upsert, isso é super seguro
    
    return WikisidianChat(vetor_db, VAULT_PATH)

chat_engine = iniciar_sistema()

if chat_engine is None:
    st.error("Caminho do cofre não encontrado. Verifique o arquivo .env.")
    st.stop() # Para a execução da página

# ==========================================
# 3. MEMÓRIA DA SESSÃO (HISTÓRICO)
# ==========================================
# O st.session_state guarda os dados enquanto a aba do navegador estiver aberta
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

# Renderiza o histórico de mensagens na tela
for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 4. A CAIXA DE TEXTO E LÓGICA DE RESPOSTA
# ==========================================
pergunta = st.chat_input("Pergunte algo sobre suas anotações...")

if pergunta:
    # Passo A: Mostra a pergunta do usuário na tela e salva no histórico
    with st.chat_message("user"):
        st.markdown(pergunta)
    st.session_state.mensagens.append({"role": "user", "content": pergunta})
    
    # Passo B: Mostra um indicador de carregamento enquanto a IA processa
    with st.chat_message("assistant"):
        with st.spinner("Consultando o banco de dados..."):
            
            # Chama a função exata que você construiu no rag_cli.py
            resposta_ia = chat_engine.perguntar(pergunta)
            
            # O st.markdown renderiza nativamente negrito, listas, títulos (#) e equações ($$)
            st.markdown(resposta_ia)
            
    # Passo C: Salva a resposta da IA no histórico
    st.session_state.mensagens.append({"role": "assistant", "content": resposta_ia})