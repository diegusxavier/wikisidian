import os
from dotenv import load_dotenv
from litellm import completion
from typing import Generator
from src.core.embedder import VectorStore

# Carrega as variáveis do arquivo .env
load_dotenv()

class HybridRagEngine:
    def __init__(self):
        # Conecta nas duas gavetas utilizando os nomes exatos das variáveis
        self.db_books = VectorStore(collection_name="pdf_books")
        self.db_obsidian = VectorStore(collection_name="obsidian_notes") 
        self.modelo = os.getenv("LLM_MODEL", "gemini/gemini-3.1-flash-lite")
        self.fontes_utilizadas = []
        self.notas_contexto_hibrido = []

    def query(self, pergunta_usuario: str, book_titles: list, modo_estrito: bool, incluir_obsidian: bool, historico: list = None) -> Generator[str, None, None]:
        """
        Método principal de consulta que atua como um Roteador Cognitivo entre buscas Globais e Específicas.
        """
        # Inicialização das flags de controle
        encontrou_algo = False
        contexto_str = ""
        self.fontes_utilizadas = []
        self.notas_contexto_hibrido = []
        
        # Define o limite de busca padronizado para as consultas locais
        top_k_busca = 5

        # ------------------------------------------------------------------
        # 🔀 PASSO 1: O ROTEADOR (Classificação de Intenção)
        # ------------------------------------------------------------------
        prompt_roteador = f"""
        Analise a pergunta do usuário sobre um livro ou artigo e classifique-a em uma das duas categorias abaixo.
        Responda APENAS com a palavra 'GLOBAL' ou 'ESPECIFICO'. Não adicione pontos, explicações ou nenhuma outra palavra.

        - GLOBAL: Se a pergunta pede um resumo geral, a tese principal, os objetivos do documento, a lista de capítulos/contos, a conclusão ou análises que exigem a visão do todo.
        - ESPECIFICO: Se a pergunta busca um fato isolado, um dado numérico, o nome de um personagem, uma definição matemática isolada ou um detalhe cirúrgico.

        Pergunta do usuário: "{pergunta_usuario}"
        Resposta:"""

        try:
            resposta_roteador = completion(
                model=self.modelo,
                messages=[{"role": "user", "content": prompt_roteador}],
                temperature=0.0, 
                stream=False
            )
            intencao = resposta_roteador.choices[0].message.content.strip().upper()
        except Exception:
            intencao = "ESPECIFICO"

        print(f"🔮 Roteador Wikisidian: Pergunta classificada como [{intencao}]")

        # ------------------------------------------------------------------
        # 🔎 PASSO 2: A BUSCA DIRECIONADA NO CHROMADB (LIVROS/ARTIGOS)
        # ------------------------------------------------------------------
        
        # Montagem inteligente do filtro 'where' do ChromaDB para múltiplos livros
        # Se houver apenas 1 livro selecionado: {"nome": "Livro_X"}
        # Se houver múltiplos: {"$or": [{"nome": "Livro_X"}, {"nome": "Livro_Y"}]}
        if len(book_titles) == 1:
            filtro_base = {"nome": book_titles[0]}
        elif len(book_titles) > 1:
            filtro_base = {"$or": [{"nome": titulo} for titulo in book_titles]}
        else:
            filtro_base = {}

        if intencao == "GLOBAL":
            # Forçamos o ChromaDB a filtrar estritamente o chunk que possui a flag 'is_resumo_global'
            filtro_global = {"$and": [filtro_base, {"is_resumo_global": "true"}]} if filtro_base else {"is_resumo_global": "true"}
            
            res_livros = self.db_books.find_similar(
                text=pergunta_usuario,
                top_k=1, # O resumo global é um bloco único pré-computado
                where_filter=filtro_global
            )
        else:
            # Busca por similaridade tradicional (A Lupa) nos livros marcados
            res_livros = self.db_books.find_similar(
                text=pergunta_usuario,
                top_k=top_k_busca,
                where_filter=filtro_base if filtro_base else None
            )

        # Processamento dos chunks de livros retornados
        if res_livros and res_livros.get('ids') and res_livros['ids'][0]:
            encontrou_algo = True
            contexto_str += "=== TRECHOS DOS LIVROS/ARTIGOS ===\n"
            
            for doc, meta in zip(res_livros['documents'][0], res_livros['metadatas'][0]):
                nome_doc = meta.get('nome', 'Livro Desconhecido')
                pagina_doc = meta.get('pagina', meta.get('numero_pagina', 'S/P'))
                
                contexto_str += f"[FONTE: {nome_doc}, p. {pagina_doc}]\n{doc}\n\n"
                
                # Alimenta o visualizador da direita do app.py
                self.fontes_utilizadas.append({
                    "nome": f"{nome_doc} - p. {pagina_doc}",
                    "texto": doc
                })

        # ------------------------------------------------------------------
        # 📝 PASSO 3: BUSCA NO OBSIDIAN (Se ativado)
        # ------------------------------------------------------------------
        if incluir_obsidian:
            res_obsidian = self.db_obsidian.find_similar(
                text=pergunta_usuario,
                top_k=top_k_busca
            )
            
            if res_obsidian and res_obsidian.get('ids') and res_obsidian['ids'][0]:
                encontrou_algo = True
                contexto_str += "=== NOTAS DO OBSIDIAN ===\n"
                
                ids_obsidian = res_obsidian['ids'][0]
                metas_obsidian = res_obsidian['metadatas'][0]
                notas_vistas = set()
                
                from pathlib import Path
                
                for meta, id_nota in zip(metas_obsidian, ids_obsidian):
                    caminho_real = meta.get('path', meta.get('caminho', meta.get('source', '')))
                    
                    if caminho_real and caminho_real not in notas_vistas:
                        notas_vistas.add(caminho_real)
                        nome_real = Path(caminho_real).add if hasattr(Path(caminho_real), 'stem') else Path(caminho_real).stem
                        nome_real = Path(caminho_real).stem
                        
                        try:
                            with open(caminho_real, 'r', encoding='utf-8') as f:
                                texto_completo = f.read()
                                texto_limpo = texto_completo.split("---")[0].strip() if "---" in texto_completo else texto_completo
                        except Exception:
                            texto_limpo = "(Erro ao carregar o conteúdo da nota)"
                        
                        contexto_str += f"\n--- INÍCIO DA NOTA: {nome_real} ---\n{texto_limpo}\n--- FIM DA NOTA ---\n"
                        
                        self.notas_contexto_hibrido.append({
                            "nome": nome_real,
                            "caminho": caminho_real
                        })

        # ------------------------------------------------------------------
        # 🛑 PASSO 4: VALIDAÇÃO DE CONTEXTO E HISTÓRICO
        # ------------------------------------------------------------------
        if not encontrou_algo and modo_estrito:
            yield "Os textos fornecidos não abordam este assunto. Não há dados locais suficientes para responder em Modo Estrito."
            return
        elif not encontrou_algo:
            contexto_str = "Nenhum contexto encontrado no banco de dados local."

        historico_str = ""
        if historico:
            historico_str = "HISTÓRICO RECENTE DA CONVERSA:\n"
            for msg in historico[-4:]:
                remetente = "USUÁRIO" if msg["role"] == "user" else "ASSISTENTE"
                historico_str += f"{remetente}: {msg.get('content', '')}\n"
            historico_str += "\n"

        # ------------------------------------------------------------------
        # 🤖 PASSO 5: CONFIGURAÇÃO DE PROMPTS E STREAMING FINAL
        # ------------------------------------------------------------------
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