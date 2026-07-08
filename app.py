import streamlit as st
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from src.config import carregar_configuracoes, salvar_configuracoes
from src.utils.file_handler import get_all_md_files, read_file_content
from src.core.embedder import VectorStore
from src.core.rag_cli import WikisidianChat
from src.core.linker import ObsidianLinker
from src.utils.undo_links import remove_ia_links
import uuid
from src.utils.history_handler import salvar_conversa, carregar_conversa, listar_conversas, excluir_conversa


st.set_page_config(page_title="Wikisidian", page_icon="🧠", layout="wide")

# ==========================================
# 0. INICIALIZAÇÃO DE VARIÁVEIS DE ESTADO (GLOBAL)
# ==========================================
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
if "nota_visualizada" not in st.session_state:
    st.session_state.nota_visualizada = None
    st.session_state.caminho_nota = None
if "conv_id" not in st.session_state:
    st.session_state.conv_id = None # ID único da conversa atual (JSON)
if "conversa_temporaria" not in st.session_state:
    st.session_state.conversa_temporaria = False

# ==========================================
# 0.1 CARREGAMENTO DINÂMICO (Anti-Cache)
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

    # --- BLOCO 2: HISTÓRICO DE CONVERSAS ---
    todas_conversas = listar_conversas()
    
    with st.expander("🕟 Histórico de Conversas", expanded=False):
        if not todas_conversas:
            st.info("Nenhuma conversa salva.")
        else:
            # Selecionador de conversa
            opcoes = {c["id"]: c["titulo"] for c in todas_conversas}
            escolha_id = st.selectbox("Selecione para continuar:", options=list(opcoes.keys()), format_func=lambda x: opcoes[x])
            
            col_carregar, col_excluir = st.columns(2)
            if col_carregar.button("📂 Carregar"):
                st.session_state.mensagens = carregar_conversa(escolha_id)
                st.session_state.conv_id = escolha_id
                st.session_state.nota_visualizada = None
                st.rerun()
                
            if col_excluir.button("🗑️ Excluir"):
                excluir_conversa(escolha_id)
                if st.session_state.conv_id == escolha_id:
                    st.session_state.mensagens = []
                    st.session_state.conv_id = None
                st.success("Apagado!")
                st.rerun()

    st.divider()

    # --- BLOCO 3: PASTAS IGNORADAS ---
    # st.expander cria um "Toggle" expansível. Tudo dentro do 'with' fica oculto até clicar.
    st.write("**🚫 Pastas Ignoradas:**")
    
    lista_atual = CONFIG_ATUAL.get("ignored_folders", [".obsidian", "99 - TEMP"])
    
    if VAULT_PATH_DINAMICO and VAULT_PATH_DINAMICO.exists():
        st.write("Marque as pastas para a IA ignorar:")
        novas_ignoradas = []
        
        pastas_raiz = [p for p in VAULT_PATH_DINAMICO.iterdir() if p.is_dir() and not p.name.startswith(".")]
        
        # O container com altura fixa substitui a necessidade do expander global!
        with st.container(height=450):
            for pasta_raiz in sorted(pastas_raiz, key=lambda x: x.name.lower()):
                nome_raiz = pasta_raiz.name
                
                # Checkbox da pasta MÃE
                mae_marcada = nome_raiz in lista_atual
                if st.checkbox(f"📁 **{nome_raiz}**", value=mae_marcada, key=f"chk_raiz_{nome_raiz}"):
                    novas_ignoradas.append(nome_raiz)
                    mae_marcada = True 
                
                subpastas = [p for p in pasta_raiz.rglob("*") if p.is_dir()]
                
                # Expander apenas para embutir as FILHAS
                if subpastas:
                    with st.expander(f"↳ Subpastas de {nome_raiz}"):
                        for sub in sorted(subpastas, key=lambda x: str(x)):
                            caminho_relativo = str(sub.relative_to(VAULT_PATH_DINAMICO)).replace("\\", "/")
                            filha_marcada = mae_marcada or (caminho_relativo in lista_atual)
                            
                            cb_filha = st.checkbox(
                                f"📂 {sub.name}", 
                                value=filha_marcada, 
                                disabled=mae_marcada, 
                                key=f"chk_sub_{caminho_relativo}"
                            )
                            
                            if cb_filha and not mae_marcada:
                                novas_ignoradas.append(caminho_relativo)
                                
        if st.button("💾 Salvar Filtros", use_container_width=True):
            CONFIG_ATUAL["ignored_folders"] = novas_ignoradas
            salvar_configuracoes(CONFIG_ATUAL)
            
            st.success("Filtros atualizados!")
            st.cache_resource.clear() 
            st.rerun()                
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
# 4. CRIAÇÃO DAS ABAS (TABS)
# ==========================================
aba_chat, aba_linker = st.tabs(["💬 Chat RAG", "🔗 Gestor de Conexões"])

