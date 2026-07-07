# 🏛️ Wikisidian

O **Wikisidian** é um ecossistema de gerenciamento de conhecimento local e inteligente que transforma o seu cofre do Obsidian (`Vault`) em uma base de conhecimento ativa e totalmente interativa. Através de técnicas de **RAG (Retrieval-Augmented Generation)**, o sistema permite que você converse com suas notas pessoais em uma interface web moderna, além de gerenciar e injetar conexões (*backlinks*) automaticamente entre seus arquivos.

---

## ✨ Principais Funcionalidades

### 💬 Chat RAG (Workspace de Tela Dividida)
* **Respostas com Streaming:** Respostas fluidas geradas palavra por palavra (efeito máquina de escrever) utilizando LLMs locais (via Ollama) ou comerciais (como Gemini).
* **Filtro Avançado de Contexto:** A IA consulta o banco vetorial local e responde utilizando *apenas* as informações contidas em suas notas.
* **Visualizador Sticky com Suporte a Markdown:** Exibição das notas originais utilizadas como fonte em uma coluna lateral fixa. Ao rolar o chat, a nota permanece ancorada na tela para leitura simultânea com suporte a equações matemáticas e tabelas.

### 🔗 Gestor de Conexões e Filtros
* **Injeção Automática de Backlinks:** Varre o cofre em busca de notas semanticamente semelhantes e injeta conexões dinamicamente ao fim de cada arquivo.
* **Filtros por Interface (Checkboxes):** Menu lateral expansível que lê os subdiretórios do seu cofre em tempo real e permite marcar quais pastas devem ser ignoradas pela IA através de caixas de seleção.
* **Botão de Pânico (Undo):** Permite reverter e remover completamente todas as assinaturas e links inseridos pela IA, restaurando seus arquivos markdown originais com segurança.
* **Configuração Persistente:** O caminho do cofre e as pastas ignoradas são salvos de forma centralizada e automática em um arquivo JSON local.

---

## 📂 Estrutura de Pastas do Projeto

O projeto segue uma arquitetura modular limpa e orientada a responsabilidades isoladas:

```text
wikisidian/
├── .streamlit/
│   └── config.toml         # Configurações de inicialização e nível de log do Streamlit
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── embedder.py     # Gerenciamento do banco de dados vetorial (ChromaDB) e embeddings
│   │   ├── linker.py       # Algoritmo de busca semântica e injeção de conexões nas notas
│   │   ├── rag_cli.py      # Motor de orquestração do RAG e interface com LLMs via LiteLLM
│   │   └── scanner.py      # Serviços de varredura profunda de arquivos
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_handler.py # Utilitários de leitura, escrita e filtragem dinâmica de arquivos .md
│   │   └── undo_links.py   # Lógica reversora para remoção das assinaturas da IA
│   ├── __init__.py
│   └── config.py           # Definição de constantes globais e gerenciamento do settings.json
├── app.py                  # Frontend e lógica de interface da aplicação web (Streamlit)
├── main.py                 # Launcher (ponto de entrada único para inicialização do ecossistema)
├── requirements.txt        # Dependências de bibliotecas do Python
└── settings.json           # Arquivo gerado dinamicamente para persistência de configurações
```

## 🛠️ Como Utilizar
Pré-requisitos
Python 3.10 ou superior instalado.

Se optar por rodar modelos locais, garanta que o Ollama esteja em execução com o modelo de sua escolha (ex: llama3).

### 1. Configuração do Ambiente
Clone o repositório, crie seu ambiente virtual (venv) e instale as dependências necessárias:

```bash
# Ative seu ambiente virtual (Windows)
venv\Scripts\activate

## Instale os pacotes necessários
pip install -r requirements.txt
```

### 2. Variáveis de Ambiente
Crie um arquivo .env na raiz do projeto com as chaves necessárias para os modelos que deseja utilizar (consulte o .env.example para referência). Exemplo para o Gemini:

```bash
GEMINI_API_KEY=sua_chave_aqui
LLM_MODEL=gemini/gemini-3.1-flash-lite
```


### 3. Inicialização
Para iniciar a aplicação, utilize o ponto de entrada oficial do ecossistema:

```bash
python main.py
```

O comando executará o script launcher, que abrirá automaticamente o seu navegador padrão na interface gráfica do Wikisidian.

## 🚀 Como Funciona no Dia a Dia

- Configuração Inicial: No menu lateral esquerdo da tela, insira o caminho absoluto para a pasta do seu cofre do Obsidian. O sistema fará a varredura e a indexação automática instantaneamente.

- Definição de Filtros: Expanda o menu "🚫 Pastas Ignoradas", selecione as pastas onde você não quer que a IA mexa (como pastas de anexos, templates ou notas temporárias) e clique em Salvar Filtros.

- Conversação: Faça uma pergunta na aba 💬 Chat RAG. Use os botões dentro do painel "📚 Ver notas originais" para abrir o conteúdo original na lateral da tela.

- Geração de Grafos Físicos: Mude para a aba 🔗 Gestor de Conexões, determine o número de conexões semânticas desejadas no seletor e clique em Iniciar Injeção de Links para ver os backlinks surgindo no seu Obsidian em tempo real.