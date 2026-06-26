import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

class VectorStore:
    def __init__(self, db_path: str = "vector_store"):
        # 1. CRIANDO O BANCO LOCAL
        # Inicializa o ChromaDB dizendo para ele salvar as matrizes numéricas
        # fisicamente na pasta "vector_store" do seu projeto. Assim o cálculo não é perdido.
        self.client = chromadb.PersistentClient(path=db_path)
        
        # 2. CARREGANDO A IA DE EMBEDDING
        # Instancia a função de embedding do SentenceTransformers.
        # Na primeira vez que você rodar o programa, ele vai baixar os pesos do 
        # modelo 'paraphrase-multilingual-MiniLM...' para a sua máquina.
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        # 3. CRIANDO O ESPAÇO N-DIMENSIONAL
        # O ChromaDB organiza os dados em "coleções". 
        # Aqui, estamos definindo a métrica matemática 'cosine' (cosseno) 
        # para que ele saiba como calcular a distância angular entre suas notas.
        self.collection = self.client.get_or_create_collection(
            name="obsidian_notes",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

    def add_notes(self, files: list[Path], contents: list[str]):
        ids = [str(f.name) for f in files] 
        
        # 4. A VETORIZAÇÃO AUTOMÁTICA
        # Quando passamos o 'contents' (que é uma lista de strings gigantes
        # com os textos das suas notas), o ChromaDB pega aquele modelo MiniLM
        # configurado na inicialização, passa texto por texto dentro da IA, 
        # transforma tudo em matrizes de 384 dimensões e armazena na memória do banco.
        # Ele associa cada vetor ao seu 'id' (nome do arquivo) e aos seus metadados (caminho).
        self.collection.add(
            documents=contents,
            ids=ids,
            metadatas=[{"path": str(f)} for f in files]
        )
        print(f"{len(files)} notas processadas e salvas no banco vetorial!")

    def find_similar(self, text: str, top_k: int = 3):
        # 5. A BUSCA SEMÂNTICA
        # Quando você quiser encontrar notas parecidas com "text", o ChromaDB
        # primeiro vetoriza esse "text" em tempo real usando o MiniLM.
        # Depois, ele varre as matrizes que já estão salvas e devolve as 
        # 'top_k' notas que têm o menor ângulo (maior similaridade de cosseno).
        results = self.collection.query(
            query_texts=[text],
            n_results=top_k
        )
        return results