"""
Módulo de leitura de edital de concurso público.
Recebe o texto do edital (já extraído do PDF) e usa o Claude
para localizar e estruturar o conteúdo programático de um cargo específico.
"""

import anthropic
import json
import os
import re
import pdfplumber

def extrair_texto_pdf(caminho_pdf: str) -> str:
    """Abre o arquivo PDF, lê todas as páginas e retorna o texto completo."""
    texto_completo = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                texto_completo.append(texto)
    return "\n".join(texto_completo)

def extrair_dados_cargo(texto_edital: str, cargo: str) -> dict:
    """
    Recebe o texto completo do edital e o nome do cargo.
    Retorna um dict estruturado com todas as informações necessárias
    para gerar a apostila.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY não configurada.")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Você é um especialista em concursos públicos brasileiros.
Analise o edital abaixo e extraia TODAS as informações do cargo "{cargo}".

Retorne APENAS um JSON válido, sem texto antes ou depois, no seguinte formato:

{{
  "cargo": "nome exato do cargo",
  "orgao": "nome do órgão/prefeitura",
  "banca": "nome da banca organizadora",
  "nivel": "fundamental|medio|tecnico|superior|magisterio",
  "salario": "valor do salário base",
  "vagas": número_inteiro,
  "carga_horaria": "carga horária",
  "conhecimentos_gerais": {{
    "NomeDaDisciplina": {{
      "questoes": número,
      "topicos": ["tópico 1", "tópico 2", ...]
    }}
  }},
  "conhecimentos_especificos": {{
    "NomeDaDisciplina": {{
      "questoes": número,
      "topicos": ["tópico 1", "tópico 2", ...]
    }}
  }}
}}

Regras:
- Inclua TODOS os tópicos exatamente como estão no edital
- Se não encontrar o cargo, retorne: {{"erro": "Cargo não encontrado no edital"}}
- Não invente informações; use apenas o que está no edital
- O JSON deve ser estritamente válido

EDITAL:
{texto_edital[:50000]}
"""

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        resposta = msg.content[0].text.strip()

        # Remove possíveis ```json ``` wrappers
        resposta = re.sub(r'^```json\s*', '', resposta)
        resposta = re.sub(r'\s*```$', '', resposta)

        dados = json.loads(resposta)

        if "erro" in dados:
            raise ValueError(dados["erro"])

        return dados

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Falha ao parsear resposta da API como JSON: {e}")
    except anthropic.APIError as e:
        raise RuntimeError(f"Erro na API: {e}")


def montar_config_apostila(dados: dict, questoes_por_disciplina: int = 5) -> dict:
    """
    Converte o dict extraído do edital para o formato
    esperado pelo ConfigApostila do módulo gerar_apostila.py.
    """
    disciplinas = []

    # Gerais primeiro
    for disc, info in dados.get("conhecimentos_gerais", {}).items():
        n_q = info.get("questoes", "?")
        topicos = info.get("topicos", [])
        topicos_str = ", ".join(topicos[:5])  # primeiros 5 para o label
        disciplinas.append(
            f"{disc} ({n_q} questões — Gerais) | Tópicos: {topicos_str}..."
        )

    # Específicos depois
    for disc, info in dados.get("conhecimentos_especificos", {}).items():
        n_q = info.get("questoes", "?")
        topicos = info.get("topicos", [])
        topicos_str = ", ".join(topicos[:5])
        disciplinas.append(
            f"{disc} ({n_q} questões — Específicos) | Tópicos: {topicos_str}..."
        )

    return {
        "cargo": dados.get("cargo", ""),
        "orgao": dados.get("orgao", ""),
        "banca": dados.get("banca", ""),
        "nivel": dados.get("nivel", "médio"),
        "disciplinas": disciplinas,
        "questoes_por_disciplina": questoes_por_disciplina,
        "_dados_completos": dados,  # preserva tópicos completos para o prompt
    }


def construir_prompt_edital(dados: dict, questoes_por_disciplina: int = 5) -> str:
    """
    Constrói um prompt rico com os tópicos exatos do edital,
    para garantir que a apostila cobre exatamente o que vai cair na prova.
    """
    cargo = dados.get("cargo", "")
    orgao = dados.get("orgao", "")
    banca = dados.get("banca", "")
    nivel = dados.get("nivel", "")

    secoes = []

    # Conhecimentos Gerais
    gerais = dados.get("conhecimentos_gerais", {})
    if gerais:
        secoes.append("## GRUPO DE CONHECIMENTOS GERAIS (20 questões)\n")
        for disc, info in gerais.items():
            topicos = "\n".join(f"  - {t}" for t in info.get("topicos", []))
            secoes.append(f"### {disc} ({info.get('questoes', '?')} questões)\n{topicos}\n")

    # Conhecimentos Específicos
    especificos = dados.get("conhecimentos_especificos", {})
    if especificos:
        secoes.append("## GRUPO DE CONHECIMENTOS ESPECÍFICOS (30 questões)\n")
        for disc, info in especificos.items():
            topicos = "\n".join(f"  - {t}" for t in info.get("topicos", []))
            secoes.append(f"### {disc} ({info.get('questoes', '?')} questões)\n{topicos}\n")

    conteudo_programatico = "\n".join(secoes)

    return f"""Você é um especialista renomado em concursos públicos brasileiros.
Elabore uma apostila completa e didática para o cargo abaixo.

**Cargo:** {cargo}
**Órgão:** {orgao}
**Banca:** {banca}
**Nível:** {nivel}

---

## CONTEÚDO PROGRAMÁTICO OFICIAL DO EDITAL

{conteudo_programatico}

---

## INSTRUÇÕES DE ESTRUTURA DA APOSTILA

Para CADA disciplina listada acima, produza:

### [Nome da Disciplina] — X questões

#### 📚 Teoria Essencial
- REGRA DINÂMICA DE TAMANHO: Avalie a extensão do conteúdo. Se for uma matéria muito longa e extensa, crie um resumo didático que facilite a leitura e o entendimento sem comprometer a estrutura da matéria. Nas demais matérias menores, forneça a teoria completa.
- Explique cada tópico de forma clara.
- Destaque os pontos que mais caem em provas da banca {banca}.

#### 🗂️ Resumo Rápido
- Tabela ou lista condensada para revisão de véspera.

#### ✏️ Questões Comentadas ({questoes_por_disciplina} questões)
- OBRIGATÓRIO: Crie exatamente {questoes_por_disciplina} questões.
- OBRIGATÓRIO: Forneça o gabarito.
- OBRIGATÓRIO: Inclua um pequeno comentário direto ao ponto explicando a alternativa correta.

---

Comece imediatamente. Use Markdown estruturado. Seja direto e denso em conteúdo útil."""