# ------------------------------------------
# ABA 1: O CHAT (SPLIT SCREEN)
# ------------------------------------------
with aba_chat:
    
    # === MAGIA DO CSS: COLUNA FIXA ===
    st.markdown("""
        <style>
            div[data-testid="stColumn"]:nth-of-type(2),
            div[data-testid="column"]:nth-of-type(2) {
                position: -webkit-sticky !important; 
                position: sticky !important;
                top: 70px !important; 
                align-self: flex-start !important; 
                z-index: 999 !important; 
            }
        </style>
    """, unsafe_allow_html=True)
    # =================================

    # --- NOVO: CABEÇALHO DO CHAT E MODO HÍBRIDO ---
    col_limpar, col_temp, col_hibrido = st.columns([2, 3, 3])
    
    with col_limpar:
        st.write("")
        if st.button("✨ Nova Conversa", use_container_width=True):
            st.session_state.mensagens = []
            st.session_state.nota_visualizada = None
            st.session_state.caminho_nota = None
            st.session_state.conv_id = None # Reseta o ID para criar um novo JSON
            st.rerun()

    with col_temp:
        st.write("")
        conversa_temp = st.toggle("👻 Modo Temporário", value=False, help="Não salva esta conversa nos históricos futuros.")
        # Guardaremos este valor para o Passo 2 (salvamento JSON)
        st.session_state.conversa_temporaria = conversa_temp 

    with col_hibrido:
        st.write("") 
        modo_criativo = st.toggle("🌐 Conhecimento Externo", value=False, help="Ative para permitir que a IA cruze os seus dados com conhecimentos externos.")
    
    st.divider()


    # 2. Criamos o Split Screen: 60% para o Chat, 40% para a Nota
    col_chat, col_nota = st.columns([6, 4], gap="large")

    # --- LADO ESQUERDO: CHAT ---
    with col_chat:
        for i, msg in enumerate(st.session_state.mensagens):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                if msg["role"] == "assistant" and "fontes" in msg and msg["fontes"]:
                    with st.expander("📚 Ver notas originais"):
                        for fonte in msg["fontes"]:
                            if st.button(f"📄 {fonte['nome']}", key=f"btn_{i}_{fonte['nome']}"):
                                st.session_state.nota_visualizada = fonte['nome']
                                st.session_state.caminho_nota = fonte['caminho']
                                st.rerun() 

        pergunta = st.chat_input("Pergunte algo sobre as suas anotações...")

        if pergunta:
            with st.chat_message("user"):
                st.markdown(pergunta)
            
            # Adicionamos a pergunta ANTES da chamada, para o histórico ficar visualmente atualizado,
            # mas vamos passar para a IA apenas as mensagens *anteriores* a esta.
            st.session_state.mensagens.append({"role": "user", "content": pergunta})
            
            with st.chat_message("assistant"):
                # NOVO: Passamos o histórico recente (excluindo a última pergunta inserida acima)
                resposta_ia = st.write_stream(
                    chat_engine.perguntar(
                        pergunta, 
                        modo_estrito=not modo_criativo,
                        historico=st.session_state.mensagens[:-1] 
                    )
                )
                    
            st.session_state.mensagens.append({
                "role": "assistant", 
                "content": resposta_ia,
                "fontes": list(chat_engine.notas_contexto) 
            })
            
            # SALVAMENTO AUTOMÁTICO
            if not st.session_state.conversa_temporaria:
                # Se não tem ID, gera um novo
                if not st.session_state.conv_id:
                    st.session_state.conv_id = str(uuid.uuid4())[:8]
                
                # O título será as primeiras 40 letras da primeira pergunta do usuário
                titulo_conversa = st.session_state.mensagens[0]["content"][:40] + "..."
                
                # Salva o arquivo JSON no disco
                salvar_conversa(st.session_state.conv_id, st.session_state.mensagens, titulo_conversa)
                
            st.rerun()

    # --- LADO DIREITO: VISUALIZADOR MARKDOWN ---
    with col_nota:
        st.header("📄 Visualizador de Notas")
        st.divider()
        
        if st.session_state.nota_visualizada:
            st.subheader(st.session_state.nota_visualizada)
            
            # Lê o ficheiro em tempo real e de forma segura
            conteudo_nota = read_file_content(Path(st.session_state.caminho_nota))
            
            # Cria uma "caixa" com altura fixa e barra de scroll
            with st.container(height=550):
                # st.markdown renderiza perfeitamente o seu texto, imagens web, tabelas e fórmulas $$
                st.markdown(conteudo_nota)
        else:
            st.info("👈 Faça uma pergunta e clique numa das notas utilizadas no chat para ler o seu conteúdo original aqui.")

