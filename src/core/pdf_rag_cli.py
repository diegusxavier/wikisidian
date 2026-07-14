import os
from dotenv import load_dotenv
from litellm import completion
from typing import Generator
from src.core.embedder import VectorStore
from pathlib import Path

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
        top_k: int = 5, 
        modo_estrito: bool = True,
        incluir_obsidian: bool = False,
        historico: list = None
    ) -> Generator[str, None, None]:
        
        contexto_str = ""
        encontrou_algo = False
        
        # Inicializa a lista de fontes utilizadas para rastrear de onde cada trecho veio
        # Inicializa a lista de fontes utilizadas para rastrear de onde cada trecho veio (Proteção da master)
        self.fontes_utilizadas = []

        # ---------------------------------------------------------
        # 🔎 PASSO 1: O ROTEADOR (Classificação de Intenção)
        # ---------------------------------------------------------
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

        print(f"🕵️ Roteador Wikisidian: Pergunta classificada como [{intencao}]")

        # A BUSCA DIRECIONADA NO CHROMADB (LIVROS/ARTIGOS)
        
        filtro_base = {}
        if book_titles:
            # Usa a sintaxe limpa da master para múltiplos títulos
            if len(book_titles) == 1:
                filtro_base = {"titulo": book_titles[0]}
            else:
                filtro_base = {"titulo": {"$in": book_titles}}

        if intencao == "GLOBAL":
            # Filtra APENAS resumos
            filtro_llm = {"$and": [filtro_base, {"tipo_dado": "resumo"}]} if filtro_base else {"tipo_dado": "resumo"}
            
            res_livros = self.db_books.find_similar(
                text=pergunta_usuario,
                top_k=1,
                where_filter=filtro_llm
            )
        else:
            # Intenção ESPECÍFICA: Filtra APENAS páginas
            filtro_llm = {"$and": [filtro_base, {"tipo_dado": "pagina"}]} if filtro_base else {"tipo_dado": "pagina"}
            
            res_livros = self.db_books.find_similar(
                text=pergunta_usuario,
                top_k=top_k, # Volta ao valor normal passado como parâmetro
                where_filter=filtro_llm
            )

        # Processamento dos chunks para a Inteligência Artificial
        if res_livros and res_livros.get('ids') and res_livros['ids'][0]:
            encontrou_algo = True
            contexto_str += "=== TRECHOS DE LIVROS ===\n"
            titulos_processados = set() 

            for doc, meta in zip(res_livros['documents'][0], res_livros['metadatas'][0]):
                titulo = meta.get('titulo', 'Desconhecido')
                tipo_dado = meta.get('tipo_dado', 'pagina') # Checa se é resumo ou pagina
                titulos_processados.add(titulo) 
                
                # Formatação condicional baseada no tipo_dado
                if tipo_dado == "resumo":
                    nome_fonte = f"📘 Resumo ({titulo})"
                    contexto_str += f"[RESUMO GERAL DO LIVRO: {titulo}]\n{doc}\n\n"
                else:
                    pagina = meta.get('pagina', '?')
                    nome_fonte = f"📄 {titulo} (p. {pagina})"
                    contexto_str += f"[LIVRO: {titulo} | PÁGINA: {pagina}]\n{doc}\n\n"
                
                # Salvamos o nome formatado e o texto cru do chunk para a UI
                self.fontes_utilizadas.append({
                    "nome": nome_fonte,
                    "texto": doc
                })

            # Injeta o Resumo Visualmente na Busca Específica
            if intencao == "ESPECIFICO":
                for titulo in titulos_processados:
                    caminho_resumo = Path(f"books_data/summaries/RESUMO_{titulo}.txt")
                    if caminho_resumo.exists():
                        with open(caminho_resumo, "r", encoding="utf-8") as f:
                            texto_resumo = f.read()
                        
                        # Anexa apenas na variável visual (não entra no contexto_str da IA)
                        self.fontes_utilizadas.append({
                            "nome": f"📘 Resumo Global ({titulo})",
                            "texto": texto_resumo
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

                ids_obsidian = res_obsidian['ids'][0]
                metas_obsidian = res_obsidian['metadatas'][0]
                notas_vistas = set()


                for meta, id_nota in zip(metas_obsidian, ids_obsidian):
                    caminho_real = meta.get('path', meta.get('caminho', meta.get('source', '')))

                    if caminho_real and caminho_real not in notas_vistas:
                        notas_vistas.add(caminho_real)
                        
                        # Nome limpo do arquivo sem a extensão (bug das duas linhas corrigido aqui)
                        nome_real = Path(caminho_real).stem

                        try:
                            with open(caminho_real, 'r', encoding='utf-8') as f:
                                texto_completo = f.read()
                                # Tenta remover o frontmatter do Obsidian (YAML)
                                texto_limpo = texto_completo.split("---")[0].strip() if "---" in texto_completo else texto_completo
                        except Exception:
                            texto_limpo = "(Erro ao carregar o conteúdo da nota)"

                        contexto_str += f"\n--- INÍCIO DA NOTA: {nome_real} ---\n{texto_limpo}\n--- FIM DA NOTA ---\n"

                        self.fontes_utilizadas.append({
                            "nome": nome_real,
                            "caminho": caminho_real
                        })

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
            1. Responda APENAS com base nos TRECHOS FORNECIDOS no contexto.
            2. REGRAS DE CITAÇÃO (OBRIGATÓRIO):
                - Se o trecho indicar [LIVRO: ... | PÁGINA: X], use o formato: (Nome do Livro, p. X).
                - Se o trecho indicar [RESUMO GERAL DO LIVRO: ...], use o formato: (Nome do Livro - Resumo Global).
                - Se o trecho vier do Obsidian, use o formato: (Nota: Nome da Nota).
            3. Se a informação não estiver presente, diga: "Os textos fornecidos não abordam este assunto".
            4. Não invente informações nem chute números de páginas."""
        else:
            temperatura = 0.6 
            prompt_sistema = """Você é um assistente de pesquisa avançado.
            REGRAS OBRIGATÓRIAS:
            1. Priorize responder com base nos TRECHOS FORNECIDOS.
            2. REGRAS DE CITAÇÃO (OBRIGATÓRIO):
                - Se o trecho indicar [LIVRO: ... | PÁGINA: X], use: (Nome do Livro, p. X).
                - Se o trecho indicar [RESUMO GERAL DO LIVRO: ...], use: (Nome do Livro - Resumo Global).
                - Se for do Obsidian, use: (Nota: Nome da Nota).
            3. CONHECIMENTO GERAL: Se a resposta não estiver nos trechos, você PODE usar seu conhecimento geral, mas DEVE avisar (ex: "Embora meus arquivos locais não mencionem isso...").
            4. Não invente citações ou referências falsas."""

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