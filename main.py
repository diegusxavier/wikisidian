from src.config import VAULT_PATH
from src.utils.file_handler import get_all_md_files, read_file_content

def main():
    print("="*50)
    print(f"🔍 Iniciando varredura no cofre: {VAULT_PATH}")
    print("="*50)
    
    # Executa a função para pegar os arquivos
    arquivos_md = get_all_md_files(VAULT_PATH)

    arquivos_md.sort()  # Ordena a lista de arquivos para uma visualização mais organizada
    
    if not arquivos_md:
        print("Nenhum arquivo .md encontrado ou o caminho está incorreto.")
        return

    print(f"\nTotal de arquivos encontrados: {len(arquivos_md)}")
    print("\nLista de arquivos (a pasta __TEMP__ NÃO deve aparecer aqui):")
    
    for arquivo in arquivos_md:
        # relative_to deixa o caminho mais limpo na tela
        caminho_limpo = arquivo.relative_to(VAULT_PATH)
        print(f"📄 - {caminho_limpo}")
        
    print("\n" + "="*50)
    
    # Testando a leitura apenas do primeiro arquivo para não poluir a tela
    primeiro_arquivo = arquivos_md[0]
    print(f"📖 Testando leitura do primeiro arquivo: {primeiro_arquivo.name}")
    conteudo = read_file_content(primeiro_arquivo)
    
    # Pega apenas os primeiros 100 caracteres para checar se leu bem
    resumo_texto = conteudo[:100].replace('\n', ' ')
    print(f"Prévia do texto: '{resumo_texto}...'")
    print("="*50)

# Este é o nosso ponto de entrada seguro!
if __name__ == '__main__':
    main()