# ------------------------------------------
# ABA 2: O LINKER (INJEÇÃO E REMOÇÃO DE BACKLINKS)
# ------------------------------------------
with aba_linker:
    st.header("Gerador Automático de Backlinks")
    st.write("A IA varre o seu cofre e injeta notas relacionadas no final dos arquivos. Você também pode desfazer este processo a qualquer momento.")
    
    top_k_links = st.slider("Quantos links deseja injetar por nota?", min_value=1, max_value=5, value=3)
    
    st.write("") # Dá um pequeno espaçamento visual
    
    # Criamos duas colunas com o mesmo tamanho
    col1, col2 = st.columns(2)
    
    with col1:
        # Botão de ação principal
        btn_injetar = st.button("🚀 Iniciar Injeção de Links", use_container_width=True)
        
    with col2:
        # Botão de reversão
        btn_remover = st.button("🧹 Desfazer Todos os Links", use_container_width=True)
        
    # --- LÓGICA DO BOTÃO INJETAR ---
    if btn_injetar:
        arquivos_para_processar = get_all_md_files(VAULT_PATH_DINAMICO, lista_fresca)
        total_arquivos = len(arquivos_para_processar)
        
        if total_arquivos == 0:
            st.warning("Nenhum ficheiro encontrado para processar.")
        else:
            linker = ObsidianLinker(chat_engine.vs)
            notas_atualizadas = 0
            
            barra_progresso = st.progress(0)
            texto_status = st.empty() 
            
            for i, arquivo in enumerate(arquivos_para_processar):
                texto_status.text(f"Processando ({i+1}/{total_arquivos}): {arquivo.name}")
                
                alterou = linker.inject_links(arquivo, top_k=top_k_links)
                if alterou:
                    notas_atualizadas += 1
                
                barra_progresso.progress((i + 1) / total_arquivos)
            
            texto_status.success(f"Finalizado! {notas_atualizadas} notas receberam novas conexões.")
            st.balloons()

    # --- LÓGICA DO BOTÃO DESFAZER ---
    if btn_remover:
        with st.spinner("A varrer o cofre e a remover as assinaturas da IA..."):
            # Chama a função de limpeza com a lista fresca de pastas ignoradas
            total_limpo = remove_ia_links(VAULT_PATH_DINAMICO, lista_fresca)
            
            if total_limpo > 0:
                st.success(f"Ufa! {total_limpo} ficheiros foram restaurados ao seu estado original com sucesso.")
            else:
                st.info("Nenhuma nota com links gerados pela IA foi encontrada nas suas pastas.")