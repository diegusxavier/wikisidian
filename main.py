from src.config import VAULT_PATH
from src.utils.file_handler import get_all_md_files, read_file_content
from src.core.embedder import VectorStore
from src.core.linker import ObsidianLinker

def main():
    print("="*60)
    print("Gestor de Conhecimento Obsidian")
    print("="*60)
    
    # 1. Busca os arquivos
    arquivos_md = get_all_md_files(VAULT_PATH)
    if not arquivos_md:
        print("Nenhum arquivo encontrado no cofre.")
        return
        
    print(f"Encontrados {len(arquivos_md)} arquivos .md no cofre.")

    # 2. Lê os conteúdos e alimenta a Inteligência Artificial
    print("\nCarregando notas na Inteligência Artificial...")
    
    vetor_db = VectorStore()
    vetor_db.sync_db(arquivos_md) # sincroniza o banco com os arquivos atuais do cofre

    conteudos = [read_file_content(f) for f in arquivos_md]
    vetor_db.add_notes(arquivos_md, conteudos)
    
    # 3. Inicializa o Linker
    linker = ObsidianLinker(vetor_db)
    
    print("\n" + "="*60)
    print("Iniciando injeção e atualização de Backlinks...")
    print("="*60)
    
    notas_atualizadas = 0
    
    # 4. O Loop Principal: Varre cada nota e tenta criar conexões
    for arquivo in arquivos_md:
        # Pede para o linker injetar até 3 novos links
        alterou = linker.inject_links(arquivo, top_k=3)
        
        if alterou:
            notas_atualizadas += 1
            print(f"Atualizada: {arquivo.name}")
            
    print("\n" + "="*60)
    print(f"Finalizado! {notas_atualizadas} notas receberam novas conexões.")
    print("="*60)

if __name__ == '__main__':
    main()