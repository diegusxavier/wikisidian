import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

class VectorStore:
    # Classe que gerencia o banco de dados vetorial. Ela é responsável por criar a coleção, adicionar notas e buscar notas similares.
    def __init__(self, db_path: str = "vector_store", collection_name: str = "obsidian_notes"):
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Embedding function é a função que transforma texto em vetores. Aqui estamos usando o modelo MiniLM, que é rápido e suporta múltiplos idiomas.
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        # Assim você pode criar VectorStore(collection_name="pdf_books")
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

    # Método para adicionar notas ao banco vetorial. Ele recebe uma lista de arquivos e seus conteúdos correspondentes.
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

    # Método para adicionar pedaços genéricos de texto ao banco.
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

    # Método para buscar notas similares. Ele recebe um texto e retorna as notas mais próximas no espaço vetorial.
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
    
    # Método para sincronizar o banco de dados vetorial com os arquivos atuais. Ele remove do banco as notas que foram deletadas do cofre.
    def sync_db(self, current_files: list[Path]):
        existing_ids = self.collection.get()['ids']
        current_names = [f.name for f in current_files]
        to_delete = [id for id in existing_ids if id not in current_names]
        
        if to_delete:
            print(f"Limpando {len(to_delete)} notas deletadas do banco vetorial...")
            self.collection.delete(ids=to_delete)
        else:
            print("Banco vetorial sincronizado com o cofre.")