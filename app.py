import streamlit as st
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from src.config import carregar_configuracoes, salvar_configuracoes
from src.utils.file_handler import get_all_md_files, read_file_content
from src.core.embedder import VectorStore
from src.core.rag_cli import WikisidianChat

st.set_page_config(page_title="Wikisidian", page_icon="🧠", layout="wide")

# ==========================================
# 0. CARREGAMENTO DINÂMICO (Anti-Cache)
# ==========================================
# Lemos o JSON em tempo real toda vez que a tela atualiza
CONFIG_ATUAL = carregar_configuracoes()
caminho_json = CONFIG_ATUAL.get("vault_path", "").strip()

if not caminho_json:
    caminho_json = os.environ.get("PERSONAL_VAULT_PATH", "")

# Esta variável agora é sempre fresca e atualizada
VAULT_PATH_DINAMICO = Path(caminho_json) if caminho_json else None

# ==========================================
# 1. FUNÇÃO PARA ABRIR O EXPLORADOR DE ARQUIVOS
# ==========================================
def selecionar_pasta_graficamente(caminho_atual):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    pasta_selecionada = filedialog.askdirectory(initialdir=caminho_atual, title="Selecione a pasta raiz do seu cofre Obsidian")
    root.destroy()
    return pasta_selecionada

# ==========================================
# 2. MENU LATERAL (CONFIGURAÇÕES)
# ==========================================
with st.sidebar:
    st.header("⚙️ Configurações")
    
    st.write("**Caminho do Cofre Obsidian:**")
    caminho_exibicao = str(VAULT_PATH_DINAMICO) if VAULT_PATH_DINAMICO else "Nenhum cofre selecionado"
    st.info(caminho_exibicao)
    
    if st.button("📁 Selecionar Pasta pelo Explorador"):
        caminho_inicial = str(VAULT_PATH_DINAMICO) if VAULT_PATH_DINAMICO else "/"
        pasta_escolhida = selecionar_pasta_graficamente(caminho_inicial)
        
        if pasta_escolhida:
            CONFIG_ATUAL["vault_path"] = pasta_escolhida
            salvar_configuracoes(CONFIG_ATUAL)
            
            st.success("Caminho atualizado com sucesso!")
            st.cache_resource.clear()  
            st.rerun()  

# ==========================================
# 3. ÁREA PRINCIPAL E INICIALIZAÇÃO
# ==========================================
st.title("Wikisidian - Gestor de Conhecimento")

if not VAULT_PATH_DINAMICO or not VAULT_PATH_DINAMICO.exists():
    st.warning("👈 Por favor, selecione a pasta válida do seu cofre do Obsidian no menu lateral para iniciar.")
    st.stop()

# A MÁGICA ACONTECE AQUI:
# Ao receber o 'caminho_str' como argumento, o Streamlit sabe que se o caminho mudar,
# ele é obrigado a deletar o cache velho e rodar tudo de novo na nova pasta!
@st.cache_resource
def iniciar_sistema(caminho_str):
    caminho_cofre = Path(caminho_str)
    
    arquivos_md = get_all_md_files(caminho_cofre)
    vetor_db = VectorStore()
    vetor_db.sync_db(arquivos_md)
    
    conteudos = [read_file_content(f) for f in arquivos_md]
    vetor_db.add_notes(arquivos_md, conteudos) 
    
    return WikisidianChat(vetor_db, caminho_cofre)

# Passamos o caminho como string para o motor
chat_engine = iniciar_sistema(str(VAULT_PATH_DINAMICO))

# ==========================================
# 4. MEMÓRIA DA SESSÃO (HISTÓRICO)
# ==========================================
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 5. A CAIXA DE TEXTO E LÓGICA DE RESPOSTA
# ==========================================
pergunta = st.chat_input("Pergunte algo sobre suas anotações...")

if pergunta:
    with st.chat_message("user"):
        st.markdown(pergunta)
    st.session_state.mensagens.append({"role": "user", "content": pergunta})
    
    with st.chat_message("assistant"):
        with st.spinner("Consultando o banco de dados..."):
            resposta_ia = chat_engine.perguntar(pergunta)
            st.markdown(resposta_ia)
            
    st.session_state.mensagens.append({"role": "assistant", "content": resposta_ia})