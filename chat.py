from src.config import VAULT_PATH
from src.utils.file_handler import get_all_md_files, read_file_content
from src.core.embedder import VectorStore
from src.core.rag_cli import WikisidianChat

def main():
    print("="*60)
    print("Inicializando Motor de Busca e Wikisidian...")
    print("="*60)
    
    arquivos_md = get_all_md_files(VAULT_PATH)
    conteudos = [read_file_content(f) for f in arquivos_md]
    
    vetor_db = VectorStore()
    vetor_db.add_notes(arquivos_md, conteudos)
    
    chat = WikisidianChat(vetor_db, VAULT_PATH)
    
    print("\nSistema online. Bem-vindo de volta.")
    print("Digite 'sair' para encerrar.\n")
    
    while True:
        pergunta = input("\nVoce: ")
        
        if pergunta.lower().strip() in ['sair', 'exit', 'quit']:
            print("Wikisidian: Encerrando os sistemas. Ate logo!")
            break
            
        if not pergunta.strip():
            continue
            
        resposta = chat.perguntar(pergunta)
        
        print("\n" + "="*60)
        print(f"Wikisidian:\n{resposta}")
        print("="*60)

if __name__ == '__main__':
    main()