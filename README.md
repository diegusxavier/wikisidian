# Wikisidian
```
wikisidian/
│
├── src/                    # Código fonte do projeto
│   ├── __init__.py
│   ├── config.py           # Configurações (caminho do cofre do Obsidian, chaves, etc)
│   ├── core/               # Lógica principal de negócio
│   │   ├── __init__.py
│   │   ├── scanner.py      # Varre o cofre e identifica quais notas precisam ser lidas
│   │   ├── embedder.py     # Transforma os textos em vetores matemáticos
│   │   ├── linker.py       # Compara os vetores e injeta os backlinks no fim dos arquivos .md
│   │   └── rag_cli.py      # Lógica do chat (Perguntas e Respostas) para o futuro
│   └── utils/              # Funções auxiliares genéricas
│       ├── __init__.py
│       └── file_handler.py # Funções seguras para ler e reescrever os arquivos .md
│
├── .gitignore              # Diz ao Git o que NÃO rastrear
├── requirements.txt        # Onde listaremos as bibliotecas (ex: chromadb, etc)
├── README.md               # Apresentação e documentação do seu projeto
└── main.py                 # O maestro do sistema, que vai chamar os scripts na ordem certa
```
