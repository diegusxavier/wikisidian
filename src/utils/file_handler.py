from pathlib import Path
from src.config import VAULT_PATH, IGNORED_FOLDERS

def get_all_md_files(vault_path: Path, pastas_ignoradas: list = None) -> list[Path]:
    """
    Varre o cofre do Obsidian e retorna uma lista com os caminhos
    de todos os arquivos .md, ignorando as subpastas configuradas de forma aninhada.
    """
    if pastas_ignoradas is None:
        pastas_ignoradas = IGNORED_FOLDERS

    md_files = []
    
    # Converte as pastas ignoradas do JSON em objetos Path para garantir 
    # que barras (/) e contra-barras (\) funcionem igual no Windows e no Mac.
    ignoradas_paths = [Path(p) for p in pastas_ignoradas]

    for file_path in vault_path.rglob("*.md"):
        is_ignored = False
        
        # Se qualquer parte do caminho começar com "." (ex: .obsidian, .trash), ignora direto
        if any(part.startswith(".") for part in file_path.parts):
            continue

        # Descobre qual é o caminho do arquivo "por dentro" do cofre
        # Ex: Se o cofre é C:/Obsidian e o ficheiro é C:/Obsidian/Faculdade/Nota.md
        # O rel_path será apenas 'Faculdade/Nota.md'
        rel_path = file_path.relative_to(vault_path)
        
        for ignored_folder, ignored_path in zip(pastas_ignoradas, ignoradas_paths):
            
            # 1. Verifica se a pasta ignorada é uma pasta-mãe ou subpasta exata no caminho
            if ignored_path == rel_path.parent or ignored_path in rel_path.parents:
                is_ignored = True
                break
                
            # 2. Fallback de segurança para nomes simples antigos (ex: ".obsidian")
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