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

    # Carrega os dados do JSON gerado pelo seu pdf_handler.py
    with open(json_path, "r", encoding="utf-8") as f:
        livro_dados = json.load(f)

    # Extrai o título e as páginas do livro 
    titulo = livro_dados.get("titulo", "Livro_Desconhecido")
    paginas = livro_dados.get("paginas", [])

    # Configura o fatiador 
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=300,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    chunks = []
    metadatas = []
    ids = []

    print(f"Fatiando o livro '{titulo}' com rigor acadêmico de página...")

    # Itera sobre cada página do livro
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

    # Envio para o ChromaDB
    print(f"Vetorizando {len(chunks)} chunks da página exata... Isso pode demorar um pouco.")
    
    db_livros = VectorStore(collection_name="pdf_books")
    db_livros.add_chunks(ids=ids, contents=chunks, metadatas=metadatas)
    
    print("Livro vetorizado e salvo no banco de dados com sucesso!")

# === Função para fatiar arquivos Markdown do Obsidian (FUNÇÃO DESATIVADA, MAS MANTIDA PARA REFERÊNCIA) ===
def chunk_markdown_file(texto: str, nome_arquivo: str, caminho_completo: str):
    """
    Fatia um arquivo Markdown respeitando seus cabeçalhos (#, ##, ###).
    Retorna três listas: ids, chunks_de_texto, e metadados.
    """
    # 1. Divide por cabeçalhos (mantém a hierarquia do Obsidian)
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    # Isso gera "Documentos" do Langchain onde o metadado diz de qual cabeçalho veio
    md_header_splits = markdown_splitter.split_text(texto)

    # 2. Proteção extra: Se uma seção (embaixo de um ##) for gigante, fatiamos por caracteres
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    splits_finais = text_splitter.split_documents(md_header_splits)

    chunks = []
    metadados = []
    ids = []

    for i, split in enumerate(splits_finais):
        chunks.append(split.page_content)
        
        # O SEGREDO ESTÁ AQUI: Salvamos o caminho da nota original para o Streamlit poder ler a nota inteira depois!
        meta = {
            "nome": nome_arquivo,
            "caminho": str(caminho_completo)
        }
        
        # Adicionamos os cabeçalhos (se a IA achar algo no "## Júlio César", ela saberá o título da seção)
        meta.update(split.metadata)
        
        metadados.append(meta)
        
        # Criamos um ID único para esse pedaço (Ex: Roma.md_chunk_0)
        ids.append(f"{nome_arquivo}_chunk_{i}")

    return ids, chunks, metadados

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