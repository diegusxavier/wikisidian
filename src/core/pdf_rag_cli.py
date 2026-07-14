import os
from dotenv import load_dotenv
from litellm import completion
from typing import Generator
from src.core.embedder import VectorStore

# Carrega as variáveis do arquivo .env
load_dotenv()

# Classe que gerencia a conversa com a IA, incluindo busca de notas relevantes, montagem do contexto, histórico e envio para o modelo.
class HybridRagEngine:
    def __init__(self):
        # Conecta nas duas gavetas do banco vetorial: uma para livros PDF e outra para notas do Obsidian
        self.db_books = VectorStore(collection_name="pdf_books")
        self.db_obsidian = VectorStore(collection_name="obsidian_notes") 
        self.modelo = os.getenv("LLM_MODEL", "gemini/gemini-3.1-flash-lite")
        self.fontes_utilizadas = []
        self.notas_contexto_hibrido = []

    # Método principal que processa a pergunta do usuário, busca nos bancos vetoriais e interage com a IA
    def query(
        self, 
        pergunta_usuario: str, 
        book_titles: list = None,
        top_k: int = 5, 
        modo_estrito: bool = True,
        incluir_obsidian: bool = False,
        historico: list = None
    ) -> Generator[str, None, None]:
        
        contexto_str = ""
        encontrou_algo = False
        contexto_str = ""
        self.fontes_utilizadas = []
        self.notas_contexto_hibrido = []
        
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
            contexto_str += "=== TRECHOS DOS LIVROS/ARTIGOS ===\n"
            
            for doc, meta in zip(res_livros['documents'][0], res_livros['metadatas'][0]):
                nome_doc = meta.get('nome', 'Livro Desconhecido')
                
                if intencao == "GLOBAL":
                    contexto_str += f"[FONTE: RESUMO GLOBAL - {nome_doc}]\n{doc}\n\n"
                    self.fontes_utilizadas.append({
                        "nome": f"🗺️ Resumo: {nome_doc}",
                        "texto": doc
                    })
                else:
                    pagina_doc = meta.get('pagina', meta.get('numero_pagina', 'S/P'))
                    contexto_str += f"[FONTE: {nome_doc}, p. {pagina_doc}]\n{doc}\n\n"
                    self.fontes_utilizadas.append({
                        "nome": f"📄 {nome_doc} - p. {pagina_doc}",
                        "texto": doc
                    })

        # --- O PULO DO GATO (Injeção de UI) ---
        # Se foi específico, a IA já recebeu as páginas. 
        # Agora buscamos o Resumo de forma silenciosa apenas para colocar o botão na tela!
        if intencao == "ESPECIFICO":
            filtro_resumo = {"$and": [filtro_base, {"tipo_dado": "resumo"}]} if filtro_base else {"tipo_dado": "resumo"}
            res_ui = self.db_books.find_similar(text=pergunta_usuario, top_k=1, where_filter=filtro_resumo)
            
            if res_ui and res_ui.get('ids') and res_ui['ids'][0]:
                doc_resumo = res_ui['documents'][0][0]
                meta_resumo = res_ui['metadatas'][0][0]
                nome_doc_resumo = meta_resumo.get('nome', 'Livro Desconhecido')
                
                # Salvamos o título, a página e o texto cru do chunk
                self.fontes_utilizadas.append({
                    "nome": f"🗺️ Resumo: {nome_doc_resumo}",
                    "texto": doc_resumo
                })

        # Busca no Obsidian (Se ativado)
        if incluir_obsidian:
            res_obsidian = self.db_obsidian.find_similar(
                text=pergunta_usuario,
                top_k=top_k_busca
            )
            
            if res_obsidian and res_obsidian.get('ids') and res_obsidian['ids'][0]:
                encontrou_algo = True
                contexto_str += "=== NOTAS DO OBSIDIAN ===\n"
                for doc, meta in zip(res_obsidian['documents'][0], res_obsidian['metadatas'][0]):
                    # Ajuste 'source' ou 'titulo' de acordo com o metadado que você usa nas notas
                    nome_nota = meta.get('source', 'Nota Desconhecida') 
                    contexto_str += f"[NOTA OBSIDIAN: {nome_nota}]\n{doc}\n\n"

        # Se não encontrou nada em nenhum dos bancos, retorna uma mensagem amigável
        if not encontrou_algo and modo_estrito:
            yield "Os textos fornecidos não abordam este assunto. Não há dados locais suficientes para responder em Modo Estrito."
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
            1. Responda baseado prioritariamente nos TRECHOS FORNECIDOS no contexto. Se o Roteador indicou um contexto GLOBAL, use-o para sintetizar a visão geral pedida.
            2. Ao usar livros, adicione a citação no formato: (Nome do Livro, p. X).
            3. Ao usar notas, adicione a citação no formato: (Nota: Nome da Nota).
            4. Se a informação não estiver presente de forma alguma nos trechos, diga: "Os textos fornecidos não abordam este assunto".
            5. Não invente informações."""
        else:
            temperatura = 0.6 
            prompt_sistema = """Você é um assistente de pesquisa avançado.
            REGRAS OBRIGATÓRIAS:
            1. Priorize responder com base nos TRECHOS FORNECIDOS (Livros e Notas).
            2. CITE SUAS FONTES: Tudo extraído do contexto deve ser citado como (Nome do Livro, p. X) ou (Nota: Nome da Nota).
            3. CONHECIMENTO GERAL: Se a resposta não estiver nos trechos, você PODE usar seu conhecimento geral para ajudar o usuário, mas DEVE avisar explicitamente (ex: "Embora meus arquivos locais não mencionem isso...").
            4. Não invente citações, páginas ou referências falsas."""

        prompt_usuario = f"CONTEXTO RECUPERADO:\n{contexto_str}\n\n{historico_str}PERGUNTA: {pergunta_usuario}\n"

        # Montagem da string de títulos de livros para exibição
        book_titles_str = ", ".join(book_titles) if book_titles else "Todos"
        print(f"Processando pergunta (Livros: {book_titles_str} | Obsidian: {incluir_obsidian} | Estrito: {modo_estrito})...")
        
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