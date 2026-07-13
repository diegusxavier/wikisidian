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
from src.utils.chunker import chunk_and_embed_book
from src.utils.pdf_handler import process_pdf_to_json
from src.utils.chunker import chunk_markdown_file

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
if "conv_id_livros" not in st.session_state:
    st.session_state.conv_id_livros = None
if "chunk_visualizado" not in st.session_state:
    st.session_state.chunk_visualizado = None

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

    # --- BLOCO 2: HISTÓRICOS DE CONVERSAS ---
    todas_conversas = listar_conversas()
    
    # Separamos as conversas (adicionaremos o prefixo 'livro_' na hora de salvar)
    conversas_obsidian = [c for c in todas_conversas if not c["id"].startswith("livro_")]
    conversas_livros = [c for c in todas_conversas if c["id"].startswith("livro_")]

    with st.expander("🕟 Histórico (Obsidian)", expanded=False):
        if not conversas_obsidian:
            st.info("Nenhuma conversa salva.")
        else:
            opcoes_obs = {c["id"]: c["titulo"] for c in conversas_obsidian}
            escolha_id_obs = st.selectbox("Continuar chat:", options=list(opcoes_obs.keys()), format_func=lambda x: opcoes_obs[x], key="hist_obs")
            col1, col2 = st.columns(2)
            if col1.button("📂 Carregar", key="load_obs"):
                st.session_state.mensagens = carregar_conversa(escolha_id_obs)
                st.session_state.conv_id = escolha_id_obs
                st.rerun()
            if col2.button("🗑️ Excluir", key="del_obs"):
                excluir_conversa(escolha_id_obs)
                st.rerun()

    with st.expander("🕟 Histórico (Livros)", expanded=False):
        if not conversas_livros:
            st.info("Nenhuma conversa salva.")
        else:
            opcoes_liv = {c["id"]: c["titulo"] for c in conversas_livros}
            escolha_id_liv = st.selectbox("Continuar pesquisa:", options=list(opcoes_liv.keys()), format_func=lambda x: opcoes_liv[x], key="hist_liv")
            col3, col4 = st.columns(2)
            if col3.button("📂 Carregar", key="load_liv"):
                st.session_state.book_messages = carregar_conversa(escolha_id_liv)
                st.session_state.conv_id_livros = escolha_id_liv
                st.session_state.chunk_visualizado = None
                st.rerun()
            if col4.button("🗑️ Excluir", key="del_liv"):
                excluir_conversa(escolha_id_liv)
                st.rerun()


    # --- BLOCO 3: PASTAS IGNORADAS (AGORA NO EXPANDER) ---
    with st.expander("🚫 Pastas Ignoradas (Obsidian)", expanded=False):
        lista_atual = CONFIG_ATUAL.get("ignored_folders", [".obsidian", "99 - TEMP"])
        
        if VAULT_PATH_DINAMICO and VAULT_PATH_DINAMICO.exists():
            novas_ignoradas = []
            pastas_raiz = [p for p in VAULT_PATH_DINAMICO.iterdir() if p.is_dir() and not p.name.startswith(".")]
            
            with st.container(height=300): # Altura reduzida para economizar mais espaço
                for pasta_raiz in sorted(pastas_raiz, key=lambda x: x.name.lower()):
                    nome_raiz = pasta_raiz.name
                    mae_marcada = nome_raiz in lista_atual
                    
                    if st.checkbox(f"📁 **{nome_raiz}**", value=mae_marcada, key=f"chk_raiz_{nome_raiz}"):
                        novas_ignoradas.append(nome_raiz)
                        mae_marcada = True 
                    
                    subpastas = [p for p in pasta_raiz.rglob("*") if p.is_dir()]
                    if subpastas:
                        for sub in sorted(subpastas, key=lambda x: str(x)):
                            caminho_relativo = str(sub.relative_to(VAULT_PATH_DINAMICO)).replace("\\", "/")
                            filha_marcada = mae_marcada or (caminho_relativo in lista_atual)
                            cb_filha = st.checkbox(f"↳ {sub.name}", value=filha_marcada, disabled=mae_marcada, key=f"chk_sub_{caminho_relativo}")
                            if cb_filha and not mae_marcada:
                                novas_ignoradas.append(caminho_relativo)
                                    
            if st.button("💾 Salvar Filtros", use_container_width=True):
                CONFIG_ATUAL["ignored_folders"] = novas_ignoradas
                salvar_configuracoes(CONFIG_ATUAL)
                st.success("Filtros atualizados!")
                st.cache_resource.clear() 
                st.rerun()                
        else:
            st.info("Selecione um cofre primeiro.")


    # --- BLOCO 4: SELEÇÃO DE LIVROS (NOVO) ---
    if "livros_selecionados" not in st.session_state:
        st.session_state.livros_selecionados = []

    with st.expander("📚 Filtro de Livros", expanded=False):
        st.write("Marque os livros que a IA deve consultar:")
        pasta_json = Path("books_data/extracted_texts")
        
        # Cria a pasta caso não exista
        pasta_json.mkdir(parents=True, exist_ok=True)
        
        # Pega todos os arquivos JSON (Livros já processados)
        livros_processados = [f.stem for f in pasta_json.glob("*.json")]
        
        if not livros_processados:
            st.info("Nenhum livro processado ainda.")
        else:
            selecionados_temp = []
            with st.container(height=200):
                for livro in livros_processados:
                    # Por padrão, deixamos todos marcados. 
                    if st.checkbox(livro, value=True, key=f"chk_livro_{livro}"):
                        selecionados_temp.append(livro)
            
            st.session_state.livros_selecionados = selecionados_temp
            if not selecionados_temp:
                st.warning("⚠️ Nenhum livro marcado. A IA não terá base para responder.")


    # --- BLOCO 5: IMPORTAÇÃO E PROCESSAMENTO DE PDFs (NOVO) ---
    with st.expander("📥 Importar Novos PDFs", expanded=False):
        arquivos_pdf = st.file_uploader("Arraste seus PDFs aqui", type=["pdf"], accept_multiple_files=True)
        
        if arquivos_pdf and st.button("🚀 Processar e Vetorizar", use_container_width=True):
            pasta_raw = Path("books_data/raw_pdfs")
            pasta_raw.mkdir(parents=True, exist_ok=True)
            
            progresso = st.progress(0)
            texto_progresso = st.empty()
            
            for i, arquivo in enumerate(arquivos_pdf):
                caminho_salvar = pasta_raw / arquivo.name
                texto_progresso.text(f"Salvando: {arquivo.name}")
                
                # 1. Salva o PDF no disco local
                with open(caminho_salvar, "wb") as f:
                    f.write(arquivo.getbuffer())
                
                try:
                    # 2. Roda o Extrator (Transforma PDF em JSON)
                    texto_progresso.text(f"Extraindo texto: {arquivo.name}")
                    # AQUI VOCÊ CHAMA A SUA FUNÇÃO DO pdf_handler.py
                    process_pdf_to_json(caminho_salvar)
                    
                    # 3. Roda o Chunker (Transforma JSON em Vetor no Chroma)
                    nome_json = arquivo.name.replace(".pdf", ".json")
                    texto_progresso.text(f"Vetorizando: {nome_json}")
                    chunk_and_embed_book(nome_json)
                    
                except Exception as e:
                    st.error(f"Erro no livro {arquivo.name}: {e}")
                    
                # Atualiza a barrinha de progresso
                progresso.progress((i + 1) / len(arquivos_pdf))
                
            texto_progresso.success("Todos os PDFs foram processados!")
            st.balloons()
