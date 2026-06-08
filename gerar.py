"""
Pipeline completo: Edital PDF → Cargo → Apostila

Uso:
  python gerar.py --edital edital.pdf --cargo "VIGIA"
  python gerar.py --edital edital.pdf --cargo "Professor Educação Infantil / Anos Iniciais"
  python gerar.py --edital edital.pdf --cargo "Agente Administrativo" --questoes 7
"""

import argparse
import os
import sys
import time

import anthropic

from ler_edital import extrair_dados_cargo, construir_prompt_edital
from gerar_apostila import salvar_markdown, sanitizar_nome_arquivo

SYSTEM_PROMPT = """Você é um especialista renomado em concursos públicos brasileiros com mais de 15 anos de experiência.
Você conhece profundamente as bancas (CESPE, FCC, VUNESP, FGV, QUADRIX, IGEDUC, etc.) e os padrões de questões.
Você escreve apostilas didáticas, claras, diretas e focadas no que realmente cai em prova.
Use sempre formatação Markdown com hierarquia clara (##, ###, **negrito**, listas).
Nunca inclua avisos, disclaimers ou introduções genéricas — vá direto ao conteúdo."""


def extrair_texto_pdf(caminho_pdf: str) -> str:
    """Extrai texto de PDF usando pdfplumber (melhor para editais com tabelas)."""
    try:
        import pdfplumber
        texto = []
        with pdfplumber.open(caminho_pdf) as pdf:
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    texto.append(t)
        return "\n".join(texto)
    except ImportError:
        pass

    # Fallback: pdfminer
    try:
        from pdfminer.high_level import extract_text
        return extract_text(caminho_pdf)
    except ImportError:
        raise RuntimeError(
            "Instale pdfplumber ou pdfminer.six para ler PDFs:\n"
            "  pip install pdfplumber"
        )


def gerar_apostila_do_edital(
    texto_edital: str,
    cargo: str,
    questoes: int = 5,
    pasta_saida: str = "apostilas"
) -> str:
    """
    Pipeline completo:
    1. Extrai dados do cargo no edital via Claude
    2. Constrói prompt rico com tópicos exatos
    3. Gera apostila via streaming
    4. Salva em arquivo .md
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY não configurada.")

    # ── Passo 1: Extração dos dados do cargo ──────────────────────────────
    print(f"\n🔍 Lendo edital e localizando o cargo '{cargo}'...")
    dados = extrair_dados_cargo(texto_edital, cargo)

    print(f"\n✅ Cargo encontrado:")
    print(f"   Cargo    : {dados.get('cargo')}")
    print(f"   Órgão    : {dados.get('orgao')}")
    print(f"   Banca    : {dados.get('banca')}")
    print(f"   Nível    : {dados.get('nivel')}")
    print(f"   Salário  : {dados.get('salario')}")
    print(f"   Vagas    : {dados.get('vagas')}")

    gerais = dados.get("conhecimentos_gerais", {})
    especificos = dados.get("conhecimentos_especificos", {})
    total_disc = len(gerais) + len(especificos)

    print(f"\n   Disciplinas extraídas ({total_disc}):")
    for d in list(gerais.keys()) + list(especificos.keys()):
        print(f"    • {d}")

    # ── Passo 2: Monta prompt com tópicos reais do edital ─────────────────
    prompt = construir_prompt_edital(dados, questoes_por_disciplina=questoes)

    # ── Passo 3: Gera apostila com streaming ──────────────────────────────
    print(f"\n⏳ Gerando apostila (streaming)...\n")
    print("─" * 60)

    client = anthropic.Anthropic(api_key=api_key)
    chunks = []
    inicio = time.time()

    try:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for texto in stream.text_stream:
                print(texto, end="", flush=True)
                chunks.append(texto)

    except anthropic.AuthenticationError:
        raise EnvironmentError("ANTHROPIC_API_KEY inválida.")
    except anthropic.RateLimitError:
        raise RuntimeError("Rate limit atingido. Aguarde e tente novamente.")
    except anthropic.APIConnectionError:
        raise RuntimeError("Sem conexão com a API.")
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Erro da API ({e.status_code}): {e.message}")
    except KeyboardInterrupt:
        print("\n\n⚠  Interrompido pelo usuário.")
        if not chunks:
            sys.exit(0)

    # ── Passo 4: Salva arquivo ─────────────────────────────────────────────
    conteudo = "".join(chunks)
    elapsed = time.time() - inicio

    nome_arquivo = sanitizar_nome_arquivo(
        dados.get("cargo", cargo).lower().replace(" ", "_").replace("/", "_")
    )
    caminho_saida = f"{pasta_saida}/{nome_arquivo}.md"

    salvar_markdown(conteudo, caminho_saida)

    print(f"\n\n{'─' * 60}")
    print(f"✅ Apostila gerada com sucesso!")
    print(f"   Arquivo  : {caminho_saida}")
    print(f"   Tamanho  : {len(conteudo):,} caracteres")
    print(f"   Tempo    : {elapsed:.1f}s")
    print("─" * 60 + "\n")

    return caminho_saida


def main():
    parser = argparse.ArgumentParser(
        description="Gera apostila de concurso a partir de um edital PDF"
    )
    parser.add_argument(
        "--edital", required=True,
        help="Caminho para o PDF do edital"
    )
    parser.add_argument(
        "--cargo", required=True,
        help="Nome do cargo (ex: 'VIGIA', 'Professor Educação Infantil / Anos Iniciais')"
    )
    parser.add_argument(
        "--questoes", type=int, default=5,
        help="Questões por disciplina (padrão: 5)"
    )
    parser.add_argument(
        "--saida", default="apostilas",
        help="Pasta de saída (padrão: apostilas/)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.edital):
        print(f"❌ Arquivo não encontrado: {args.edital}")
        sys.exit(1)

    print(f"📄 Lendo PDF: {args.edital}")
    texto_edital = extrair_texto_pdf(args.edital)
    print(f"   {len(texto_edital):,} caracteres extraídos")

    try:
        gerar_apostila_do_edital(
            texto_edital=texto_edital,
            cargo=args.cargo,
            questoes=args.questoes,
            pasta_saida=args.saida
        )
    except (EnvironmentError, RuntimeError, ValueError) as e:
        print(f"\n❌ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
