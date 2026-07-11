import json
import re
import fitz  # PyMuPDF
from pathlib import Path

# ==========================================
# DEFINIÇÃO DE CAMINHOS
# ==========================================
# Resolve o caminho a partir de src/utils/pdf_handler.py -> wikisidian/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BOOKS_DIR = BASE_DIR / "books_data"
RAW_PDFS_DIR = BOOKS_DIR / "raw_pdfs"
EXTRACTED_TEXTS_DIR = BOOKS_DIR / "extracted_texts"

def setup_book_directories():
    """Garante que as pastas de livros existam."""
    RAW_PDFS_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTED_TEXTS_DIR.mkdir(parents=True, exist_ok=True)

def clean_text(text: str) -> str:
    """
    Limpa o texto do PDF:
    - Remove quebras de linha soltas no meio de frases.
    - Remove espaços múltiplos.
    """
    # Substitui quebras de linha por espaço, a menos que haja duas seguidas (fim de parágrafo)
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    # Remove espaços em excesso
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def process_pdf_to_json(pdf_path: Path) -> Path:
    """
    Lê um PDF, extrai o texto página por página e salva num JSON estruturado.
    Retorna o caminho do ficheiro JSON gerado.
    """
    setup_book_directories()
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"Ficheiro não encontrado: {pdf_path}")

    print(f"A ler PDF: {pdf_path.name}...")
    
    # Abre o documento com o PyMuPDF
    doc = fitz.open(pdf_path)
    
    # Estrutura de dados que vai garantir a nossa citação académica depois
    livro_dados = {
        "titulo": pdf_path.stem,
        "paginas": []
    }

    # Iterar página a página
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        cleaned_text = clean_text(text)
        
        # Só adiciona se houver texto (ignora páginas em branco ou só com imagens puras)
        if len(cleaned_text) > 10: 
            livro_dados["paginas"].append({
                "numero_pagina": page_num + 1,  # Guardamos como 1-indexed para o utilizador
                "texto": cleaned_text
            })
    
    doc.close()

    # Salvar em JSON na pasta de textos extraídos
    json_filename = f"{pdf_path.stem}.json"
    json_path = EXTRACTED_TEXTS_DIR / json_filename
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(livro_dados, f, ensure_ascii=False, indent=4)
        
    print(f"✔️ Extração concluída! Metadados guardados em: {json_path}")
    return json_path

# ==========================================
# BLOCO DE TESTE RÁPIDO (Se correr o ficheiro diretamente)
# ==========================================
if __name__ == "__main__":
    setup_book_directories()
    
    # Procura todos os ficheiros .pdf na pasta de raw_pdfs
    pdfs_encontrados = list(RAW_PDFS_DIR.glob("*.pdf"))
    
    if not pdfs_encontrados:
        print(f"⚠️ Nenhum PDF encontrado para testar.")
        print(f"Por favor, coloque pelo menos um arquivo .pdf na pasta:\n{RAW_PDFS_DIR}")
    else:
        pdf_teste = pdfs_encontrados[0]
        print(f"🧪 Iniciando teste com o arquivo: {pdf_teste.name}")
        
        try:
            caminho_json = process_pdf_to_json(pdf_teste)
            print(f"✅ Teste concluído com sucesso!")
            print(f"Abra o arquivo gerado para verificar se o texto foi extraído corretamente:\n{caminho_json}")
        except Exception as e:
            print(f"❌ Ocorreu um erro durante o processamento:\n{e}")