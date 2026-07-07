from pathlib import Path
from src.config import VAULT_PATH
from src.utils.file_handler import get_all_md_files
from src.config import MARCADOR_IA

def remove_ia_links(vault_path: Path, pastas_ignoradas: list = None) -> int:
    """
    Varre o cofre e remove todos os links gerados pela IA, 
    restaurando as notas ao seu estado original.
    """
    # Agora passamos a lista dinâmica para a nossa função de busca
    arquivos_md = get_all_md_files(vault_path, pastas_ignoradas)
    
    if not arquivos_md:
        return 0
        
    divisor_completo = f"\n\n---\n{MARCADOR_IA}"
    notas_limpas = 0
    
    for arquivo in arquivos_md:
        try:
            conteudo = arquivo.read_text(encoding='utf-8')
            
            if MARCADOR_IA in conteudo:
                if divisor_completo in conteudo:
                    texto_restaurado = conteudo.split(divisor_completo)[0]
                else:
                    texto_restaurado = conteudo.split(MARCADOR_IA)[0].rstrip()
                    if texto_restaurado.endswith("---"):
                        texto_restaurado = texto_restaurado[:-3].rstrip()
                
                arquivo.write_text(texto_restaurado, encoding='utf-8')
                notas_limpas += 1
                
        except Exception as e:
            print(f"Erro ao limpar '{arquivo.name}': {e}")
            
    return notas_limpas

# A função main() em baixo pode ficar como estava...

def main():
    """
    Função principal para executar este script isoladamente.
    """
    print("="*60)
    print("Iniciando Protocolo de Limpeza (Desfazendo links da IA)")
    print("="*60)
    
    total_limpo = remove_ia_links(VAULT_PATH)
    
    print("\n" + "="*60)
    print(f"Ufa! {total_limpo} arquivos foram restaurados com sucesso.")
    print("="*60)

# Permite rodar este ficheiro diretamente pelo terminal
if __name__ == '__main__':
    main()