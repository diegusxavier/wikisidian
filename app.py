import streamlit as st
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import uuid

# Importações originais do seu projeto
from src.config import carregar_configuracoes, salvar_configuracoes
from src.utils.file_handler import get_all_md_files, read_file_content
from src.core.embedder import VectorStore
from src.core.linker import ObsidianLinker
from src.utils.undo_links import remove_ia_links
from src.utils.history_handler import salvar_conversa, carregar_conversa, listar_conversas, excluir_conversa
# Importa o motor do Obsidian a partir do novo arquivo
from src.core.md_rag_cli import WikisidianChat
# Importa o motor de Livros a partir do arquivo PDF
from src.core.pdf_rag_cli import HybridRagEngine

st.set_page_config(page_title="Wikisidian", page_icon="🧠", layout="wide")

# ==========================================
# 0. INICIALIZAÇÃO DE VARIÁVEIS DE ESTADO (GLOBAL)
# ==========================================
# Estado para a Guia 1 (Chat Obsidian Original)
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
if "nota_visualizada" not in st.session_state:
    st.session_state.nota_visualizada = None
    st.session_state.caminho_nota = None
if "conv_id" not in st.session_state:
    st.session_state.conv_id = None
if "conversa_temporaria" not in st.session_state:
    st.session_state.conversa_temporaria = False

# NOVO: Estado isolado para a Guia 2 (Chat de Livros PDF)
if "book_messages" not in st.session_state:
    st.session_state.book_messages = []

# ==========================================
# 0.1 CARREGAMENTO DINÂMICO (Anti-Cache)
# ==========================================
CONFIG_ATUAL = carregar_configuracoes()
caminho_json = CONFIG_ATUAL.get("vault_path", "").strip()

if not caminho_json:
    caminho_json = os.environ.get("PERSONAL_VAULT_PATH", "")

VAULT_PATH_DINAMICO = Path(caminho_json) if caminho_json else None

