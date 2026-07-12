from src.core.embedder import VectorStore
# IMPORTANTE: Importe aqui a biblioteca que você já usa para chamar o Gemini no seu app
# Exemplo: import google.generativeai as genai 

class PDFRagEngine:
    def __init__(self):
        # Conecta exclusivamente na gaveta de livros
        self.db = VectorStore(collection_name="pdf_books")
        
    def query_book(self, user_question: str, book_title: str = None, top_k: int = 4):
        """
        Busca a resposta da pergunta dentro de um livro específico ou em todos.
        """
        # 1. Configura o filtro de busca (Opcional, mas recomendado)
        filtro = {"titulo": book_title} if book_title else None
        
        # 2. Busca os chunks mais relevantes no ChromaDB
        resultados = self.db.find_similar(
            text=user_question, 
            top_k=top_k, 
            where_filter=filtro
        )
        
        if not resultados['documents'][0]:
            return "Não encontrei informações relevantes nos livros para responder a essa pergunta."

        # 3. Monta o Contexto Acadêmico (A Mágica da Citação)
        contexto_formatado = ""
        documentos = resultados['documents'][0]
        metadados = resultados['metadatas'][0]

        for doc, meta in zip(documentos, metadados):
            # Injeta a referência exata antes de cada trecho para a IA ler
            contexto_formatado += f"[Fonte: {meta['titulo']} | Página: {meta['pagina']}]\n{doc}\n\n"

        # 4. O System Prompt (Instruções de Ouro)
        system_prompt = f"""
Você é um assistente de pesquisa acadêmica rigoroso. 
Responda à pergunta do usuário baseando-se EXCLUSIVAMENTE nos trechos fornecidos abaixo.

REGRAS OBRIGATÓRIAS DE CITAÇÃO:
- Ao final de toda frase ou afirmação que você fizer, você DEVE citar a fonte no formato: (Nome do Livro, p. X).
- Se a resposta não estiver nos trechos, diga "O texto fornecido não aborda este assunto". 
- Não invente informações e não use seu conhecimento prévio.

TRECHOS EXTRAÍDOS:
{contexto_formatado}
"""
        
        print("\n--- CONTEXTO ENVIADO PARA A IA ---")
        print(contexto_formatado)
        print("----------------------------------\n")

        # 5. Chamada para a LLM (Substitua pela sua chamada atual do Gemini)
        # Exemplo pseudo-código (adapte para o seu LiteLLM ou GenAI):
        # response = genai.generate_text(prompt=system_prompt + "\nPergunta: " + user_question)
        # return response.text
        
        return "Implementar chamada do Gemini aqui usando a variável 'system_prompt' e 'user_question'."

# ==========================================
# BLOCO DE TESTE RÁPIDO
# ==========================================
if __name__ == "__main__":
    engine = PDFRagEngine()
    
    # Teste de busca (substitua pelo nome de um livro que você já extraiu na Etapa C)
    pergunta = "Qual é o assunto principal?"
    nome_do_livro = "meu_livro_teste" # Opcional: coloque None para buscar em todos
    
    resposta = engine.query_book(pergunta, book_title=nome_do_livro)
    print(f"Resposta da IA:\n{resposta}")