from src.config import VAULT_PATH
from src.utils.file_handler import get_all_md_files

def main():
    print("="*60)
    print("🚑 Iniciando Protocolo de Limpeza (Desfazendo links da IA)")
    print("="*60)
    
    arquivos_md = get_all_md_files(VAULT_PATH)
    if not arquivos_md:
        print("Nenhum arquivo encontrado no cofre.")
        return
        
    marcador = "### Notas Relacionadas (IA)"
    # Como adicionamos uma quebra de linha e uma linha horizontal (---) antes do marcador,
    # vamos procurar por esse bloco inteiro para não deixar lixo para trás.
    divisor_completo = f"\n\n---\n{marcador}"
    
    notas_limpas = 0
    
    for arquivo in arquivos_md:
        try:
            conteudo = arquivo.read_text(encoding='utf-8')
            
            # Se a nota tem o marcador, ela foi alterada pela IA
            if marcador in conteudo:
                # O .split() divide o texto em uma lista. 
                # A parte [0] é tudo que vem ANTES do divisor (ou seja, o SEU texto original).
                if divisor_completo in conteudo:
                    texto_restaurado = conteudo.split(divisor_completo)[0]
                else:
                    # Fallback de segurança caso a quebra de linha esteja um pouco diferente
                    texto_restaurado = conteudo.split(marcador)[0].rstrip()
                    if texto_restaurado.endswith("---"):
                        texto_restaurado = texto_restaurado[:-3].rstrip()
                
                # Sobrescreve o arquivo apenas com o seu texto original
                arquivo.write_text(texto_restaurado, encoding='utf-8')
                notas_limpas += 1
                print(f"🧹 Limpo: {arquivo.name}")
                
        except Exception as e:
            print(f"❌ Erro ao limpar '{arquivo.name}': {e}")
            
    print("\n" + "="*60)
    print(f"✅ Ufa! {notas_limpas} arquivos foram restaurados com sucesso.")
    print("="*60)

if __name__ == '__main__':
    main()