import json
import os
from pathlib import Path
from litellm import completion 
from src.config import carregar_configuracoes 

def gerar_e_salvar_resumo(nome_livro: str, caminho_json_extraido: Path) -> str:
    """
    Lê o texto extraído do PDF, pede para a LLM criar um resumo global estruturado,
    e salva esse resumo na pasta books_data/summaries/.
    """
    pasta_resumos = Path("books_data/summaries")
    pasta_resumos.mkdir(parents=True, exist_ok=True)
    caminho_resumo = pasta_resumos / f"RESUMO_{nome_livro}.txt"

    if caminho_resumo.exists():
        with open(caminho_resumo, "r", encoding="utf-8") as f:
            return f.read()

    with open(caminho_json_extraido, "r", encoding="utf-8") as f:
        dados_livro = json.load(f)
    
    texto_completo = ""
    
    # 1. Primeiro acessamos a lista que está dentro da chave "paginas"
    # Usamos .get() com uma lista vazia [] como fallback de segurança
    lista_paginas = dados_livro.get("paginas", [])
    
    # 2. Agora sim iteramos sobre os dicionários de cada página
    for pagina in lista_paginas:
        texto_completo += pagina.get("texto", "") + "\n"

    modelo_ia = os.getenv("LLM_MODEL", "gemini/gemini-3.1-flash-lite")

    # 1. PROMPT DO SISTEMA (A Persona)
    prompt_sistema = """
    Você é um pesquisador sênior e analista de dados especialista em sintetizar documentos complexos. 
    Seu objetivo é extrair a essência de livros e artigos com precisão absoluta, sem perder detalhes cruciais.
    Sempre estruture suas respostas de forma lógica, usando Markdown, subtítulos claros e marcadores (bullet points) quando necessário.
    """

    # 2. PROMPT DO USUÁRIO (A Tarefa e os Dados)
    prompt_usuario = f"""
    Leia o texto abaixo. Identifique o tipo de documento (artigo, livro técnico ou ficção) e crie um resumo abrangente seguindo a estrutura correspondente:
    
    - PARA ARTIGOS CIENTÍFICOS:
    1. Resumo do Artigo
    2. Objetivo Principal
    3. Metodologia (se aplicável)
    4. Principais Resultados / Ideias Centrais
    5. Conclusão e pontos relevantes

    - PARA LIVROS TÉCNICOS/ACADÊMICOS:
    1. Tema Central do Livro
    2. Principais Capítulos e Ideias
    3. Aplicações Práticas ou Exemplos
    4. Pontos específicos de interesse para profissionais da área
    5. Conclusão e Relevância

    - PARA FICÇÃO:
    1. Resumo da Trama
    2. Personagens Principais
    3. Desenvolvimento da história em seus principais pontos
    4. Resumo das capítulos e eventos-chave
    5. Conclusão, reflexão e Mensagem Final
    
    - OBSERVAÇÃO IMPORTANTE PARA TEXTOS DE FICÇÃO COM CONTEÚDO VIOLENTO OU SENSÍVEL:
    Ignore descrições gráficas de violência e foque exclusivamente em:
    1. A estrutura dos capítulos e o arco narrativo.
    2. O desenvolvimento psicológico dos personagens e seus dilemas morais.
    3. A atmosfera, o estilo de escrita e a temática da obra (ex: horror psicológico, suspense).
    4. Resumo da trama (sem detalhar cenas violentas específicas).

    TEXTO PARA RESUMIR:
    {texto_completo[:100000]}
    """

    resposta = completion(
        model=modelo_ia,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        temperature=0.2, 
        stream=False     
    )

    # Captura a resposta da IA
    resumo_gerado = resposta.choices[0].message.content

    # --- O TRATAMENTO DE ERRO (PULO DO GATO) ---
    if resumo_gerado is None:
        print(f"Aviso: A IA recusou-se a resumir '{nome_livro}' (Possível bloqueio de segurança).")
        resumo_gerado = "RESUMO INDISPONÍVEL.\n\nA Inteligência Artificial não pôde gerar o resumo para este documento. Isso geralmente ocorre quando a API bloqueia a resposta devido a filtros de segurança internos (ex: o livro contém linguagem de violência, terror, ou temas explícitos que violam as políticas do modelo de IA)."

    # Grava o resultado (agora com segurança de que sempre será uma string)
    with open(caminho_resumo, "w", encoding="utf-8") as f:
        f.write(resumo_gerado)

    return resumo_gerado