# ==========================================
# 3. ÁREA PRINCIPAL E INICIALIZAÇÃO
# ==========================================
st.title("🧠 Wikisidian - Gestor de Conhecimento")

if not VAULT_PATH_DINAMICO or not VAULT_PATH_DINAMICO.exists():
    st.warning("👈 Por favor, selecione a pasta válida do seu cofre do Obsidian no menu lateral para iniciar.")
    st.stop()

@st.cache_resource
def iniciar_sistema(caminho_str, pastas_ignoradas_tupla):
    caminho_cofre = Path(caminho_str)
    arquivos_md = get_all_md_files(caminho_cofre, pastas_ignoradas_tupla)
    
    vetor_db = VectorStore(collection_name="obsidian_notes")
    
    # O sync devolve APENAS o que precisa ser lido!
    arquivos_pendentes = vetor_db.sync_db(arquivos_md) 
    
    if arquivos_pendentes:
        todos_ids = []
        todos_chunks = []
        todos_metadados = []
        
        # Só faz o loop no que é Novo ou Modificado
        for arquivo in arquivos_pendentes:
            conteudo_completo = read_file_content(arquivo)
            mtime_arquivo = arquivo.stat().st_mtime # Coleta a data do Windows
            
            ids_nota, chunks_nota, metadados_nota = chunk_markdown_file(
                texto=conteudo_completo,
                nome_arquivo=arquivo.name,
                caminho_completo=str(arquivo),
                mtime=mtime_arquivo # Passa o carimbo pro chunker
            )
            
            todos_ids.extend(ids_nota)
            todos_chunks.extend(chunks_nota)
            todos_metadados.extend(metadados_nota)
        
        if todos_ids:
            vetor_db.add_chunks(ids=todos_ids, contents=todos_chunks, metadatas=todos_metadados)
    else:
        # Se você rodar o app e não tiver editado nada no Obsidian, ele pula direto pra cá em 0.1 segundo!
        print("Cofre já está 100% sincronizado com o Banco Vetorial. Pulando leitura.")
    
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
    
    # Adicionamos os controles superiores da aba
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.write("")
        if st.button("✨ Nova Pesquisa", key="btn_novo_livro", use_container_width=True):
            st.session_state.book_messages = []
            st.session_state.conv_id_livros = None
            st.session_state.chunk_visualizado = None
            st.rerun() 
    with col2:
        st.write("")
        conversa_temp_livro = st.toggle("Modo Temporário", value=False, key="tg_tmp_livro", help="Não salva no histórico.")
    with col3:
        st.write("")
        modo_estrito_livro = st.toggle("Modo Acadêmico Estrito", value=True, key="tg_estrito_livro")
    with col4:
        st.write("")
        incluir_obsidian = st.toggle("🔗 Cruzar com Obsidian", value=False, key="tg_obs_livro")
    with col5:
        # Novo Slider para o Top K
        top_k_livros = st.slider("Trechos (Top-K)", min_value=5, max_value=9, value=5, step=1, key="slider_top_k_livros")

    st.divider()

    # NOVO: DIVISÃO DA TELA (60% Chat, 40% Visualizador de Chunk)
    col_chat_livros, col_nota_livros = st.columns([6, 4], gap="large")

    # --- LADO ESQUERDO: CHAT DOS LIVROS ---
    with col_chat_livros:
        for i, msg in enumerate(st.session_state.book_messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # Renderiza os botões de fonte se a IA tiver usado algum chunk
                if msg["role"] == "assistant" and "fontes" in msg and msg["fontes"]:
                    with st.expander("📚 Ver trechos utilizados"):
                        for j, fonte in enumerate(msg["fontes"]):
                            # Clicar neste botão muda o chunk que será mostrado na direita
                            if st.button(f"🔖 {fonte['nome']}", key=f"btn_livro_chunk_{i}_{j}"):
                                st.session_state.chunk_visualizado = fonte
                                st.rerun()

        if prompt_livro := st.chat_input("Faça uma pergunta sobre a biblioteca de PDFs...", key="input_livro"):
            with st.chat_message("user"):
                st.markdown(prompt_livro)
            
            st.session_state.book_messages.append({"role": "user", "content": prompt_livro})

            with st.chat_message("assistant"):
                engine_livros = HybridRagEngine()
                historico_para_ia = st.session_state.book_messages[-5:-1] if len(st.session_state.book_messages) > 1 else None

                resposta_completa = st.write_stream(
                    engine_livros.query(
                        pergunta_usuario=prompt_livro,
                        book_titles=st.session_state.livros_selecionados,
                        top_k=top_k_livros,
                        modo_estrito=modo_estrito_livro,
                        incluir_obsidian=incluir_obsidian,
                        historico=historico_para_ia
                    )
                )

            # Salva no histórico local da sessão
            st.session_state.book_messages.append({
                "role": "assistant", 
                "content": resposta_completa,
                "fontes": engine_livros.fontes_utilizadas # Guardamos os chunks recebidos do motor
            })

            # SALVAMENTO EM JSON (Se não for temporário)
            if not conversa_temp_livro:
                if not st.session_state.conv_id_livros:
                    # Usamos o prefixo 'livro_' para não misturar com os IDs do Obsidian
                    st.session_state.conv_id_livros = "livro_" + str(uuid.uuid4())[:8]
                
                titulo_conversa = "[PDF] " + st.session_state.book_messages[0]["content"][:35] + "..."
                salvar_conversa(st.session_state.conv_id_livros, st.session_state.book_messages, titulo_conversa)

            st.rerun()

    # --- LADO DIREITO: VISUALIZADOR DE CHUNKS ---
    with col_nota_livros:
        st.header("📄 Trecho do Livro")
        st.divider()
        
        if st.session_state.chunk_visualizado:
            fonte_atual = st.session_state.chunk_visualizado
            st.subheader(fonte_atual["nome"])
            
            # Caixa estilizada para mostrar o chunk exato que a IA leu
            with st.container(height=550):
                st.info(fonte_atual["texto"])
        else:
            st.info("👈 Clique num botão de fonte gerado pela IA no chat para ler o trecho exato do livro do qual a informação foi extraída.")


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