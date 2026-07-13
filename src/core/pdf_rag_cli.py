import os
from dotenv import load_dotenv
from litellm import completion
from typing import Generator
from src.core.embedder import VectorStore

# Carrega as variaveis do arquivo .env
load_dotenv()

# Classe que gerencia a conversa com a IA, incluindo busca de notas relevantes, montagem do contexto, histórico e envio para o modelo.
class HybridRagEngine:
    def __init__(self):
        # Conecta nas duas gavetas do banco vetorial: uma para livros PDF e outra para notas do Obsidian
        self.db_books = VectorStore(collection_name="pdf_books")
        self.db_obsidian = VectorStore(collection_name="obsidian_notes") # Confirme se é este o nome da sua coleção de notas
        self.modelo = os.getenv("LLM_MODEL", "gemini/gemini-3.1-flash-lite")

    # Método principal que processa a pergunta do usuário, busca nos bancos vetoriais e interage com a IA
    def query(
        self, 
        pergunta_usuario: str, 
        book_titles: list = None,
        top_k: int = 4, 
        modo_estrito: bool = True,
        incluir_obsidian: bool = False,
        historico: list = None
    ) -> Generator[str, None, None]:
        
        contexto_str = ""
        encontrou_algo = False
        
        # Inicializa a lista de fontes utilizadas para rastrear de onde cada trecho veio
        self.fontes_utilizadas = [] 

        # Busca nos livros PDF (Se houver títulos especificados)
        filtro_livro = None
        if book_titles:
            if len(book_titles) == 1:
                filtro_livro = {"titulo": book_titles[0]}
            else:
                filtro_livro = {"titulo": {"$in": book_titles}}
        
        # Busca nos livros PDF com base no filtro definido (ou sem filtro se book_titles for None)
        res_livros = self.db_books.find_similar(
            text=pergunta_usuario, 
            top_k=top_k, 
            where_filter=filtro_livro
        )

        # Se encontrou resultados nos livros, monta o contexto e registra as fontes
        if res_livros['ids'] and res_livros['ids'][0]:
            encontrou_algo = True
            contexto_str += "=== TRECHOS DE LIVROS ===\n"
            for doc, meta in zip(res_livros['documents'][0], res_livros['metadatas'][0]):
                titulo = meta.get('titulo', 'Desconhecido')
                pagina = meta.get('pagina', '?')
                
                contexto_str += f"[LIVRO: {titulo} | PÁGINA: {pagina}]\n{doc}\n\n"
                
                # Salvamos o título, a página e o texto cru do chunk
                self.fontes_utilizadas.append({
                    "nome": f"{titulo} (p. {pagina})",
                    "texto": doc
                })

        # Busca no Obsidian (Se ativado)
        if incluir_obsidian:
            res_obsidian = self.db_obsidian.find_similar(
                text=pergunta_usuario, 
                top_k=top_k
            )
            
            if res_obsidian['ids'] and res_obsidian['ids'][0]:
                encontrou_algo = True
                contexto_str += "=== NOTAS DO OBSIDIAN ===\n"
                for doc, meta in zip(res_obsidian['documents'][0], res_obsidian['metadatas'][0]):
                    # Ajuste 'source' ou 'titulo' de acordo com o metadado que você usa nas notas
                    nome_nota = meta.get('source', 'Nota Desconhecida') 
                    contexto_str += f"[NOTA OBSIDIAN: {nome_nota}]\n{doc}\n\n"

        # Se não encontrou nada em nenhum dos bancos, retorna uma mensagem amigável
        if not encontrou_algo and modo_estrito:
            yield "Desculpe, não encontrei nenhuma informação sobre esse assunto nos livros ou notas selecionadas."
            return
        elif not encontrou_algo:
            contexto_str = "Nenhum contexto encontrado no banco de dados local."

        # Trata o histórico da conversa
        historico_str = ""
        if historico:
            historico_str = "HISTÓRICO RECENTE DA CONVERSA:\n"
            for msg in historico[-4:]:
                remetente = "USUÁRIO" if msg["role"] == "user" else "ASSISTENTE"
                historico_str += f"{remetente}: {msg.get('content', '')}\n"
            historico_str += "\n"

        # Define o prompt do sistema e do usuário com base no modo estrito ou híbrido
        if modo_estrito:
            temperatura = 0.2
            prompt_sistema = """Você é um assistente de pesquisa acadêmica rigoroso.
            REGRAS OBRIGATÓRIAS:
            1. Responda APENAS com base nos TRECHOS FORNECIDOS no contexto (Livros ou Notas).
            2. Ao usar livros, adicione a citação no formato: (Nome do Livro, p. X).
            3. Ao usar notas, adicione a citação no formato: (Nota: Nome da Nota).
            4. Se a informação não estiver presente nos trechos, diga: "Os textos fornecidos não abordam este assunto".
            5. Não invente informações."""
        else:
            temperatura = 0.6 
            prompt_sistema = """Você é um assistente de pesquisa avançado.
            REGRAS OBRIGATÓRIAS:
            1. Priorize responder com base nos TRECHOS FORNECIDOS (Livros e Notas).
            2. CITE SUAS FONTES: Tudo extraído do contexto deve ser citado como (Nome do Livro, p. X) ou (Nota: Nome da Nota).
            3. CONHECIMENTO GERAL: Se a resposta não estiver nos trechos, você PODE usar seu conhecimento geral para ajudar o usuário, mas DEVE avisar explicitamente (ex: "Embora meus arquivos locais não mencionem isso...").
            4. Não invente citações, páginas ou referências bibliográficas falsas."""

        prompt_usuario = f"CONTEXTO RECUPERADO:\n{contexto_str}\n\n{historico_str}PERGUNTA: {pergunta_usuario}\n"

        # Montagem da string de títulos de livros para exibição
        book_titles_str = ", ".join(book_titles) if book_titles else "Todos"
        print(f"Processando pergunta (Livros: {book_titles_str} | Obsidian: {incluir_obsidian} | Estrito: {modo_estrito})...")
        
        # Chamada à IA com streaming de resposta
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
# BLOCO DE TESTE
# ==========================================
if __name__ == "__main__":
    engine = HybridRagEngine()
    
    pergunta = "Qual a importância da educação bilingue?"
    
    print("\n--- TESTE: MODO ESTRITO (SÓ LIVROS) ---")
    for chunk in engine.query(pergunta, modo_estrito=True, incluir_obsidian=False):
        print(chunk, end="", flush=True)
        
    print("\n\n--- TESTE: MODO HÍBRIDO (LIVROS + OBSIDIAN + IA GERAL) ---")
    for chunk in engine.query(pergunta, modo_estrito=False, incluir_obsidian=True):
        print(chunk, end="", flush=True)