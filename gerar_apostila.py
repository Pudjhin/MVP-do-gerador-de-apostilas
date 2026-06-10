"""
Módulo principal de geração de apostilas para concursos públicos.
Usa a API da Anthropic (Claude) via streaming com auto-continuação.
"""

import anthropic
import os
import re
from dataclasses import dataclass, field
from typing import Generator

# ---------------------------------------------------------------------------
# Configuração de disciplinas padrão por perfil de cargo
# ---------------------------------------------------------------------------

DISCIPLINAS_PADRAO = {
    "professor": [
        "Língua Portuguesa",
        "Legislação Educacional (LDB, BNCC, ECA)",
        "Didática e Metodologia de Ensino",
        "Psicologia da Educação",
        "Conhecimentos Pedagógicos",
    ],
    "administrativo": [
        "Língua Portuguesa",
        "Raciocínio Lógico",
        "Noções de Direito Administrativo",
        "Noções de Informática",
        "Atualidades",
    ],
    "tecnico": [
        "Língua Portuguesa",
        "Raciocínio Lógico",
        "Conhecimentos Específicos",
        "Noções de Administração Pública",
        "Atualidades",
    ],
}

# ---------------------------------------------------------------------------
# Dataclasses de entrada
# ---------------------------------------------------------------------------

@dataclass
class ConfigApostila:
    cargo: str
    orgao: str = ""
    banca: str = ""
    disciplinas: list[str] = field(default_factory=list)
    nivel: str = "médio"
    questoes_por_disciplina: int = 50  # <-- AQUI: Acelerador no máximo!

    def __post_init__(self):
        self.cargo = self.cargo.strip()
        if not self.cargo:
            raise ValueError("O campo 'cargo' não pode ser vazio.")
        if not self.disciplinas:
            perfil = self._detectar_perfil()
            self.disciplinas = DISCIPLINAS_PADRAO.get(perfil, DISCIPLINAS_PADRAO["administrativo"])

    def _detectar_perfil(self) -> str:
        cargo_lower = self.cargo.lower()
        if any(p in cargo_lower for p in ["professor", "docente", "educador", "pedagog"]):
            return "professor"
        if any(p in cargo_lower for p in ["técnico", "tecnico", "analista", "especialista"]):
            return "tecnico"
        return "administrativo"

