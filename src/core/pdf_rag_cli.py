import os
from dotenv import load_dotenv
from litellm import completion
from typing import Generator
from src.core.embedder import VectorStore

# Carrega as variaveis do arquivo .env
load_dotenv()

class HybridRagEngine:
    def __init__(self):
        # Conecta nas duas gavetas
        self.db_books = VectorStore(collection_name="pdf_books")
        self.db_obsidian = VectorStore(collection_name="obsidian_notes") # Confirme se é este o nome da sua coleção de notas
        self.modelo = os.getenv("LLM_MODEL", "gemini/gemini-3.1-flash-lite")

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
        
        # NOVO: Resetamos as fontes a cada nova pergunta para guardar os chunks
        self.fontes_utilizadas = [] 

        # ==========================================
        # 1. BUSCA NOS LIVROS
        # ==========================================
        filtro_livro = None
        if book_titles:
            if len(book_titles) == 1:
                filtro_livro = {"titulo": book_titles[0]}
            else:
                filtro_livro = {"titulo": {"$in": book_titles}}

        res_livros = self.db_books.find_similar(
            text=pergunta_usuario, 
            top_k=top_k, 
            where_filter=filtro_livro
        )

        if res_livros['ids'] and res_livros['ids'][0]:
            encontrou_algo = True
            contexto_str += "=== TRECHOS DE LIVROS ===\n"
            for doc, meta in zip(res_livros['documents'][0], res_livros['metadatas'][0]):
                titulo = meta.get('titulo', 'Desconhecido')
                pagina = meta.get('pagina', '?')
                
                contexto_str += f"[LIVRO: {titulo} | PÁGINA: {pagina}]\n{doc}\n\n"
                
                # NOVO: Salvamos o título, a página e o texto cru do chunk!
                self.fontes_utilizadas.append({
                    "nome": f"{titulo} (p. {pagina})",
                    "texto": doc
                })
        # ==========================================
        # 2. BUSCA NO OBSIDIAN (Se ativado)
        # ==========================================
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
                
                self.notas_contexto_hibrido = []
                notas_vistas = set() # Cria um "filtro" para não repetir a mesma nota
                
                from pathlib import Path # Garante que temos a ferramenta de caminhos
                
                # Ignoramos o 'doc' do banco e focamos apenas no metadado
                for meta, id_nota in zip(metas_obsidian, ids_obsidian):
                    caminho_real = meta.get('path', meta.get('source', ''))
                    
                    # Se achou um caminho válido e essa nota ainda não foi processada
                    if caminho_real and caminho_real not in notas_vistas:
                        notas_vistas.add(caminho_real)
                        
                        nome_real = Path(caminho_real).stem # Pega só o nome do arquivo (sem o .md e sem chunk)
                        
                        # Vai até o disco e lê a nota inteira
                        try:
                            with open(caminho_real, 'r', encoding='utf-8') as f:
                                texto_completo = f.read()
                                # Opcional: Se houver links da IA no fim, podemos limpar
                                texto_limpo = texto_completo.split("---")[0].strip() if "---" in texto_completo else texto_completo
                        except Exception:
                            texto_limpo = "(Erro ao carregar o conteúdo da nota)"
                        
                        contexto_str += f"\n--- INÍCIO DA NOTA: {nome_real} ---\n{texto_limpo}\n--- FIM DA NOTA ---\n"
                        
                        # Salva o nome bonito para o botão no app.py
                        self.notas_contexto_hibrido.append({
                            "nome": nome_real,
                            "caminho": caminho_real
                        })
        # ==========================================
        # 3. VERIFICAÇÃO DE DADOS
        # ==========================================
        if not encontrou_algo and modo_estrito:
            yield "Desculpe, não encontrei nenhuma informação sobre esse assunto nos livros ou notas selecionadas."
            return
        elif not encontrou_algo:
            contexto_str = "Nenhum contexto encontrado no banco de dados local."

        # ==========================================
        # 4. TRATAMENTO DO HISTÓRICO
        # ==========================================
        historico_str = ""
        if historico:
            historico_str = "HISTÓRICO RECENTE DA CONVERSA:\n"
            for msg in historico[-4:]:
                remetente = "USUÁRIO" if msg["role"] == "user" else "ASSISTENTE"
                historico_str += f"{remetente}: {msg.get('content', '')}\n"
            historico_str += "\n"

        # ==========================================
        # 5. CONFIGURAÇÃO DO PROMPT E LLM
        # ==========================================
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