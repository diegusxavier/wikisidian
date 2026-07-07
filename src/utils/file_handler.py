from pathlib import Path
from src.config import VAULT_PATH, IGNORED_FOLDERS

def get_all_md_files(vault_path: Path, pastas_ignoradas: list = None) -> list[Path]:
    """
    Varre o cofre do Obsidian e retorna uma lista com os caminhos
    de todos os arquivos .md, ignorando as pastas configuradas.
    """
    # Se não passarmos nada, usa a configuração padrão (útil para o chat.py do terminal)
    if pastas_ignoradas is None:
        pastas_ignoradas = IGNORED_FOLDERS

    md_files = []
    
    for file_path in vault_path.rglob("*.md"):
        is_ignored = False
        
        # Agora usamos a variável dinâmica 'pastas_ignoradas'
        for ignored_folder in pastas_ignoradas:
            if ignored_folder in file_path.parts:
                is_ignored = True
                break  
        
        if not is_ignored:
            md_files.append(file_path)
            
    return md_files

def read_file_content(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Erro ao ler o arquivo {file_path.name}: {e}")
        return ""