# ==========================================
# 1. FUNÇÕES AUXILIARES DA UI
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

    # --- BLOCO 2: HISTÓRICO DE CONVERSAS (OBSIDIAN) ---
    todas_conversas = listar_conversas()
    with st.expander("🕟 Histórico de Conversas (Obsidian)", expanded=False):
        if not todas_conversas:
            st.info("Nenhuma conversa salva.")
        else:
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
    st.write("**🚫 Pastas Ignoradas:**")
    lista_atual = CONFIG_ATUAL.get("ignored_folders", [".obsidian", "99 - TEMP"])
    
    if VAULT_PATH_DINAMICO and VAULT_PATH_DINAMICO.exists():
        novas_ignoradas = []
        pastas_raiz = [p for p in VAULT_PATH_DINAMICO.iterdir() if p.is_dir() and not p.name.startswith(".")]
        
        with st.container(height=450):
            for pasta_raiz in sorted(pastas_raiz, key=lambda x: x.name.lower()):
                nome_raiz = pasta_raiz.name
                mae_marcada = nome_raiz in lista_atual
                
                if st.checkbox(f"📁 **{nome_raiz}**", value=mae_marcada, key=f"chk_raiz_{nome_raiz}"):
                    novas_ignoradas.append(nome_raiz)
                    mae_marcada = True 
                
                subpastas = [p for p in pasta_raiz.rglob("*") if p.is_dir()]
                if subpastas:
                    with st.expander(f"↳ Subpastas de {nome_raiz}"):
                        for sub in sorted(subpastas, key=lambda x: str(x)):
                            caminho_relativo = str(sub.relative_to(VAULT_PATH_DINAMICO)).replace("\\", "/")
                            filha_marcada = mae_marcada or (caminho_relativo in lista_atual)
                            
                            cb_filha = st.checkbox(
                                f"📂 {sub.name}", value=filha_marcada, disabled=mae_marcada, key=f"chk_sub_{caminho_relativo}"
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

@st.cache_resource
def iniciar_sistema(caminho_str, pastas_ignoradas_tupla):
    caminho_cofre = Path(caminho_str)
    arquivos_md = get_all_md_files(caminho_cofre, pastas_ignoradas_tupla)
    
    vetor_db = VectorStore(collection_name="obsidian_notes") # MODIFICADO: Explicitei a coleção
    vetor_db.sync_db(arquivos_md)
    
    if arquivos_md:
        conteudos = [read_file_content(f) for f in arquivos_md]
        vetor_db.add_notes(arquivos_md, conteudos) 
    
    return WikisidianChat(vetor_db, caminho_cofre)

lista_fresca = tuple(CONFIG_ATUAL.get("ignored_folders", []))
chat_engine_obsidian = iniciar_sistema(str(VAULT_PATH_DINAMICO), lista_fresca)


# ==========================================
# 4. CRIAÇÃO DAS 3 ABAS (TABS)
# ==========================================
# MODIFICADO: Adicionado a aba "Chat Livros (PDF)" como segunda aba
aba_chat_obsidian, aba_chat_livros, aba_linker = st.tabs(["💬 Chat Obsidian", "📚 Chat Livros (PDF)", "🔗 Gestor de Conexões"])

# ------------------------------------------
# ABA 1: CHAT RAG OBSIDIAN (Mantido original)
# ------------------------------------------
with aba_chat_obsidian:
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

    col_limpar, col_temp, col_hibrido = st.columns([2, 3, 3])
    
    with col_limpar:
        st.write("")
        if st.button("✨ Nova Conversa", use_container_width=True, key="btn_novo_obs"):
            st.session_state.mensagens = []
            st.session_state.nota_visualizada = None
            st.session_state.caminho_nota = None
            st.session_state.conv_id = None 
            st.rerun()

    with col_temp:
        st.write("")
        conversa_temp = st.toggle("👻 Modo Temporário", value=False, help="Não salva no histórico.", key="tg_temp_obs")
        st.session_state.conversa_temporaria = conversa_temp 

    with col_hibrido:
        st.write("") 
        modo_criativo = st.toggle("🌐 Conhecimento Externo", value=False, key="tg_ext_obs")
    
    st.divider()

    col_chat, col_nota = st.columns([6, 4], gap="large")

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

        if pergunta := st.chat_input("Pergunte algo sobre as suas anotações..."):
            with st.chat_message("user"):
                st.markdown(pergunta)
            
            st.session_state.mensagens.append({"role": "user", "content": pergunta})
            
            with st.chat_message("assistant"):
                resposta_ia = st.write_stream(
                    chat_engine_obsidian.perguntar(
                        pergunta, 
                        modo_estrito=not modo_criativo,
                        historico=st.session_state.mensagens[:-1] 
                    )
                )
                    
            st.session_state.mensagens.append({
                "role": "assistant", 
                "content": resposta_ia,
                "fontes": list(chat_engine_obsidian.notas_contexto) 
            })
            
            if not st.session_state.conversa_temporaria:
                if not st.session_state.conv_id:
                    st.session_state.conv_id = str(uuid.uuid4())[:8]
                titulo_conversa = st.session_state.mensagens[0]["content"][:40] + "..."
                salvar_conversa(st.session_state.conv_id, st.session_state.mensagens, titulo_conversa)
                
            st.rerun()

    with col_nota:
        st.header("📄 Visualizador de Notas")
        st.divider()
        if st.session_state.nota_visualizada:
            st.subheader(st.session_state.nota_visualizada)
            conteudo_nota = read_file_content(Path(st.session_state.caminho_nota))
            with st.container(height=550):
                st.markdown(conteudo_nota)
        else:
            st.info("👈 Faça uma pergunta e clique numa das notas utilizadas no chat para ler o seu conteúdo original aqui.")


# ------------------------------------------
# ABA 2: CHAT LIVROS PDF (O SEU NOVO NOTEBOOKLM)
# ------------------------------------------
with aba_chat_livros:
    st.header("📚 Pesquisa Acadêmica em Livros")
    
    # --- PAINEL DE CONTROLE (Botões e Toggles) ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.write("") # Alinhamento
        if st.button("✨ Nova Pesquisa", key="btn_novo_livro", use_container_width=True):
            st.session_state.book_messages = []
            st.rerun() 
            
    with col2:
        st.write("")
        # NOVO: Toggle para usar apenas as notas como consulta rápida sem salvar no histórico
        conversa_temp_livro = st.toggle("Modo Temporário", value=True, key="tg_tmp_livro", help="Não memoriza mensagens para otimizar tokens.")
        
    with col3:
        st.write("")
        # NOVO: Controle estrito de resposta da LLM (usando seu HybridRAG)
        modo_estrito_livro = st.toggle("Modo Acadêmico Estrito", value=True, key="tg_estrito_livro", 
                                 help="Se ativado, a IA obrigatoriamente fará a citação baseada apenas nos PDFs extraídos.")
    with col4:
        st.write("")
        # NOVO: O botão mágico que cruza Livros com o seu Obsidian
        incluir_obsidian = st.toggle("🔗 Cruzar com Obsidian", value=False, key="tg_obs_livro",
                                     help="Busca a resposta simultaneamente nos Livros e no seu Cofre Obsidian.")

    st.divider()

    # --- RENDERIZAÇÃO DO HISTÓRICO ---
    for msg in st.session_state.book_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- INPUT DO USUÁRIO ---
    if prompt_livro := st.chat_input("Faça uma pergunta sobre a biblioteca de PDFs...", key="input_livro"):
        
        with st.chat_message("user"):
            st.markdown(prompt_livro)
        
        # Apenas salva a pergunta se não for modo temporário
        if not conversa_temp_livro:
            st.session_state.book_messages.append({"role": "user", "content": prompt_livro})

        # --- RESPOSTA DA IA ---
        with st.chat_message("assistant"):
            # NOVO: Instanciamos o motor híbrido que você configurou no rag_cli.py
            engine_livros = HybridRagEngine()
            
            # Pega as últimas 4 mensagens de contexto
            historico_para_ia = st.session_state.book_messages[-5:-1] if len(st.session_state.book_messages) > 1 else None

            # Renderiza o stream da IA
            resposta_completa = st.write_stream(
                engine_livros.query(
                    pergunta_usuario=prompt_livro,
                    modo_estrito=modo_estrito_livro,
                    incluir_obsidian=incluir_obsidian,
                    historico=historico_para_ia
                )
            )

        # Salva a resposta no state se não for modo temporário
        if not conversa_temp_livro and resposta_completa:
            st.session_state.book_messages.append({"role": "assistant", "content": resposta_completa})


# ------------------------------------------
# ABA 3: O LINKER (Gestor de Conexões Original)
# ------------------------------------------
with aba_linker:
    st.header("Gerador Automático de Backlinks")
    st.write("A IA varre o seu cofre e injeta notas relacionadas no final dos arquivos. Você também pode desfazer este processo a qualquer momento.")
    
    top_k_links = st.slider("Quantos links deseja injetar por nota?", min_value=1, max_value=5, value=3)
    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        btn_injetar = st.button("🚀 Iniciar Injeção de Links", use_container_width=True)
    with col2:
        btn_remover = st.button("🧹 Desfazer Todos os Links", use_container_width=True)
        
    if btn_injetar:
        arquivos_para_processar = get_all_md_files(VAULT_PATH_DINAMICO, lista_fresca)
        total_arquivos = len(arquivos_para_processar)
        
        if total_arquivos == 0:
            st.warning("Nenhum ficheiro encontrado para processar.")
        else:
            linker = ObsidianLinker(chat_engine_obsidian.vs)
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

    if btn_remover:
        with st.spinner("A varrer o cofre e a remover as assinaturas da IA..."):
            total_limpo = remove_ia_links(VAULT_PATH_DINAMICO, lista_fresca)
            if total_limpo > 0:
                st.success(f"Ufa! {total_limpo} ficheiros foram restaurados ao seu estado original com sucesso.")
            else:
                st.info("Nenhuma nota com links gerados pela IA foi encontrada nas suas pastas.")