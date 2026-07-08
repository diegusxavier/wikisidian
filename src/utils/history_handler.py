import json
from pathlib import Path
from datetime import datetime
from src.config import BASE_DIR

# Define onde as conversas serão salvas (na raiz do projeto)
HISTORY_DIR = BASE_DIR / "chat_history"

def _garantir_pasta():
    """Cria a pasta chat_history se ela não existir."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

def salvar_conversa(conv_id: str, mensagens: list, titulo: str):
    """Salva a lista de mensagens num arquivo JSON."""
    _garantir_pasta()
    caminho = HISTORY_DIR / f"{conv_id}.json"
    
    dados = {
        "id": conv_id,
        "titulo": titulo,
        "atualizado_em": datetime.now().isoformat(),
        "mensagens": mensagens
    }
    
    caminho.write_text(json.dumps(dados, indent=4, ensure_ascii=False), encoding="utf-8")

def carregar_conversa(conv_id: str) -> list:
    """Lê um arquivo JSON e devolve a lista de mensagens."""
    caminho = HISTORY_DIR / f"{conv_id}.json"
    if caminho.exists():
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            return dados.get("mensagens", [])
        except Exception as e:
            print(f"Erro ao carregar conversa {conv_id}: {e}")
    return []

def listar_conversas() -> list:
    """Retorna uma lista de dicionários com as conversas salvas, ordenadas das mais recentes para as mais antigas."""
    _garantir_pasta()
    conversas = []
    
    for arquivo in HISTORY_DIR.glob("*.json"):
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            conversas.append({
                "id": dados.get("id"),
                "titulo": dados.get("titulo", "Conversa sem título"),
                "atualizado_em": dados.get("atualizado_em", "")
            })
        except Exception:
            pass # Ignora arquivos corrompidos
            
    # Ordena para a conversa mais recente aparecer no topo
    return sorted(conversas, key=lambda x: x["atualizado_em"], reverse=True)

def excluir_conversa(conv_id: str) -> bool:
    """Deleta o arquivo JSON da conversa."""
    caminho = HISTORY_DIR / f"{conv_id}.json"
    if caminho.exists():
        caminho.unlink()
        return True
    return False