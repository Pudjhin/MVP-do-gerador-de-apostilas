"""
CLI para geração de apostilas de concurso público.
Uso: python main.py
     python main.py --cargo "Professor Educação Infantil" --orgao "Prefeitura de São Luís" --banca CESPE
"""

import argparse
import sys
import time
from pathlib import Path
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

from gerar_apostila import (
    ConfigApostila,
    gerar_apostila_stream,
    salvar_markdown,
    sanitizar_nome_arquivo,
    converter_md_para_pdf,
)

from ler_edital import extrair_texto_pdf, extrair_dados_cargo, montar_config_apostila

def parse_args():
    parser = argparse.ArgumentParser(
        description="Gerador de apostilas para concursos públicos via Claude API"
    )
    parser.add_argument("--cargo", help="Nome do cargo (ex: 'Professor Anos Iniciais')")
    parser.add_argument("--orgao", default="", help="Órgão ou instituição")
    parser.add_argument("--banca", default="", help="Banca examinadora (ex: CESPE, FCC)")
    parser.add_argument(
        "--nivel",
        default="médio",
        choices=["fundamental", "médio", "superior"],
        help="Nível de escolaridade exigido",
    )
    parser.add_argument(
        "--disciplinas",
        nargs="+",
        help="Lista de disciplinas (separadas por espaço, use aspas para nomes compostos)",
    )
    parser.add_argument(
        "--questoes",
        type=int,
        default=5,
        help="Número de questões por disciplina (padrão: 5)",
    )
    parser.add_argument(
        "--saida",
        default="",
        help="Caminho do arquivo de saída (padrão: apostilas/<cargo>.md)",
    )
    return parser.parse_args()


def solicitar_interativo() -> ConfigApostila:
    """Modo interativo com suporte a leitura de edital em PDF."""
    print("\n" + "=" * 60)
    print("  GERADOR DE APOSTILAS — CONCURSOS PÚBLICOS")
    print("=" * 60 + "\n")

    print("Opção 1: Extrair disciplinas do edital em PDF (Automático)")
    print("Opção 2: Digitar disciplinas manualmente")
    opcao = input("\nEscolha (1 ou 2) [Enter para 1]: ").strip() or "1"

    if opcao == "1":
        pdf_path = input("\nCaminho do arquivo PDF do edital: ").strip()
        while not pdf_path or not Path(pdf_path).exists():
            print("  ⚠  Arquivo não encontrado. Verifique o caminho e tente novamente.")
            pdf_path = input("Caminho do arquivo PDF: ").strip()

        cargo = input("Nome exato do Cargo no edital (ex: Analista Administrativo): ").strip()
        while not cargo:
            print("  ⚠  O cargo é obrigatório para a IA localizar as disciplinas corretas.")
            cargo = input("Nome exato do Cargo: ").strip()

        questoes_str = input("Questões por disciplina (Enter para 5): ").strip()
        try:
            questoes = int(questoes_str) if questoes_str else 5
        except ValueError:
            questoes = 5

        print("\n⏳ Lendo o PDF e extraindo o texto...")
        texto_pdf = extrair_texto_pdf(pdf_path)

        print("⏳ Analisando edital com a IA (isso pode levar alguns segundos)...")
        dados_extraidos = extrair_dados_cargo(texto_pdf, cargo)

        print("✅ Edital mapeado com sucesso! Montando configuração da apostila...\n")
        config_dict = montar_config_apostila(dados_extraidos, questoes)

        # Retorna o modelo preenchido com os dados sugados do PDF
        return ConfigApostila(
            cargo=config_dict["cargo"],
            orgao=config_dict["orgao"],
            banca=config_dict["banca"],
            nivel=config_dict["nivel"],
            disciplinas=config_dict["disciplinas"],
            questoes_por_disciplina=config_dict["questoes_por_disciplina"]
        )

    else:
        # Modo Manual Original (mantido como fallback)
        cargo = input("\nCargo: ").strip()
        while not cargo:
            print("  ⚠  O cargo é obrigatório.")
            cargo = input("Cargo: ").strip()

        orgao = input("Órgão/Instituição (Enter para pular): ").strip()
        banca = input("Banca examinadora (Enter para pular): ").strip()

        niveis = {"1": "fundamental", "2": "médio", "3": "superior"}
        print("\nNível de escolaridade:")
        print("  1 - Fundamental")
        print("  2 - Médio")
        print("  3 - Superior")
        nivel_escolha = input("Escolha (Enter para médio): ").strip()
        nivel = niveis.get(nivel_escolha, "médio")

        print("\nDisciplinas (deixe em branco para usar padrão do cargo):")
        print("Digite uma por linha. Linha vazia para finalizar.")
        disciplinas = []
        while True:
            d = input(f"  Disciplina {len(disciplinas)+1}: ").strip()
            if not d:
                break
            disciplinas.append(d)

        questoes_str = input("\nQuestões por disciplina (Enter para 5): ").strip()
        try:
            questoes = int(questoes_str) if questoes_str else 5
            questoes = max(1, min(questoes, 15)) 
        except ValueError:
            questoes = 5

        return ConfigApostila(
            cargo=cargo,
            orgao=orgao,
            banca=banca,
            nivel=nivel,
            disciplinas=disciplinas,
            questoes_por_disciplina=questoes,
        )


