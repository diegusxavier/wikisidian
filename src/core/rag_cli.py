import os
from dotenv import load_dotenv
from litellm import completion
from typing import Generator
from src.core.embedder import VectorStore

# Carrega as variaveis do arquivo .env
load_dotenv()

class PDFRagEngine:
    def __init__(self):
        # Conecta exclusivamente na gaveta de livros
        self.db = VectorStore(collection_name="pdf_books")
        self.modelo = os.getenv("LLM_MODEL", "gemini/gemini-3.1-flash-lite")

    def query_book(
        self, 
        pergunta_usuario: str, 
        book_title: str = None, 
        top_k: int = 4, 
        modo_estrito: bool = True, 
        historico: list = None
    ) -> Generator[str, None, None]:
        
        # 1. Configura o filtro e busca no banco
        filtro = {"titulo": book_title} if book_title else None
        resultados = self.db.find_similar(
            text=pergunta_usuario, 
            top_k=top_k, 
            where_filter=filtro
        )

        ids_encontrados = resultados['ids'][0] if resultados['ids'] else []
        metadados_encontrados = resultados['metadatas'][0] if resultados['metadatas'] else []
        documentos_encontrados = resultados['documents'][0] if resultados['documents'] else []

        if not ids_encontrados and modo_estrito:
            yield "Desculpe, não encontrei nenhuma informação sobre esse assunto nos livros selecionados."
            return

        # 2. Montagem do Contexto (Carimbando a página em cada trecho)
        contexto_str = ""
        if ids_encontrados:
            for doc, meta in zip(documentos_encontrados, metadados_encontrados):
                contexto_str += f"\n--- FONTE: {meta['titulo']} | PÁGINA: {meta['pagina']} ---\n{doc}\n"
        else:
            contexto_str = "Nenhum trecho de livro encontrado no banco vetorial."

        # 3. Tratamento do Histórico Conversacional
        historico_str = ""
        if historico:
            historico_str = "HISTÓRICO RECENTE DA CONVERSA (Para contexto):\n"
            for msg in historico[-4:]:
                remetente = "USUÁRIO" if msg["role"] == "user" else "ASSISTENTE"
                conteudo = msg.get("content", "")
                historico_str += f"\n{remetente}: {conteudo}\n"
            historico_str += "\n"

        # 4. O Prompt Dinâmico (Estrito vs Híbrido)
        if modo_estrito:
            temperatura = 0.2
            prompt_sistema = """Você é um assistente de pesquisa acadêmica rigoroso.
            REGRAS OBRIGATÓRIAS:
            1. Responda APENAS com base nos TRECHOS FORNECIDOS no contexto.
            2. Ao final de toda frase ou afirmação que vier do texto, adicione a citação no formato: (Nome do Livro, p. X).
            3. Se a informação não estiver presente nos trechos, responda: "O texto fornecido não aborda este assunto".
            4. Não utilize nenhum conhecimento externo e não invente informações."""
        else:
            temperatura = 0.6 
            prompt_sistema = """Você é um assistente de pesquisa acadêmica.
            REGRAS OBRIGATÓRIAS:
            1. Você receberá TRECHOS FORNECIDOS de livros. Priorize sempre responder com base neles.
            2. CITAÇÕES OBRIGATÓRIAS: Tudo o que você extrair dos trechos deve ser citado no formato: (Nome do Livro, p. X).
            3. CONHECIMENTO EXTERNO: Se a resposta não estiver nos trechos, ou se precisar explicar um conceito complexo citado no texto, você PODE usar seu conhecimento geral.
            4. TRANSPARÊNCIA: Se usar conhecimento geral, você NÃO DEVE inventar páginas. Avise claramente no texto (ex: "Embora o livro não detalhe isso, de acordo com conhecimentos gerais...")."""

        prompt_usuario = f"""CONTEXTO (Trechos do Livro):\n{contexto_str}\n\n{historico_str}PERGUNTA DO USUÁRIO: {pergunta_usuario}\n"""

        # 5. A Chamada à IA
        print(f"PDFRagEngine a processar a pergunta (Livro: {book_title or 'Todos'} | Estrito: {modo_estrito})...")
        try:
            resposta = completion(
                model=self.modelo,
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario}
                ],
                temperature=temperatura,
                stream=True 
            )
            
            for pedaco in resposta:
                conteudo = pedaco.choices[0].delta.content
                if conteudo:
                    yield conteudo
            
        except Exception as e:
            yield f"Erro ao comunicar com a IA: {e}"

# ==========================================
# BLOCO DE TESTE RÁPIDO
# ==========================================
if __name__ == "__main__":
    engine = PDFRagEngine()
    
    # 1. Vamos checar se o banco realmente tem dados
    total_docs = engine.db.collection.count()
    print(f"Total de chunks salvos no banco 'pdf_books': {total_docs}")
    
    if total_docs == 0:
        print("O banco está vazio! Precisamos rodar o chunker.py novamente.")
    else:
        # 2. Faça uma pergunta sobre algo que você SABE que está no seu PDF
        # Substitua a string abaixo por um termo exato do seu livro de teste
        pergunta = "Substitua por uma palavra ou frase que existe no seu PDF"
        
        print(f"\nBuscando por: '{pergunta}'")
        
        # Vamos ver o que o banco devolve cru
        resultados_brutos = engine.db.find_similar(pergunta, top_k=2)
        print(f"IDs encontrados pelo ChromaDB: {resultados_brutos['ids']}")
        
        print("\nResposta da IA:")
        for pedaco in engine.query_book(pergunta, modo_estrito=True):
            print(pedaco, end="", flush=True)