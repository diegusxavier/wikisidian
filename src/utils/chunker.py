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

# Função para fatiar arquivos Markdown do Obsidian
def chunk_markdown_file(texto: str, nome_arquivo: str, caminho_completo: str, mtime: float, tamanho_chunk: int = 1500, overlap: int = 300):    
    """
    Fatia um arquivo Markdown com base na quantidade de caracteres e sobreposição (overlap),
    ignorando a estrutura de cabeçalhos para evitar chunks muito pequenos.
    """
    chunks_nota = []
    ids_nota = []
    metadados_nota = []
    
    tamanho_texto = len(texto)
    inicio = 0
    contador_chunk = 0
    
    # Se a nota for muito pequena, salva ela inteira de uma vez
    if tamanho_texto <= tamanho_chunk:
        chunks_nota.append(texto)
        ids_nota.append(f"{nome_arquivo}_unico")
        metadados_nota.append({
            "nome": nome_arquivo,
            "path": caminho_completo,
            "tipo_dado": "nota", # Mantendo a nossa padronização de Tipagem Forte!
            "mtime": mtime
        })
        return ids_nota, chunks_nota, metadados_nota

    # Lógica de Janela Deslizante (Sliding Window) para notas grandes
    while inicio < tamanho_texto:
        # Pega o bloco de texto do tamanho limite
        fim = inicio + tamanho_chunk
        pedaco = texto[inicio:fim]
        
        # Opcional (porém recomendado): Não cortar a palavra no meio.
        # Se não chegamos no fim do texto, recuamos até encontrar um espaço ou quebra de linha
        if fim < tamanho_texto:
            ultimo_espaco = max(pedaco.rfind(' '), pedaco.rfind('\n'))
            if ultimo_espaco != -1:
                fim = inicio + ultimo_espaco
                pedaco = texto[inicio:fim]
        
        # Só adiciona se o pedaço tiver conteúdo real
        if pedaco.strip():
            chunks_nota.append(pedaco.strip())
            ids_nota.append(f"{nome_arquivo}_chunk_{contador_chunk}")
            metadados_nota.append({
                "nome": nome_arquivo,
                "path": caminho_completo,
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