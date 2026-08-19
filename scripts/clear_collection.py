#!/usr/bin/env python3
"""
clear_collection.py — Limpeza de coleções do ChromaDB

Remove coleções do banco vetorial (vector_store/) de forma segura e controlada.
Útil durante desenvolvimento/testes: troca de embeddings, mudanças no chunker,
re-vetorização, etc.

Uso:
    python scripts/clear_collection.py              # modo interativo (lista + confirma)
    python scripts/clear_collection.py --list       # apenas lista as coleções
    python scripts/clear_collection.py --drop obsidian_notes   # deleta 1 coleção (pede confirmação)
    python scripts/clear_collection.py --drop-all   # deleta TODAS (pede confirmação)

Atenção: a operação é DESTRUTIVA e irreversível. Após deletar uma coleção,
os dados são re-criados automaticamente no próximo boot do app (sync_db
re-vetoriza as notas; livros precisam ser re-importados).
"""

import argparse
import sys
from pathlib import Path

import chromadb

# Padrão do projeto: caminhos sempre a partir da raiz (não depende do CWD)
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "vector_store"


def listar_colecoes(client) -> dict:
    """Retorna {nome_da_colecao: quantidade_de_chunks}."""
    resultado = {}
    for col_info in client.list_collections():
        nome = col_info.name
        try:
            col = client.get_collection(nome)
            resultado[nome] = col.count()
        except Exception as e:
            resultado[nome] = f"erro ao contar: {e}"
    return resultado


def confirmar(mensagem: str) -> bool:
    """Pede confirmação explícita do usuário antes de uma ação destrutiva."""
    resposta = input(f"{mensagem} [s/N]: ").strip().lower()
    return resposta in ("s", "sim", "y", "yes")


def main():
    parser = argparse.ArgumentParser(description="Limpeza de coleções do ChromaDB")
    parser.add_argument("--list", action="store_true", help="apenas lista as coleções e sai")
    parser.add_argument("--drop", metavar="NOME", help="deleta a coleção especificada")
    parser.add_argument("--drop-all", action="store_true", help="deleta TODAS as coleções")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"❌ Banco vetorial não encontrado em: {DB_PATH}")
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(DB_PATH))
    colecoes = listar_colecoes(client)

    if not colecoes:
        print("ℹ️  Nenhuma coleção encontrada no banco vetorial.")
        return

    print("\n📚 Coleções encontradas em vector_store/:")
    for nome, qtd in colecoes.items():
        print(f"   • {nome}: {qtd} chunks")

    if args.list:
        return

    # --- Modo --drop: deleta uma coleção específica ---
    if args.drop:
        if args.drop not in colecoes:
            print(f"❌ Coleção '{args.drop}' não existe.")
            sys.exit(1)
        if confirmar(f"\n⚠️  Deletar a coleção '{args.drop}' ({colecoes[args.drop]} chunks)? "
                    f"Esta ação é IRREVERSÍVEL."):
            client.delete_collection(args.drop)
            print(f"✅ Coleção '{args.drop}' deletada com sucesso.")
        else:
            print("Operação cancelada.")
        return

    # --- Modo --drop-all: deleta todas ---
    if args.drop_all:
        total = sum(qtd for qtd in colecoes.values() if isinstance(qtd, int))
        if confirmar(f"\n⚠️  Deletar TODAS as coleções ({total} chunks no total)? "
                    f"Esta ação é IRREVERSÍVEL."):
            for nome in colecoes:
                client.delete_collection(nome)
                print(f"✅ Coleção '{nome}' deletada.")
        else:
            print("Operação cancelada.")
        return

    # --- Modo interativo (padrão) ---
    print("\nDigite o nome da coleção para deletar, 'todas' para deletar tudo, ou Enter para sair.")
    escolha = input("> ").strip()

    if not escolha:
        print("Nada a fazer. Saindo.")
        return

    if escolha.lower() in ("todas", "all", "*"):
        total = sum(qtd for qtd in colecoes.values() if isinstance(qtd, int))
        if confirmar(f"⚠️  Deletar TODAS as coleções ({total} chunks)? Esta ação é IRREVERSÍVEL."):
            for nome in colecoes:
                client.delete_collection(nome)
                print(f"✅ Coleção '{nome}' deletada.")
        else:
            print("Operação cancelada.")
        return

    if escolha not in colecoes:
        print(f"❌ Coleção '{escolha}' não existe. Use --list para ver as disponíveis.")
        sys.exit(1)

    if confirmar(f"⚠️  Deletar a coleção '{escolha}' ({colecoes[escolha]} chunks)? "
                f"Esta ação é IRREVERSÍVEL."):
        client.delete_collection(escolha)
        print(f"✅ Coleção '{escolha}' deletada com sucesso.")
    else:
        print("Operação cancelada.")


if __name__ == "__main__":
    main()