import os
from pathlib import Path
import dotenv

# 1. Encontra a raiz do projeto e aponta para o .env
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# 2. Carrega as variáveis do arquivo .env
dotenv.load_dotenv(dotenv_path=ENV_PATH)

# 3. Puxa o caminho do .env. Se não existir, deixa como None (vazio)
vault_str = os.environ.get("PERSONAL_VAULT_PATH")
if not vault_str:
    raise ValueError("ERRO CRÍTICO: PERSONAL_VAULT_PATH não encontrado no arquivo .env!")
VAULT_PATH = Path(vault_str)

# 4. Transforma em objeto Path.
# O pathlib resolve as barras invertidas (\) do Windows automaticamente,
# então você não precisa mais se preocupar com o 'r' antes da string aqui!
VAULT_PATH = Path(vault_str) if vault_str else None

# 5. Suas pastas ignoradas continuam aqui normalmente
IGNORED_FOLDERS = [
    "99 - TEMP",    
    ".obsidian"    
]

MARCADOR_IA = "### Notas Relacionadas (IA)"