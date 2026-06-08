"""
Geração em lote de apostilas para múltiplos cargos.
Útil para gerar um catálogo completo de materiais de concurso.

Uso:
    python batch.py --config batch_config.json
    python batch.py  # usa configuração embutida de exemplo
"""

import json
import sys
import time
from pathlib import Path

from gerar_apostila import (
    ConfigApostila,
    gerar_apostila,
    salvar_markdown,
    sanitizar_nome_arquivo,
)


# ---------------------------------------------------------------------------
# Exemplo de configuração embutida
# ---------------------------------------------------------------------------

EXEMPLO_CONFIG = [
    {
        "cargo": "Professor Educação Infantil",
        "orgao": "Prefeitura Municipal",
        "banca": "CESPE",
        "nivel": "superior",
        "disciplinas": [
            "Língua Portuguesa",
            "Legislação Educacional (LDB, BNCC, ECA)",
            "Didática e Metodologia para Educação Infantil",
            "Psicologia do Desenvolvimento Infantil",
        ],
        "questoes_por_disciplina": 5,
    },
    {
        "cargo": "Assistente Administrativo",
        "orgao": "Câmara Municipal",
        "banca": "FCC",
        "nivel": "médio",
        "disciplinas": [
            "Língua Portuguesa",
            "Raciocínio Lógico",
            "Noções de Informática",
            "Direito Administrativo Básico",
        ],
        "questoes_por_disciplina": 5,
    },
]


def carregar_config(caminho: str) -> list[dict]:
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def processar_lote(configs: list[dict], pasta_saida: str = "apostilas") -> None:
    total = len(configs)
    sucessos = 0
    falhas = []

    print(f"\n{'='*60}")
    print(f"  GERAÇÃO EM LOTE — {total} apostila(s)")
    print(f"{'='*60}\n")

    for i, cfg_dict in enumerate(configs, 1):
        cargo = cfg_dict.get("cargo", "")
        print(f"[{i}/{total}] Gerando: {cargo}")
        print(f"         Órgão: {cfg_dict.get('orgao', '—')} | Banca: {cfg_dict.get('banca', '—')}")

        try:
            config = ConfigApostila(**cfg_dict)
        except (ValueError, TypeError) as e:
            print(f"         ❌ Configuração inválida: {e}\n")
            falhas.append({"cargo": cargo, "erro": str(e)})
            continue

        nome_arquivo = sanitizar_nome_arquivo(cargo.lower().replace(" ", "_"))
        caminho_saida = f"{pasta_saida}/{nome_arquivo}.md"

        inicio = time.time()
        try:
            conteudo = gerar_apostila(config)
            salvar_markdown(conteudo, caminho_saida)
            elapsed = time.time() - inicio
            print(f"         ✅ Salvo em {caminho_saida} ({len(conteudo):,} chars, {elapsed:.1f}s)\n")
            sucessos += 1

        except (EnvironmentError, RuntimeError, OSError) as e:
            elapsed = time.time() - inicio
            print(f"         ❌ Erro após {elapsed:.1f}s: {e}\n")
            falhas.append({"cargo": cargo, "erro": str(e)})

        # Pausa entre requisições para evitar rate limit
        if i < total:
            time.sleep(2)

    # Relatório final
    print(f"{'─'*60}")
    print(f"  Resultado: {sucessos}/{total} apostilas geradas com sucesso")
    if falhas:
        print(f"\n  Falhas:")
        for f in falhas:
            print(f"    • {f['cargo']}: {f['erro']}")
    print(f"{'─'*60}\n")

    # Salva log de erros se houver
    if falhas:
        log_path = f"{pasta_saida}/_erros_batch.json"
        Path(pasta_saida).mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(falhas, f, ensure_ascii=False, indent=2)
        print(f"  Log de erros salvo em: {log_path}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Geração em lote de apostilas")
    parser.add_argument("--config", help="Caminho para JSON de configuração do lote")
    parser.add_argument("--saida", default="apostilas", help="Pasta de saída (padrão: apostilas/)")
    parser.add_argument(
        "--exemplo",
        action="store_true",
        help="Salva exemplo de arquivo de configuração JSON",
    )
    args = parser.parse_args()

    if args.exemplo:
        exemplo_path = "batch_config_exemplo.json"
        with open(exemplo_path, "w", encoding="utf-8") as f:
            json.dump(EXEMPLO_CONFIG, f, ensure_ascii=False, indent=2)
        print(f"✅ Exemplo salvo em {exemplo_path}")
        return

    if args.config:
        try:
            configs = carregar_config(args.config)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ Erro ao carregar config: {e}")
            sys.exit(1)
    else:
        print("Nenhum --config fornecido. Usando configuração de exemplo embutida.")
        configs = EXEMPLO_CONFIG

    processar_lote(configs, pasta_saida=args.saida)


if __name__ == "__main__":
    main()
