import os
from pathlib import Path
from typing import Generator
from dotenv import load_dotenv
from litellm import completion
from src.core.embedder import VectorStore
from src.config import MARCADOR_IA
from typing import Generator

# Carrega as variaveis do arquivo .env para a memoria
load_dotenv()

class WikisidianChat:
    def __init__(self, vector_store: VectorStore, vault_path: Path):
        self.vs = vector_store
        self.vault_path = vault_path
        
        # Busca o modelo definido no .env. Se nao achar, usa o Gemini como padrao.
        self.modelo = os.getenv("LLM_MODEL", "gemini/gemini-3.1-flash-lite")
        self.notas_contexto = [] # Guarda o rastro das notas utilizadas

    def _obter_texto_da_nota(self, caminho_completo_str: str) -> str:
        """
        Em vez de tentar juntar a raiz do cofre com o nome do arquivo,
        esta funcao agora recebe o caminho exato e absoluto (incluindo subpastas)
        que foi resgatado da memoria do ChromaDB.
        """
        caminho = Path(caminho_completo_str)
        try:
            return caminho.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Aviso: Erro ao ler arquivo no caminho {caminho}: {e}")
            return ""

    def perguntar(self, pergunta_usuario: str, top_k: int = 6, modo_estrito: bool = True, historico: list = None) -> Generator[str, None, None]:
        """
        1. Procura as notas mais relevantes no ChromaDB.
        2. Monta o contexto limpo usando os caminhos reais.
        3. Define o Prompt (Estrito ou Híbrido) com base na escolha do utilizador.
        4. Envia para o modelo escolhido via LiteLLM, incluindo o histórico.
        """
        resultados = self.vs.find_similar(pergunta_usuario, top_k=top_k)
        ids_encontrados = resultados['ids'][0]
        metadados_encontrados = resultados['metadatas'][0]

        if not ids_encontrados and modo_estrito:
            yield "Desculpe, não encontrei nenhuma nota relevante no seu cofre sobre esse assunto."
            return

        # 2. Montagem do Contexto
        contexto_str = ""
        self.notas_contexto = [] 

        if ids_encontrados:
            for nome_nota, metadado in zip(ids_encontrados, metadados_encontrados):
                caminho_real = metadado.get('path', metadado.get('source', ''))
                texto = self._obter_texto_da_nota(caminho_real)
                
                if texto:
                    texto_limpo = texto.split(MARCADOR_IA)[0].strip()
                    contexto_str += f"\n--- INICIO DA NOTA: {nome_nota} ---\n{texto_limpo}\n--- FIM DA NOTA ---\n"
                    self.notas_contexto.append({
                        "nome": nome_nota,
                        "caminho": caminho_real
                    })
        else:
            contexto_str = "Nenhuma nota encontrada no cofre sobre este tópico específico."

        # --- NOVO: Tratamento do Histórico Conversacional ---
        historico_str = ""
        if historico:
            historico_str = "HISTÓRICO RECENTE DA CONVERSA (Para contexto):\n"
            # Pegamos apenas as últimas 4 mensagens (2 interações) para poupar tokens
            for msg in historico[-4:]:
                remetente = "USUÁRIO" if msg["role"] == "user" else "ASSISTENTE"
                # Removemos a lista de fontes do histórico para não poluir os tokens
                conteudo = msg.get("content", "")
                historico_str += f"\n{remetente}: {conteudo}\n"
            historico_str += "\n"

        # 3. O Prompt Dinâmico
        if modo_estrito:
            temperatura = 0.2
            prompt_sistema = """Voce e o Wikisidian, um assistente pessoal.
            REGRAS OBRIGATORIAS:
            1. Responda APENAS com base no CONTEXTO fornecido.
            2. Se a informacao nao estiver presente nas notas fornecidas, responda EXATAMENTE: "Nao encontrei informacoes sobre isso nas suas anotacoes."
            3. Nao utilize nenhum conhecimento externo.
            Ao final da sua resposta, adicione uma secao chamada 'Fontes Utilizadas:' e liste as notas."""
        else:
            temperatura = 0.6 
            prompt_sistema = """Você é o Wikisidian, um assistente de conhecimento estilo NotebookLM.
            REGRAS OBRIGATORIAS:
            1. Você receberá um CONTEXTO com as notas do usuário. Priorize sempre essas informações.
            2. Se a resposta completa ou parcial NÃO estiver no contexto, você DEVE usar o seu conhecimento externo para expandir a resposta, conectar conceitos ou preencher lacunas.
            3. TRANSPARÊNCIA: Se utilizar conhecimento externo, avise claramente no meio do texto (ex: "Expandindo com conhecimentos gerais...").
            4. Seja inteligente com o HISTÓRICO: se o usuário disser "e como isso funciona?", procure a que "isso" ele se refere no histórico recente.
            5. Ao final da sua resposta, adicione uma seção chamada 'Notas Relacionadas:' e liste os nomes das notas do contexto."""

        # Injetamos o histórico antes da pergunta atual
        prompt_usuario = f"""CONTEXTO (Notas do usuario):\n{contexto_str}\n\n{historico_str}PERGUNTA DO USUARIO: {pergunta_usuario}\n"""

        # 4. A Chamada à IA
        print(f"Wikisidian a processar a pergunta (Estrito: {modo_estrito})...")
        try:
            # --- DEBUG: Ver o que a IA recebe ---
            print("\n" + "="*40)
            print("CONTEXTO E HISTÓRICO ENVIADO PARA A IA:")
            print(prompt_usuario) # O prompt_usuario já contém contexto + histórico
            print("="*40 + "\n")

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