# ---------------------------------------------------------------------------
# Geração de conteúdo
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Você é um especialista renomado em concursos públicos brasileiros com mais de 15 anos de experiência.
Você conhece profundamente as bancas (CESPE, FCC, VUNESP, FGV, QUADRIX, etc.) e os padrões de questões.
Você escreve apostilas didáticas, claras, diretas e focadas no que realmente cai em prova.
Use sempre formatação Markdown com hierarquia clara (##, ###, **negrito**, listas).
Nunca inclua avisos, disclaimers ou introduções genéricas — vá direto ao conteúdo."""

def _construir_prompt_teoria(config: ConfigApostila, disciplina_focada: str) -> str:
    contexto_banca = f"Banca: **{config.banca}**\n" if config.banca else ""
    contexto_orgao = f"Órgão/Instituição: **{config.orgao}**\n" if config.orgao else ""

    return f"""Você deve gerar APENAS a parte teórica EXCLUSIVAMENTE para a disciplina abaixo, pertencente ao concurso de {config.cargo}.

{contexto_orgao}{contexto_banca}Nível de Escolaridade: {config.nivel}

============================================================
DISCIPLINA A SER GERADA AGORA:
{disciplina_focada}
============================================================

Instruções Cruciais:
1. Desenvolva uma seção '📚 Teoria Essencial' EXAUSTIVA e de ALTÍSSIMA DENSIDADE para os tópicos listados. Aprofunde cada conceito ao máximo, trazendo contexto histórico, exemplos práticos de aplicação, jurisprudência (quando for matéria de Direito) e explicações minuciosas. 
2. O material deve ser extenso e robusto. Use e abuse de tabelas detalhadas, listas e blocos de texto profundos.
3. Destaque pegadinhas clássicas da banca utilizando blocos de citação (> Pegadinha).
4. Após a teoria profunda, crie um '🗂️ Resumo Rápido' em formato de tabela ou lista para revisão de véspera.

Importante: NÃO GERE AS QUESTÕES AGORA. Foque 100% do espaço na teoria e no resumo. Vá direto para o conteúdo da matéria."""

def _construir_prompt_questoes(config: ConfigApostila, disciplina_focada: str) -> str:
    contexto_banca = f"Banca: **{config.banca}**\n" if config.banca else ""

    return f"""Você deve gerar APENAS as questões comentadas EXCLUSIVAMENTE para a disciplina abaixo, pertencente ao concurso de {config.cargo}.

{contexto_banca}Nível de Escolaridade: {config.nivel}
Disciplina: {disciplina_focada}

Instruções Cruciais:
1. Gere exatamente {config.questoes_por_disciplina} questões inéditas ou adaptadas focadas no perfil da banca.
2. O formato deve ser múltipla escolha (A a E) ou Certo/Errado.
3. Forneça o GABARITO e o COMENTÁRIO detalhado EXCLUSIVAMENTE da alternativa CORRETA. É terminantemente proibido comentar as alternativas incorretas.
4. Inicie sua resposta obrigatoriamente com o título '## 📝 Questões Comentadas'.

Importante: NÃO GERE TEORIA. Vá direto para as questões."""

def _gerar_com_auto_continuacao(client, prompt_texto) -> Generator[str, None, None]:
    """
    Roda o streaming e, se bater no limite de tokens, pede para a IA continuar
    exatamente de onde parou de forma invisível para o usuário.
    """
    mensagens = [{"role": "user", "content": prompt_texto}]
    texto_assistente = ""
    
    while True:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=mensagens,
        ) as stream:
            for chunk in stream.text_stream:
                texto_assistente += chunk
                yield chunk
        
        # Verifica se a IA parou porque chegou no final ou porque estourou o limite
        mensagem_final = stream.get_final_message()
        
        if mensagem_final.stop_reason == "max_tokens":
            # Guarda o que ela já disse e manda continuar
            mensagens.append({"role": "assistant", "content": texto_assistente})
            mensagens.append({"role": "user", "content": "Continue exatamente de onde você parou. Não adicione introduções, apenas continue a frase ou o tópico."})
            texto_assistente = "" # Reseta para o próximo ciclo
        else:
            break # Terminou de verdade

def gerar_apostila_stream(config: ConfigApostila) -> Generator[str, None, None]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Variável de ambiente ANTHROPIC_API_KEY não encontrada. "
            "Configure-a no arquivo .env antes de executar."
        )

    client = anthropic.Anthropic(api_key=api_key)

    yield f"# APOSTILA COMPLETA — {config.cargo.upper()}\n\n"
    if config.orgao or config.banca:
        orgao_str = config.orgao if config.orgao else "Órgão não especificado"
        banca_str = f"Banca {config.banca}" if config.banca else "Banca não especificada"
        yield f"## {orgao_str} — {banca_str}\n\n"
    yield "---\n\n"

    for i, disciplina in enumerate(config.disciplinas, 1):
        nome_limpo = disciplina.split('|')[0].strip().upper()
        yield f"# {i}. {nome_limpo}\n\n---\n\n"

        try:
            # PARTE 1: Teoria com auto-continuação
            prompt_teoria = _construir_prompt_teoria(config, disciplina)
            for text in _gerar_com_auto_continuacao(client, prompt_teoria):
                yield text
            
            yield "\n\n"

            # PARTE 2: Questões com auto-continuação
            prompt_questoes = _construir_prompt_questoes(config, disciplina)
            for text in _gerar_com_auto_continuacao(client, prompt_questoes):
                yield text
                    
        except anthropic.AuthenticationError:
            raise EnvironmentError("ANTHROPIC_API_KEY inválida. Verifique a chave no .env.")
        except Exception as e:
            raise RuntimeError(f"Erro na matéria {nome_limpo}: {e}")

        yield "\n\n<br>\n\n"

def gerar_apostila(config: ConfigApostila) -> str:
    return "".join(gerar_apostila_stream(config))

# ---------------------------------------------------------------------------
# Utilitários de saída
# ---------------------------------------------------------------------------

def salvar_markdown(conteudo: str, caminho: str) -> None:
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)

def sanitizar_nome_arquivo(nome: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", nome).strip()

def converter_md_para_pdf(caminho_md: str, caminho_pdf: str) -> None:
    """
    Lê um arquivo Markdown, converte para HTML estruturado com estilização
    básica de impressão e gera um PDF profissional usando o WeasyPrint.
    """
    import markdown
    from weasyprint import HTML, CSS

    if not os.path.exists(caminho_md):
        raise FileNotFoundError(f"Arquivo Markdown não encontrado: {caminho_md}")

    # 1. Lê o conteúdo em Markdown
    with open(caminho_md, "r", encoding="utf-8") as f:
        texto_markdown = f.read()

    # 2. Converte para HTML ativando suporte a tabelas e elementos extras
    html_puro = markdown.markdown(texto_markdown, extensions=['tables', 'fenced_code'])

    # 3. Injeta um CSS básico de folha de estilo para o PDF ficar bonito e legível
    css_estilo = """
    @page {
        size: A4;
        margin: 20mm 15mm;
        background-color: #faf9f6;
        @bottom-right {
            content: counter(page);
            font-size: 9pt;
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #718096;
        }
    }
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
        color: #2d3748;
        font-size: 11pt;
        margin: 0;
        padding: 0;
        orphans: 4;
        widows: 4;
    }
    .page-container {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 6px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    h1 {
        font-size: 20pt;
        color: #2b6cb0;
        text-align: center;
        page-break-before: always;
        margin-bottom: 25px;
        padding-bottom: 10px;
        border-bottom: 3px solid #63b3ed;
    }
    h1:first-of-type {
        page-break-before: avoid;
    }
    h2 {
        font-size: 16pt;
        color: #2c5282;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 5px;
        margin-top: 25px;
        page-break-after: avoid;
    }
    h3 {
        font-size: 13pt;
        color: #4a5568;
        margin-top: 20px;
        page-break-after: avoid;
        border-left: 4px solid #4299e1;
        padding-left: 10px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        font-size: 10pt;
    }
    th, td {
        border: 1px solid #cbd5e0;
        padding: 10px;
        text-align: left;
    }
    th {
        background-color: #ebf8ff;
        color: #2b6cb0;
        font-weight: bold;
    }
    tr:nth-child(even) {
        background-color: #f7fafc;
    }
    blockquote {
        background-color: #fffaf0;
        border-left: 4px solid #dd6b20;
        padding: 10px 15px;
        margin: 20px 0;
        font-style: italic;
        font-size: 10.5pt;
    }
    hr {
        border: 0;
        border-top: 1px solid #e2e8f0;
        margin: 30px 0;
    }
    code {
        background-color: #edf2f7;
        padding: 2px 4px;
        border-radius: 4px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.9em;
        color: #e53e3e;
    }
    pre {
        background-color: #2d3748;
        color: #f7fafc;
        padding: 12px;
        border-radius: 4px;
        overflow-x: auto;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.9em;
    }
    """

    # 4. Compila o documento final e gera o PDF
    os.makedirs(os.path.dirname(caminho_pdf) or ".", exist_ok=True)
    HTML(string=html_puro).write_pdf(caminho_pdf, stylesheets=[CSS(string=css_estilo)])
    print(f"📊 PDF gerado com sucesso em: {caminho_pdf}")