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
    caminho_resumo = pasta_resumos / f"{nome_livro}_resumo.txt"

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
    1. Objetivo Principal
    2. Metodologia (se aplicável)
    3. Principais Resultados / Ideias Centrais
    4. Conclusão

    - PARA LIVROS TÉCNICOS/ACADÊMICOS:
    1. Tema Central do Livro
    2. Principais Capítulos e Ideias
    3. Conclusão e Relevância

    - PARA FICÇÃO:
    1. Resumo da Trama
    2. Personagens Principais
    3. Desenvolvimento da história
    4. Conclusão, reflexão e Mensagem Final
    
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

    resumo_gerado = resposta.choices[0].message.content

    with open(caminho_resumo, "w", encoding="utf-8") as f:
        f.write(resumo_gerado)

    return resumo_gerado