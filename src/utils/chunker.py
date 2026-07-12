import json
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Importamos o seu banco de dados atualizado
from src.core.embedder import VectorStore

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXTRACTED_TEXTS_DIR = BASE_DIR / "books_data" / "extracted_texts"

def chunk_and_embed_book(json_filename: str):
    json_path = EXTRACTED_TEXTS_DIR / json_filename
    if not json_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {json_path}")

    # Lemos os dados estruturados do PDF
    with open(json_path, "r", encoding="utf-8") as f:
        livro_dados = json.load(f)

    titulo = livro_dados["titulo"]
    paginas = livro_dados["paginas"]

    # Configuramos o fatiador inteligente
    # chunk_size: Tamanho máximo de letras por pedaço
    # chunk_overlap: Quantas letras um pedaço compartilha com o próximo
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=250,
        separators=["\n\n", "\n", ".", " ", ""] # Tenta cortar primeiro em parágrafos, depois pontos...
    )

    chunks = []
    metadatas = []
    ids = []

    print(f"Fatiando o livro '{titulo}' e resolvendo fronteiras de páginas...")

    for i, pagina in enumerate(paginas):
        texto_atual = pagina["texto"]
        numero_pagina = pagina["numero_pagina"]

        # Começamos a montar o nosso "Sanduíche de Contexto"
        texto_enriquecido = ""

        # 1. Borda Superior: Pega os últimos 300 caracteres da página anterior (se não for a primeira página)
        if i > 0:
            texto_anterior = paginas[i - 1]["texto"]
            texto_enriquecido += texto_anterior[-300:] + " " # [-300:] pega de trás para frente

        # 2. O Recheio: A página atual inteira
        texto_enriquecido += texto_atual

        # 3. Borda Inferior: Pega os primeiros 400 caracteres da próxima página (se não for a última)
        if i + 1 < len(paginas):
            texto_proxima = paginas[i + 1]["texto"]
            texto_enriquecido += " " + texto_proxima[:300]

        # Agora entregamos esse texto super protegido para o text_splitter cortar em pedaços de 1000
        pedacos = text_splitter.split_text(texto_enriquecido)

        for j, pedaco in enumerate(pedacos):
            chunks.append(pedaco)
            # Metadados perfeitos para a citação acadêmica
            metadatas.append({
                "titulo": titulo,
                "pagina": numero_pagina
            })
            # Criamos um ID único para cada pedaço
            ids.append(f"{titulo}_p{numero_pagina}_chunk{j}")

    # Agora enviamos para o ChromaDB, usando a coleção específica de livros
    print(f"Vetorizando {len(chunks)} chunks... Isso pode demorar um pouco.")
    
    db_livros = VectorStore(collection_name="pdf_books")
    db_livros.add_chunks(ids=ids, contents=chunks, metadatas=metadatas)
    
    print("✔️ Livro vetorizado e salvo no banco de dados com sucesso!")

# ==========================================
# BLOCO DE TESTE RÁPIDO
# ==========================================
if __name__ == "__main__":
    # Pega o primeiro arquivo JSON da pasta para testar
    jsons_encontrados = list(EXTRACTED_TEXTS_DIR.glob("*.json"))
    
    if jsons_encontrados:
        arquivo_teste = jsons_encontrados[0].name
        chunk_and_embed_book(arquivo_teste)
    else:
        print("Nenhum JSON encontrado. Rode o pdf_handler.py primeiro.")