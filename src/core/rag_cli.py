import os
from pathlib import Path
from dotenv import load_dotenv
from litellm import completion
from src.core.embedder import VectorStore
from src.config import MARCADOR_IA

# Carrega as variaveis do arquivo .env para a memoria
load_dotenv()

class WikisidianChat:
    def __init__(self, vector_store: VectorStore, vault_path: Path):
        self.vs = vector_store
        self.vault_path = vault_path
        
        # Busca o modelo definido no .env. Se nao achar, usa o Gemini como padrao.
        self.modelo = os.getenv("LLM_MODEL", "gemini/gemini-3.1-flash-lite")

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

    def perguntar(self, pergunta_usuario: str, top_k: int = 6) -> str:
        """
        1. Procura as notas mais relevantes no ChromaDB.
        2. Monta o contexto limpo usando os caminhos reais das subpastas.
        3. Envia para o modelo escolhido via LiteLLM.
        """
        # 1. Busca Matematica no ChromaDB
        resultados = self.vs.find_similar(pergunta_usuario, top_k=top_k)
        
        ids_encontrados = resultados['ids'][0]
        
        # AQUI ESTA A MAGICA DAS SUBPASTAS:
        # Extraimos as etiquetas de metadados que acompanham as notas encontradas.
        # Retorna uma lista de dicionarios, ex: [{'path': 'G:/.../Nota.md'}, ...]
        metadados_encontrados = resultados['metadatas'][0]

        if not ids_encontrados:
            return "Desculpe, nao encontrei nenhuma nota relevante no seu cofre sobre esse assunto."

        # 2. Montagem do Contexto
        contexto_str = ""
        notas_utilizadas = []

        # O zip permite percorrer o nome da nota e a sua etiqueta de caminho ao mesmo tempo
        for nome_nota, metadado in zip(ids_encontrados, metadados_encontrados):
            
            # Pegamos o caminho completo exato que salvamos no banco de dados
            caminho_real = metadado['path']
            
            # Passamos esse caminho exato para a nossa funcao de leitura
            texto = self._obter_texto_da_nota(caminho_real)
            
            if texto:
                # Removemos a area de links gerada pelo programa para manter o contexto puro
                texto_limpo = texto.split(MARCADOR_IA)[0].strip()
                
                contexto_str += f"\n--- INICIO DA NOTA: {nome_nota} ---\n"
                contexto_str += f"{texto_limpo}\n"
                contexto_str += f"--- FIM DA NOTA ---\n"
                notas_utilizadas.append(nome_nota)

        # 3. O Prompt Estruturado
        prompt_sistema = """Voce e o Wikisidian, um assistente pessoal.
        REGRAS OBRIGATORIAS:
        1. Responda APENAS com base no CONTEXTO fornecido.
        2. Se a informacao nao estiver presente nas notas fornecidas, responda EXATAMENTE: "Nao encontrei informacoes sobre isso nas suas anotacoes."
        3. Nao utilize nenhum conhecimento externo, mesmo que voce saiba a resposta.
        4. Se o contexto for irrelevante para a pergunta, diga que nao possui informacoes sobre o tema.
        Ao final da sua resposta, adicione uma secao chamada 'Fontes Utilizadas:' e liste as notas."""
        
        prompt_usuario = f"""CONTEXTO (Notas do usuario):
        {contexto_str}

PERGUNTA DO USUARIO: {pergunta_usuario}
"""

        # 4. A Chamada a IA
        print("Wikisidian a processar a sua pergunta...")
        try:
            resposta = completion(
                model=self.modelo,
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario}
                ],
                temperature=0.3 # Temperatura baixa para garantir respostas factuais
            )
            
            texto_resposta = resposta.choices[0].message.content
            return texto_resposta
            
        except Exception as e:
            return f"Erro ao comunicar com a IA: {e}"