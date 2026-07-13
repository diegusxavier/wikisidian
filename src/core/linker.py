import re
from pathlib import Path
from src.core.embedder import VectorStore
from src.config import MARCADOR_IA

class ObsidianLinker:
    # Classe que gerencia a injeção de links no Obsidian. Ela lê o conteúdo da nota, identifica links já existentes, busca novas notas similares no banco vetorial e atualiza o arquivo sem duplicar informações.
    def __init__(self, vector_store: VectorStore):
        # O Linker precisa receber o "cérebro" (banco vetorial) já carregado
        self.vs = vector_store
        
        # Um marcador limpo e seguro para separar o seu texto da área da IA
        self.marcador = MARCADOR_IA
        
        # DEFINIMOS O NOSSO NÍVEL DE RIGOR AQUI (Limiar de Distância)
        # O ChromaDB devolve a distância entre as notas (0.0 é idêntico, 1.0+ é muito diferente).
        # Se a distância for MAIOR que este valor, a IA descarta a sugestão, 
        # mesmo que seja a "mais próxima" encontrada. 
        # Ajuste: 0.4 é bastante rigoroso (exige muita similaridade), 0.7 é mais permissivo.
        self.distancia_maxima = 0.5 

    def _format_backlink(self, note_name: str) -> str:
        """
        Remove a extensão .md e formata no padrão de link do Obsidian.
        Ex: 'Arquitetura.md' vira '- [[Arquitetura]]'
        """
        nome_limpo = note_name.replace(".md", "")
        return f"- [[{nome_limpo}]]"

    def inject_links(self, file_path: Path, top_k: int = 3) -> bool:
        """
        Lê a nota, identifica links já existentes (Lista Negra), busca novas notas similares,
        aplica o filtro de rigor matemático e atualiza o arquivo sem duplicar informações.
        """
        try:
            # Lê o conteúdo de forma segura, mantendo a acentuação correta
            conteudo = file_path.read_text(encoding='utf-8')
            
            # Se o arquivo estiver vazio, ignoramos e não fazemos nada
            if not conteudo.strip():
                return False

            # =================================================================
            # PASSO 1: Separar o texto original dos links já gerados anteriormente
            # =================================================================
            if self.marcador in conteudo:
                # Divide o arquivo em dois pedaços usando o marcador
                partes = conteudo.split(self.marcador)
                texto_original = partes[0].strip() # O texto puro que você escreveu
                texto_links = partes[1]            # Os links que a IA gerou no passado
                
                # O Regex (re) procura tudo que está dentro de [[ ]] na área de links.
                # Isso cria a nossa "Lista Negra", evitando que a IA recomende a mesma nota duas vezes.
                nomes_extraidos = re.findall(r"\[\[(.*?)\]\]", texto_links)
                # Adiciona o ".md" de volta para o formato bater com o nome real do arquivo
                links_existentes = set(f"{nome}.md" for nome in nomes_extraidos)
            else:
                # Se não tem marcador, é a primeira vez que a IA lê esta nota.
                texto_original = conteudo.strip()
                links_existentes = set()

            # =================================================================
            # PASSO 2: Buscar no banco vetorial
            # =================================================================
            # Passamos APENAS o seu texto original para não poluir a bússola da IA.
            # Pedimos 15 resultados para ter uma boa margem de opções caso o filtro rejeite muitas.
            resultados = self.vs.find_similar(texto_original, top_k=15)
            
            # Extraímos os nomes dos arquivos encontrados
            ids_encontrados = resultados['ids'][0]
            # Extraímos também as notas matemáticas (distâncias) de cada arquivo
            distancias = resultados['distances'][0] 
            
            # =================================================================
            # PASSO 3: Filtrar as novas recomendações (Rigor e Lista Negra)
            # =================================================================
            novas_recomendacoes = []
            
            # O 'zip' é uma ferramenta do Python que nos permite percorrer duas listas
            # ao mesmo tempo (o nome da nota e a distância daquela nota).
            for nome_nota, distancia in zip(ids_encontrados, distancias):
                
                # Regra de Ouro: Só aceitamos a nota se a distância for MENOR que o limite!
                if distancia <= self.distancia_maxima:
                    
                    # Além da distância, verificamos se não é a própria nota e se não está na Lista Negra
                    if nome_nota != file_path.name and nome_nota not in links_existentes:
                        novas_recomendacoes.append(nome_nota)
                else:
                    # Como os resultados do ChromaDB vêm ordenados (do melhor para o pior),
                    # se batermos em uma distância ruim, sabemos que todas as próximas também serão ruins.
                    # O 'break' interrompe a busca mais cedo para economizar processamento.
                    break 

            # Limitamos para adicionar apenas a quantidade desejada (ex: 3 links por rodada)
            novas_recomendacoes = novas_recomendacoes[:top_k]

            # Se depois de todos os filtros não sobrou nenhuma nota boa, não alteramos o arquivo
            if not novas_recomendacoes:
                return False

            # =================================================================
            # PASSO 4: Montar o texto final e reescrever no arquivo
            # =================================================================
            bloco_novos_links = ""
            for nota in novas_recomendacoes:
                bloco_novos_links += f"{self._format_backlink(nota)}\n"

            if self.marcador in conteudo:
                # Se a nota já tinha a área de links, nós apenas grudamos os novos lá no finalzinho
                novo_conteudo = conteudo.rstrip() + "\n" + bloco_novos_links
            else:
                # Se for a primeira vez, criamos a linha divisória elegante, o marcador e os links
                novo_conteudo = conteudo.rstrip() + f"\n\n---\n{self.marcador}\n{bloco_novos_links}"

            # Reescreve o arquivo no disco rígido com as atualizações
            file_path.write_text(novo_conteudo, encoding='utf-8')
            
            return True
            
        except Exception as e:
            # Caso algum arquivo esteja corrompido ou bloqueado, o programa não trava inteiro
            print(f"Erro ao processar '{file_path.name}': {e}")
            return False