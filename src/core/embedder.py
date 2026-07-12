import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

class VectorStore:
    # ALTERAÇÃO 1: Adicionamos 'collection_name' aqui, mantendo 'obsidian_notes' como padrão
    def __init__(self, db_path: str = "vector_store", collection_name: str = "obsidian_notes"):
        self.client = chromadb.PersistentClient(path=db_path)
        
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        # ALTERAÇÃO 2: Agora o nome da coleção é dinâmico. 
        # Assim você pode criar VectorStore(collection_name="pdf_books")
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

    # MANTER INTACTO: Este é o seu método antigo, que serve para as notas do Obsidian
    def add_notes(self, files: list[Path], contents: list[str]):
        # Quando passamos o 'contents' (que é uma lista de strings gigantes
        # com os textos das suas notas), o ChromaDB pega aquele modelo MiniLM
        # configurado na inicialização, passa texto por texto dentro da IA,
        # transforma tudo em matrizes de 384 dimensões e armazena na memória do banco.
        # Ele associa cada vetor ao seu 'id' (nome do arquivo) e aos seus metadados (caminho).
        ids = [str(f.name) for f in files] 
        self.collection.upsert(
            documents=contents,
            ids=ids,
            metadatas=[{"path": str(f)} for f in files]
        )
        print(f"{len(files)} notas processadas e salvas no banco vetorial!")

    # ALTERAÇÃO 3: Criamos um método novo, focado em receber os dados crus do livro.
    # Ele exige que você passe a lista de metadados para garantir a citação acadêmica.
    def add_chunks(self, ids: list[str], contents: list[str], metadatas: list[dict]):
        """
        Adiciona pedaços genéricos de texto (como páginas de um PDF) ao banco.
        Cada item em 'metadatas' deve conter, por exemplo: {"titulo": "Livro X", "pagina": 15}
        """
        self.collection.upsert(
            documents=contents,
            ids=ids,
            metadatas=metadatas
        )
        print(f"{len(contents)} blocos de texto salvos com sucesso!")

    # ALTERAÇÃO 4: Adicionamos o parâmetro 'where'. Isso é o que permite você 
    # filtrar a busca para procurar apenas num livro específico, resolvendo seu receio.
    def find_similar(self, text: str, top_k: int = 3, where_filter: dict = None):
        """
        Busca notas similares. Se 'where_filter' for passado, 
        ex: onde_buscar = {"titulo": "Dom_Casmurro"}, ele ignora os outros livros.
        """
        query_args = {
            "query_texts": [text],
            "n_results": top_k
        }
        
        # Se você passou um filtro (um livro específico), adicionamos isso na busca
        if where_filter:
            query_args["where"] = where_filter
            
        results = self.collection.query(**query_args)
        return results
    
    # MANTER INTACTO: Sua lógica original para o Obsidian
    def sync_db(self, current_files: list[Path]):
        existing_ids = self.collection.get()['ids']
        current_names = [f.name for f in current_files]
        to_delete = [id for id in existing_ids if id not in current_names]
        
        if to_delete:
            print(f"Limpando {len(to_delete)} notas deletadas do banco vetorial...")
            self.collection.delete(ids=to_delete)
        else:
            print("Banco vetorial sincronizado com o cofre.")