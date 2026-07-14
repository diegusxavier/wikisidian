import json
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters import MarkdownHeaderTextSplitter

# Importamos o seu banco de dados atualizado
from src.core.embedder import VectorStore

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXTRACTED_TEXTS_DIR = BASE_DIR / "books_data" / "extracted_texts"

# Função para fatiar e vetorização de livros PDF
def chunk_and_embed_book(json_filename: str):
    json_path = EXTRACTED_TEXTS_DIR / json_filename
    if not json_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        livro_dados = json.load(f)

    titulo = livro_dados.get("titulo", "Livro_Desconhecido")
    paginas = livro_dados.get("paginas", [])

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, chunk_overlap=300, separators=["\n\n", "\n", ".", " ", ""]
    )

    chunks = []
    metadatas = []
    ids = []

    print(f"Fatiando o livro '{titulo}' com rigor acadêmico de página...")

    # 1. Processar todas as páginas
    for pagina in paginas:
        texto_atual = pagina["texto"]
        numero_pagina = pagina["numero_pagina"]

        pedacos = text_splitter.split_text(texto_atual)

        for j, pedaco in enumerate(pedacos):
            chunks.append(pedaco)
            metadatas.append({
                "titulo": titulo,
                "pagina": numero_pagina,
                "tipo_dado": "pagina" # <- AQUI INJETAMOS O METADADO
            })
            ids.append(f"{titulo}_p{numero_pagina}_chunk{j}")

    # 2. O PULO DO GATO: Ler e vetorizar o Resumo Global também!
    caminho_resumo = BASE_DIR / "books_data" / "summaries" / f"RESUMO_{titulo}.txt"
    if caminho_resumo.exists():
        with open(caminho_resumo, "r", encoding="utf-8") as f:
            texto_resumo = f.read()
        chunks.append(texto_resumo)
        metadatas.append({
            "titulo": titulo,
            "pagina": 0, 
            "tipo_dado": "resumo" # <- AQUI MARCAMOS COMO RESUMO
        })
        ids.append(f"{titulo}_resumo_global")

    print(f"Vetorizando {len(chunks)} chunks... Isso pode demorar um pouco.")
    
    db_livros = VectorStore(collection_name="pdf_books")
    db_livros.add_chunks(ids=ids, contents=chunks, metadatas=metadatas)
    print("Livro vetorizado e salvo no banco de dados com sucesso!")

# Função para fatiar arquivos Markdown do Obsidian
def chunk_markdown_file(texto: str, nome_arquivo: str, caminho_completo: str, mtime: float, tamanho_chunk: int = 1500, overlap: int = 300):
    """
    Fatia um arquivo Markdown com base na quantidade de caracteres e sobreposição (overlap),
    garantindo blocos de tamanho uniforme. Injeta o título do documento
    no início de cada chunk para evitar a "perda de contexto" na vetorização.
    """
    chunks_nota = []
    ids_nota = []
    metadados_nota = []
    
    tamanho_texto = len(texto)
    inicio = 0
    contador_chunk = 0
    
    # Remove a extensão .md para ficar um título limpo no enriquecimento
    titulo_limpo = nome_arquivo.replace(".md", "")
    
    # Se a nota for muito pequena, salva ela inteira de uma vez
    if tamanho_texto <= tamanho_chunk:
        chunk_enriquecido = f"[Documento: {titulo_limpo}]\n{texto}"
        chunks_nota.append(chunk_enriquecido)
        ids_nota.append(f"{nome_arquivo}_unico")
        metadados_nota.append({
            "nome": nome_arquivo,
            "path": str(caminho_completo),
            "caminho": str(caminho_completo), # Mantido da branch feat para o app.py
            "tipo_dado": "nota", # Mantendo a nossa padronização de Tipagem Forte!
            "mtime": mtime
        })
        return ids_nota, chunks_nota, metadados_nota

    # Lógica de Janela Deslizante (Sliding Window) para notas grandes
    while inicio < tamanho_texto:
        # Pega o bloco de texto do tamanho limite
        fim = inicio + tamanho_chunk
        pedaco = texto[inicio:fim]
        
        # Não cortar a palavra no meio
        if fim < tamanho_texto:
            ultimo_espaco = max(pedaco.rfind(' '), pedaco.rfind('\n'))
            if ultimo_espaco != -1:
                fim = inicio + ultimo_espaco
                pedaco = texto[inicio:fim]
        
        # Só adiciona se o pedaço tiver conteúdo real
        if pedaco.strip():
            # O PULO DO GATO (Enriquecimento da branch feat acoplado aqui): 
            chunk_enriquecido = f"[Documento: {titulo_limpo}]\n{pedaco.strip()}"
            chunks_nota.append(chunk_enriquecido)
            
            ids_nota.append(f"{nome_arquivo}_chunk_{contador_chunk}")
            metadados_nota.append({
                "nome": nome_arquivo,
                "path": str(caminho_completo),
                "caminho": str(caminho_completo), # Mantido da branch feat
                "tipo_dado": "nota", 
                "mtime": mtime
            })
            contador_chunk += 1
            
        # O próximo chunk começa recuando o valor do overlap para não perder contexto
        inicio = fim - overlap
        
    return ids_nota, chunks_nota, metadados_nota


# ==========================================
# BLOCO DE TESTE RÁPIDO
# ==========================================
if __name__ == "__main__":
    jsons_encontrados = list(EXTRACTED_TEXTS_DIR.glob("*.json"))
    
    if jsons_encontrados:
        arquivo_teste = jsons_encontrados[0].name
        print(f"Iniciando teste com o arquivo: {arquivo_teste}")
        chunk_and_embed_book(arquivo_teste)
    else:
        print("Nenhum JSON encontrado. Rode o seu extrator de PDF primeiro.")