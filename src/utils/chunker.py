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

    # 1. Carrega os dados do JSON gerado pelo seu pdf_handler.py
    with open(json_path, "r", encoding="utf-8") as f:
        livro_dados = json.load(f)

    titulo = livro_dados.get("titulo", "Livro_Desconhecido")
    paginas = livro_dados.get("paginas", [])

    # 2. Configura o fatiador 
    # Aumentei um pouco o overlap para compensar o fato de cortarmos estritamente por página
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=300,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    chunks = []
    metadatas = []
    ids = []

    print(f"Fatiando o livro '{titulo}' com rigor acadêmico de página...")

    for pagina in paginas:
        texto_atual = pagina["texto"]
        numero_pagina = pagina["numero_pagina"]

        # Fatiamos APENAS o texto da página atual
        pedacos = text_splitter.split_text(texto_atual)

        for j, pedaco in enumerate(pedacos):
            chunks.append(pedaco)
            # Metadados estritos: sem mistura de páginas
            metadatas.append({
                "titulo": titulo,
                "pagina": numero_pagina
            })
            # ID único que você pode usar para deletar ou atualizar depois
            ids.append(f"{titulo}_p{numero_pagina}_chunk{j}")

    # 3. Envio para o ChromaDB
    print(f"Vetorizando {len(chunks)} chunks da página exata... Isso pode demorar um pouco.")
    
    db_livros = VectorStore(collection_name="pdf_books")
    db_livros.add_chunks(ids=ids, contents=chunks, metadatas=metadatas)
    
    print("Livro vetorizado e salvo no banco de dados com sucesso!")

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