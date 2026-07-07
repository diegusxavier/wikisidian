import streamlit as st
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from src.config import VAULT_PATH, CONFIG_ATUAL, salvar_configuracoes
from src.utils.file_handler import get_all_md_files, read_file_content
from src.core.embedder import VectorStore
from src.core.rag_cli import WikisidianChat

st.set_page_config(page_title="Wikisidian", page_icon="🧠", layout="wide") # Mudei para 'wide' para dar mais espaço


# ==========================================
# FUNÇÃO PARA ABRIR O EXPLORADOR DE ARQUIVOS
# ==========================================
def selecionar_pasta_graficamente(caminho_atual):
    """Abre uma janela nativa do sistema para selecionar um diretório."""
    root = tk.Tk()
    root.withdraw()  # Oculta a janela principal vazia do tkinter
    root.attributes('-topmost', True)  # Traz a janela do explorador para a frente de tudo
    
    # Abre o seletor de diretórios começando no caminho atual (se existir)
    pasta_selecionada = filedialog.askdirectory(initialdir=caminho_atual, title="Selecione a pasta raiz do seu cofre Obsidian")
    root.destroy()  # Fecha o processo do tkinter de forma limpa
    return pasta_selecionada


# ==========================================
# 1. MENU LATERAL (CONFIGURAÇÕES)
# ==========================================
with st.sidebar:
    st.header("⚙️ Configurações")
    
    st.write("**Caminho do Cofre Obsidian:**")
    caminho_exibicao = str(VAULT_PATH) if VAULT_PATH else "Nenhum cofre selecionado"
    st.info(caminho_exibicao)
    
    # Botão para abrir o explorador de arquivos
    if st.button("📁 Selecionar Pasta pelo Explorador"):
        caminho_inicial = str(VAULT_PATH) if VAULT_PATH else "/"
        pasta_escolhida = selecionar_pasta_graficamente(caminho_inicial)
        
        # Se o usuário escolheu uma pasta (não cancelou a janela)
        if pasta_escolhida:
            CONFIG_ATUAL["vault_path"] = pasta_escolhida
            salvar_configuracoes(CONFIG_ATUAL)
            
            st.success("Caminho atualizado com sucesso!")
            st.cache_resource.clear()  # Limpa o banco vetorial antigo do cache
            st.rerun()  # Recarrega o app com o novo cofre
            
    st.divider()
    st.caption("ℹ️ Após alterar o caminho, o Wikisidian vai escanear a nova pasta e sincronizar o banco vetorial.")

# ==========================================
# 2. ÁREA PRINCIPAL E INICIALIZAÇÃO
# ==========================================
st.title("Wikisidian - Gestor de Conhecimento")

# Se não há caminho configurado, mostra um aviso amigável no centro da tela e para a execução
if not VAULT_PATH or not Path(VAULT_PATH).exists():
    st.warning("Por favor, configure o caminho válido do seu cofre do Obsidian no menu lateral para iniciar.")
    st.stop()

@st.cache_resource
def iniciar_sistema():
    # 1. Busca os arquivos do cofre (respeitando o caminho configurado)
    arquivos_md = get_all_md_files(VAULT_PATH)
    # 2. Inicializa o motor vetorial
    vetor_db = VectorStore()
    # 3. Sincroniza o banco com o que existe atualmente nas pastas
    vetor_db.sync_db(arquivos_md)
    # 4. Lê os conteúdos e alimenta o banco
    conteudos = [read_file_content(f) for f in arquivos_md]
    vetor_db.add_notes(arquivos_md, conteudos)
    # 5. Retorna o motor de chat pronto para uso
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