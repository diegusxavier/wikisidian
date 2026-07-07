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
    
    # --- BLOCO 1: SELEÇÃO DO COFRE ---
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

    st.divider()

    # --- BLOCO 2: PASTAS IGNORADAS ---
    # st.expander cria um "Toggle" expansível. Tudo dentro do 'with' fica oculto até clicar.
    with st.expander("🚫 Pastas Ignoradas"):
        st.write("Selecione as pastas que a IA **NÃO** deve ler:")
        
        lista_atual = CONFIG_ATUAL.get("ignored_folders", [".obsidian", "99 - TEMP"])
        novas_ignoradas = []
        
        if VAULT_PATH_DINAMICO and VAULT_PATH_DINAMICO.exists():
            # 1. Lê todas as pastas de primeiro nível dentro do cofre
            pastas_no_cofre = [p.name for p in VAULT_PATH_DINAMICO.iterdir() if p.is_dir()]
            
            # 2. Junta as pastas encontradas com as que já estavam salvas (para garantir que pastas ocultas como .obsidian apareçam)
            todas_as_pastas = sorted(list(set(pastas_no_cofre + lista_atual)))
            
            # 3. Cria um Checkbox para cada pasta dinamicamente
            for pasta in todas_as_pastas:
                # O parâmetro 'value' define se a caixinha já começa marcada
                marcado = st.checkbox(f"📁 {pasta}", value=(pasta in lista_atual))
                
                # Se estiver marcado na tela, adicionamos à nossa lista temporária
                if marcado:
                    novas_ignoradas.append(pasta)
            
            # 4. O botão para confirmar e salvar no JSON
            if st.button("💾 Salvar Filtros"):
                CONFIG_ATUAL["ignored_folders"] = novas_ignoradas
                salvar_configuracoes(CONFIG_ATUAL)
                
                st.success("Filtros atualizados!")
                st.cache_resource.clear() # Limpa a IA
                st.rerun()                # Recarrega a página
        else:
            st.info("Selecione um cofre primeiro para ver as pastas.")

# ==========================================
# 3. ÁREA PRINCIPAL E INICIALIZAÇÃO
# ==========================================
st.title("Wikisidian - Gestor de Conhecimento")

if not VAULT_PATH_DINAMICO or not VAULT_PATH_DINAMICO.exists():
    st.warning("👈 Por favor, selecione a pasta válida do seu cofre do Obsidian no menu lateral para iniciar.")
    st.stop()

# Passamos as pastas ignoradas como parâmetro. Convertemos para 'tuple' (tupla) 
# porque o @st.cache_resource exige variáveis imutáveis para funcionar corretamente.
@st.cache_resource
def iniciar_sistema(caminho_str, pastas_ignoradas_tupla):
    caminho_cofre = Path(caminho_str)
    
    # 1. Busca as notas, agora enviando a lista atualizada de pastas ignoradas
    arquivos_md = get_all_md_files(caminho_cofre, pastas_ignoradas_tupla)
    
    vetor_db = VectorStore()
    vetor_db.sync_db(arquivos_md)
    
    # 2. Proteção: Só adiciona se houver ficheiros (evita erros se você ignorar tudo)
    if arquivos_md:
        conteudos = [read_file_content(f) for f in arquivos_md]
        vetor_db.add_notes(arquivos_md, conteudos) 
    else:
        st.info("Nenhuma nota encontrada nas pastas permitidas.")
    
    return WikisidianChat(vetor_db, caminho_cofre)

# Pegamos a lista fresca do JSON, convertemos para tupla e injetamos no motor!
lista_fresca = tuple(CONFIG_ATUAL.get("ignored_folders", []))
chat_engine = iniciar_sistema(str(VAULT_PATH_DINAMICO), lista_fresca)

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