import os
import json
from pathlib import Path
import chromadb

class VectorStore:
    def __init__(self, collection_name="obsidian_notes"):
        # Mantenha a sua conexão atual com o ChromaDB aqui
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(name=collection_name)
        
        # NOVO: O "cérebro" que lembra o que já foi processado
        self.sync_cache_path = Path("books_data/obsidian_cache.json")

    def _carregar_cache(self):
        if self.sync_cache_path.exists():
            with open(self.sync_cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _salvar_cache(self, cache_dict):
        self.sync_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.sync_cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_dict, f, indent=4)

    def sync_db(self, arquivos_md: list[Path]) -> list[Path]:
        """
        Compara os arquivos reais com o cache. 
        Retorna APENAS a lista de arquivos que precisam ser (re)vetorizados.
        """
        cache_atual = self._carregar_cache()
        arquivos_pendentes = []
        novo_cache = {}

        print("Verificando alterações no cofre Obsidian...")

        # 1. Verifica adições e modificações
        for arquivo in arquivos_md:
            caminho_str = str(arquivo)
            # Lê o timestamp de última modificação do arquivo no Windows/Mac/Linux
            tempo_modificacao = os.path.getmtime(arquivo)

            # Se o arquivo é novo OU foi editado recentemente
            if caminho_str not in cache_atual or cache_atual[caminho_str] != tempo_modificacao:
                arquivos_pendentes.append(arquivo)
                # Opcional: Se for uma modificação, apagamos os chunks antigos antes de gerar os novos
                if caminho_str in cache_atual:
                    self.collection.delete(where={"caminho": caminho_str})

            novo_cache[caminho_str] = tempo_modificacao

        # 2. Verifica deleções (Notas que você apagou do Obsidian)
        arquivos_deletados = [caminho for caminho in cache_atual if caminho not in novo_cache]
        if arquivos_deletados:
            for deletado in arquivos_deletados:
                self.collection.delete(where={"caminho": deletado})
            print(f"{len(arquivos_deletados)} arquivos deletados removidos do banco vetorial.")

        # Salva o estado atualizado para a próxima execução
        self._salvar_cache(novo_cache)

        return arquivos_pendentes
        
    # Mantenha os seus métodos find_similar e add_chunks intactos abaixo...

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