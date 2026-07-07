import os
import sys
import subprocess
from pathlib import Path

def main():
    print("Iniciando o Wikisidian...")
    # Define o caminho do app.py na raiz do projeto
    app_path = Path(__file__).resolve().parent / "app.py"
    
    if not app_path.exists():
        print(f"Erro: Arquivo {app_path} não encontrado!")
        return

    # Executa o comando 'streamlit run app.py' usando o interpretador Python atual
    # sys.executable garante que ele use o mesmo Python do seu venv
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])
    except Exception as e:
        print(f"Erro ao iniciar a interface: {e}")

if __name__ == '__main__':
    main()