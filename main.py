from src.config import VAULT_PATH
from src.utils.file_handler import get_all_md_files, read_file_content
from src.core.embedder import VectorStore

def main():
    print("="*50)
    print("Inicializando Motor de Inteligência Artificial...")
    # Isso pode demorar alguns segundos na primeira vez, pois ele 
    # carrega o modelo do SentenceTransformers na memória.
    vetor_db = VectorStore()
    print("-"*50)
    
    arquivos_md = get_all_md_files(VAULT_PATH)
    
    if not arquivos_md:
        print("Nenhum arquivo encontrado.")
        return
    else:
        print(f"{len(arquivos_md)} arquivos .md encontrados no cofre.")
        for arquivo in arquivos_md:
            print(f"- {arquivo}")
        print("-"*50)

    # Para o teste ser rápido, vamos pegar apenas as 5 primeiras notas
    arquivos_teste = arquivos_md[:5]
    conteudos_teste = [read_file_content(f) for f in arquivos_teste]

    print("\n" + "-"*50)
    print("Conteúdo [0] de exemplo:")
    print(conteudos_teste[0][:500] + "...\n")  # Mostra apenas os primeiros 500 caracteres
    print("-"*50)

    
    print(f"\nInserindo {len(arquivos_teste)} notas no banco vetorial...")
    # Isso vai transformar os textos em vetores e salvar na pasta 'vector_store'
    vetor_db.add_notes(arquivos_teste, conteudos_teste)
    
    print("\n" + "-"*50)
    print("Testando a busca por similaridade...")
    # Vamos fazer uma pergunta aleatória. Você pode mudar esse texto para 
    # algo que tenha a ver com as 5 notas que foram processadas.
    termo_busca = "engenharia" 
    
    resultados = vetor_db.find_similar(text=termo_busca, top_k=2)
    
    print(f"\nResultados para a busca: '{termo_busca}'")
    # O ChromaDB retorna um dicionário complexo. A chave 'ids' contém o nome dos arquivos
    # e a chave 'distances' contém a distância (quanto menor, mais similar)
    ids_encontrados = resultados['ids'][0]
    
    for i, nome_arquivo in enumerate(ids_encontrados):
        print(f"{i+1}º lugar: {nome_arquivo}")
        
    print("\n" + "="*50)

if __name__ == '__main__':
    main()