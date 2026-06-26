import re
from pathlib import Path
from src.core.embedder import VectorStore

class ObsidianLinker:
    def __init__(self, vector_store: VectorStore):
        self.vs = vector_store
        # Um marcador mais limpo para facilitar a divisão do texto
        self.marcador = "### Notas Relacionadas (IA)"

    def _format_backlink(self, note_name: str) -> str:
        nome_limpo = note_name.replace(".md", "")
        return f"- [[{nome_limpo}]]"

    def inject_links(self, file_path: Path, top_k: int = 3) -> bool:
        """
        Lê a nota, identifica links já existentes, busca novas notas similares 
        e atualiza o arquivo sem duplicar informações.
        """
        try:
            conteudo = file_path.read_text(encoding='utf-8')
            
            if not conteudo.strip():
                return False

            # Passo 1: Separar o texto original dos links já gerados anteriormente
            if self.marcador in conteudo:
                # Divide o arquivo em dois pedaços usando o marcador
                partes = conteudo.split(self.marcador)
                texto_original = partes[0].strip() # Seu texto
                texto_links = partes[1]            # Os links antigos
                
                # O Regex (re) procura tudo que está dentro de [[ ]]
                nomes_extraidos = re.findall(r"\[\[(.*?)\]\]", texto_links)
                # Adiciona o ".md" de volta para criar nossa "Lista Negra"
                links_existentes = set(f"{nome}.md" for nome in nomes_extraidos)
            else:
                texto_original = conteudo.strip()
                links_existentes = set()

            # Passo 2: Buscar no banco vetorial
            # Buscamos APENAS pelo seu texto original (para os links antigos não confundirem a IA)
            # Pedimos 15 resultados (é instantâneo) para ter margem de sobra para o filtro
            resultados = self.vs.find_similar(texto_original, top_k=15)
            ids_encontrados = resultados['ids'][0]
            
            # Passo 3: Filtrar as novas recomendações
            novas_recomendacoes = []
            for nome_nota in ids_encontrados:
                # Se não for a própria nota E não estiver na lista negra, nós aceitamos!
                if nome_nota != file_path.name and nome_nota not in links_existentes:
                    novas_recomendacoes.append(nome_nota)

            # Limitamos para adicionar apenas o número desejado por vez (ex: 3)
            novas_recomendacoes = novas_recomendacoes[:top_k]

            # Se não sobrou nenhuma recomendação nova, não fazemos nada
            if not novas_recomendacoes:
                return False

            # Passo 4: Montar o texto final e salvar
            bloco_novos_links = ""
            for nota in novas_recomendacoes:
                bloco_novos_links += f"{self._format_backlink(nota)}\n"

            if self.marcador in conteudo:
                # Se já existia a seção, apenas grudamos os links novos lá no final
                novo_conteudo = conteudo.rstrip() + "\n" + bloco_novos_links
            else:
                # Se for a primeira vez, criamos a linha divisória, o marcador e os links
                novo_conteudo = conteudo.rstrip() + f"\n\n---\n{self.marcador}\n{bloco_novos_links}"

            # Reescreve o arquivo com a atualização
            file_path.write_text(novo_conteudo, encoding='utf-8')
            
            return True
            
        except Exception as e:
            print(f"Erro ao processar '{file_path.name}': {e}")
            return False