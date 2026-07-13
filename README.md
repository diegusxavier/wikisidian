# 🏛️ Wikisidian

O **Wikisidian** é um ecossistema de gerenciamento de conhecimento local e inteligente de dupla função. Ele atua como uma interface de conversação avançada e gestor para o seu cofre do Obsidian (`Vault`), além de ser um poderoso motor de ingestão e análise de livros e artigos em formato PDF. 

Através de arquiteturas robustas de **RAG (Retrieval-Augmented Generation)**, Roteamento Cognitivo e processamento de linguagem natural (via Ollama ou modelos comerciais como Gemini), o Wikisidian permite que você converse com os seus dados locais através de uma interface web moderna, além de gerenciar conexões semânticas (*backlinks*) de forma automatizada.

---

## ✨ Principais Funcionalidades

### 💬 Chat RAG com Notas em Markdown (Obsidian)
* **Conhecimento Confinado e Estrito:** A IA consulta o banco de dados vetorial local (ChromaDB) e responde baseando-se estritamente nas informações documentadas nas suas anotações do Obsidian.
* **Leitura Híbrida Inteligente:** Processa arquivos Markdown, extraindo títulos, hierarquias e conteúdos originais ignorando diretórios e metadados indesejados.
* **Tela Dividida (Split Screen):** Ao referenciar uma fonte na resposta, a interface gera botões interativos que abrem a nota original na íntegra na lateral da tela, permitindo auditoria humana da resposta.

### 📚 Chat RAG para Livros (PDF)
* **Ingestão Avançada (ETL):** O sistema não realiza apenas leituras rasas. Ele extrai PDFs página por página, converte em JSON mantendo rastreabilidade (livro, número da página) e aplica *Overlapping* inteligente no *Chunker* para não perder contextos nas bordas das páginas.
* **Auto-Sumarização Silenciosa:** Durante o upload de um PDF, uma LLM atua em *background* para gerar e armazenar um Resumo Global Estruturado da obra.
* **Roteador Cognitivo:** O sistema analisa a intenção da pergunta do usuário antes de buscar no banco.
    * *Perguntas Globais* (ex: "Me resuma este livro") buscam o *Super Chunk* de resumo na íntegra.
    * *Perguntas Específicas* (ex: "O que diz a página 40?") utilizam o operador lógico de banco de dados para isolar as páginas cruas, garantindo precisão matemática (Tipagem Forte).
* **Filtro Customizável (Top-K):** Controle dinâmico pelo usuário para recuperar de 5 a 9 trechos de contexto por resposta, além de cruzamento de dados com as notas do Obsidian.

### 🔗 Gestor de Conexões e Filtros
* **Injeção Automática de Backlinks:** Varre as notas em busca de similaridades semânticas e injeta conexões bidirecionais dinamicamente no final do Markdown.
* **Desfazer (Undo):** Reversor de segurança capaz de remover limpa e integralmente os links previamente injetados pela IA.
* **Filtros e Configurações Persistentes:** Interface para selecionar diretórios do Obsidian a serem ignorados (arquivos de mídia, templates) ou seleção múltipla de livros importados, gerando modificação imediata na memória do motor de RAG.

---

## 🛠️ Como Utilizar

Python 3.10 ou superior instalado.

_Se optar por rodar modelos locais, garanta que o Ollama esteja em execução com o modelo de sua escolha (ex: llama3)._

### 1. Configuração do Ambiente
Clone o repositório, crie seu ambiente virtual (venv) e instale as dependências necessárias:

```bash
# Clonar o repositório
git clone https://github.com/diegusxavier/wikisidian.git

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

## 🖥️ Menus da Interface de Usuário
- Menu Lateral Esquerdo:

    - Configuração do caminho absoluto para o seu Cofre (Vault) do Obsidian.

    - Botões de acesso ao Histórico JSON (conversas salvas de livros e notas).

    - Painel de seleção dinâmica para excluir/marcar Pastas Ignoradas.

    - Painel de Importação (Drag and Drop) de PDFs e exclusão de obras processadas.

    - Filtro de visualização para marcar/desmarcar quais livros a IA pode ler naquele momento.

- Menu Superior (Tabs):

    - 💬 Chat Obsidian: Interação focada em sua base de conhecimento própria.

    - 📚 Chat Livros (PDF): Interação focada nas obras carregadas, com controle Estrito, Roteamento Cognitivo e seletor Top-K.

    - 🔗 Gestor de Conexões: Ferramenta dedicada para forjar links ou auditar metadados no Obsidian.

## 📂 Estrutura de Pastas
A arquitetura do projeto separa o motor lógico da interface visual:

```python
wikisidian/
├── books_data/
│   ├── extracted_texts/  # Páginas de PDFs extraídas em fomato estruturado (.json)
│   ├── raw_pdfs/         # Armazenamento bruto das obras
│   └── summaries/        # Resumos Globais gerados por IA em Markdown (.txt)
├── src/
│   ├── core/
│   │   ├── embedder.py       # Interações vetoriais com o banco de dados ChromaDB
│   │   ├── linker.py         # Motor semântico para injeção de links nas notas
│   │   ├── pdf_rag_cli.py    # Motor RAG com Roteador Cognitivo para os Livros
│   │   ├── rag_cli.py        # Motor RAG nativo para o Obsidian
│   │   └── scanner.py        # Varredura de arquivos
│   ├── utils/
│   │   ├── chunker.py        # Fragmentação semântica (Markdown e PDF) com Overlapping
│   │   ├── file_handler.py   # Utilitários de manipulação de disco
│   │   ├── pdf_handler.py    # Extrator avançado de páginas
│   │   ├── summarizer.py     # Agente responsável pelo Resumo Global Automático
│   │   └── undo_links.py     # Algoritmo reversor de assinaturas
│   └── config.py
├── vector_store/         # Banco de dados vetorial local (ChromaDB)
├── app.py                # Frontend Web interativo construído em Streamlit
├── main.py               # Launcher principal do ecossistema
├── requirements.txt      # Dependências de biblioteca
└── settings.json         # Configurações dinâmicas persistidas
```
