import os
import json
from pathlib import Path
import dotenv

# 1. Encontra a raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
SETTINGS_PATH = BASE_DIR / "settings.json" # O nosso novo ficheiro de configuração local

dotenv.load_dotenv(dotenv_path=ENV_PATH)

# ==========================================
# LÓGICA DO SETTINGS.JSON
# ==========================================
def carregar_configuracoes() -> dict:
    """Lê o ficheiro settings.json. Se não existir, devolve um dicionário padrão."""
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
        except Exception:
            return {"vault_path": "", "ignored_folders": ["99 - TEMP", ".obsidian"]}
    else:
        # Valores padrão se o ficheiro ainda não existir
        return {"vault_path": "", "ignored_folders": ["99 - TEMP", ".obsidian"]}

def salvar_configuracoes(nova_config: dict):
    """Sobrescreve o ficheiro settings.json com as novas configurações."""
    SETTINGS_PATH.write_text(json.dumps(nova_config, indent=4, ensure_ascii=False), encoding='utf-8')

# Carrega as configurações na memória ao iniciar
CONFIG_ATUAL = carregar_configuracoes()

# ==========================================
# VARIÁVEIS EXPORTADAS
# ==========================================
# O MARCADOR_IA que criámos para seguir o princípio DRY
MARCADOR_IA = "### Notas Relacionadas (IA)"

# Tenta pegar do settings.json. Se estiver vazio lá, tenta do .env como plano B (para não quebrar nada agora)
caminho_salvo = CONFIG_ATUAL.get("vault_path", "").strip()
if not caminho_salvo:
    caminho_salvo = os.environ.get("PERSONAL_VAULT_PATH", "")

VAULT_PATH = Path(caminho_salvo) if caminho_salvo else None

# Carrega as pastas ignoradas do JSON
IGNORED_FOLDERS = CONFIG_ATUAL.get("ignored_folders", [])