def main():
    args = parse_args()

    # Decide modo: argumento CLI ou interativo
    if args.cargo:
        try:
            config = ConfigApostila(
                cargo=args.cargo,
                orgao=args.orgao,
                banca=args.banca,
                nivel=args.nivel,
                disciplinas=args.disciplinas or [],
                questoes_por_disciplina=args.questoes,
            )
        except ValueError as e:
            print(f"\n❌ Erro de configuração: {e}")
            sys.exit(1)
    else:
        config = solicitar_interativo()

    # Define caminho de saída
    if args.saida:
        caminho_saida = args.saida
    else:
        nome_arquivo = sanitizar_nome_arquivo(config.cargo.lower().replace(" ", "_"))
        caminho_saida = f"apostilas/{nome_arquivo}.md"

    # Exibe resumo antes de gerar
    print("\n" + "─" * 60)
    print(f"  Cargo    : {config.cargo}")
    if config.orgao:
        print(f"  Órgão    : {config.orgao}")
    if config.banca:
        print(f"  Banca    : {config.banca}")
    print(f"  Nível    : {config.nivel}")
    print(f"  Disciplinas ({len(config.disciplinas)}):")
    for d in config.disciplinas:
        print(f"    • {d}")
    print(f"  Questões : {config.questoes_por_disciplina} por disciplina")
    print(f"  Saída    : {caminho_saida}")
    print("─" * 60)

    confirmar = input("\nGerar apostila? (Enter para confirmar / Ctrl+C para cancelar): ")
    print()

    # Geração com streaming e progresso
    conteudo_total = []
    inicio = time.time()
    chars = 0

    print("⏳ Gerando apostila (streaming)...\n")
    print("─" * 60)

    try:
        for chunk in gerar_apostila_stream(config):
            print(chunk, end="", flush=True)
            conteudo_total.append(chunk)
            chars += len(chunk)

    except (EnvironmentError, RuntimeError) as e:
        print(f"\n\n❌ {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠  Geração interrompida pelo usuário.")
        if conteudo_total:
            salvar = input("Salvar conteúdo parcial? (s/N): ").strip().lower()
            if salvar != "s":
                sys.exit(0)
        else:
            sys.exit(0)

    # Salva arquivo
    conteudo = "".join(conteudo_total)
    try:
        salvar_markdown(conteudo, caminho_saida)
        # Gera o PDF logo em seguida
        print("\n⏳ Convertendo material para PDF...")
        caminho_pdf = caminho_saida.replace(".md", ".pdf")
        converter_md_para_pdf(caminho_saida, caminho_pdf)
    except OSError as e:
        print(f"\n\n❌ Erro ao salvar arquivo: {e}")
        sys.exit(1)

    elapsed = time.time() - inicio
    print(f"\n\n{'─' * 60}")
    print(f"✅ Apostila gerada com sucesso!")
    print(f"   Arquivo : {caminho_saida}")
    print(f"   Tamanho : {chars:,} caracteres")
    print(f"   Tempo   : {elapsed:.1f}s")
    print("─" * 60 + "\n")


if __name__ == "__main__":
    main()
