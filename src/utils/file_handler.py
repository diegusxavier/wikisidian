from pathlib import Path
from src.config import VAULT_PATH, IGNORED_FOLDERS

def get_all_md_files(vault_path: Path) -> list[Path]:
    """
    Varre o cofre do Obsidian e retorna uma lista com os caminhos
    de todos os arquivos .md, ignorando as pastas configuradas.
    """
    md_files = []
    
    # O método .rglob("*.md") procura todos os arquivos que terminam com .md
    # na pasta principal e em todas as subpastas (r de recursivo).
    for file_path in vault_path.rglob("*.md"):
        
        # file_path.parts divide o caminho em pedaços. 
        # Ex: ('C:', 'Cofre', '__TEMP__', 'nota.md')
        # Isso é mais seguro que apenas checar se a palavra "__TEMP__" está na string.
        is_ignored = False
        for ignored_folder in IGNORED_FOLDERS:
            if ignored_folder in file_path.parts:
                is_ignored = True
                break  # Se achou uma pasta ignorada, para de procurar nesta nota
        
        # Se o arquivo não está em uma pasta ignorada, adicionamos à lista
        if not is_ignored:
            md_files.append(file_path)
            
    return md_files


def read_file_content(file_path: Path) -> str:
    """
    Lê o conteúdo de um arquivo de forma segura, garantindo que acentos 
    e caracteres especiais (UTF-8) sejam entendidos pelo Python.
    """
    try:
        # .read_text() é uma função maravilhosa do pathlib que abre, 
        # lê o conteúdo inteiro e fecha o arquivo automaticamente.
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Erro ao ler o arquivo {file_path.name}: {e}")
        return ""