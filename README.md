# 📚 Gerador de Apostilas — Concursos Públicos

Gera apostilas completas (teoria + resumo + questões comentadas) para qualquer cargo de concurso público, usando a API do Claude (Anthropic).

---

## Estrutura do projeto

```
concurso_mvp/
├── gerar_apostila.py   # Módulo core: config, prompt, chamada de API
├── main.py             # CLI interativa + argumentos
├── batch.py            # Geração em lote via JSON
├── requirements.txt    # Dependências (só o que é usado)
└── apostilas/          # Pasta de saída (criada automaticamente)
```

---

## Instalação

```bash
pip install -r requirements.txt
```

---

## Configuração

Defina sua chave da API como variável de ambiente:

**Linux/macOS:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Windows (CMD):**
```cmd
set ANTHROPIC_API_KEY=sk-ant-...
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Uso

### Modo interativo (sem argumentos)
```bash
python main.py
```
Vai solicitar cargo, órgão, banca, nível e disciplinas.

### Modo CLI (com argumentos)
```bash
python main.py \
  --cargo "Professor Educação Infantil" \
  --orgao "Prefeitura de São José do Ribamar" \
  --banca CESPE \
  --nivel superior \
  --questoes 5
```

### Com disciplinas customizadas
```bash
python main.py \
  --cargo "Agente Administrativo" \
  --banca FCC \
  --disciplinas "Língua Portuguesa" "Raciocínio Lógico" "Informática"
```

### Geração em lote
```bash
# Gera exemplo de arquivo de configuração
python batch.py --exemplo

# Edite batch_config_exemplo.json e depois:
python batch.py --config batch_config_exemplo.json
```

---

## Estrutura da apostila gerada

Para cada disciplina:
- **Teoria Essencial** — tópicos mais cobrados, definições, exemplos, pegadinhas
- **Resumo Rápido** — tabela ou lista para revisão de véspera
- **Questões Comentadas** — enunciado + alternativas + gabarito + explicação detalhada

---

## Detecção automática de disciplinas

Se você não informar disciplinas, o sistema detecta o perfil pelo nome do cargo:

| Perfil detectado | Disciplinas padrão |
|---|---|
| Professor / Docente / Pedagogo | Língua Portuguesa, LDB/BNCC/ECA, Didática, Psicologia, Conhecimentos Pedagógicos |
| Técnico / Analista / Especialista | Língua Portuguesa, Raciocínio Lógico, Conhecimentos Específicos, Administração Pública, Atualidades |
| Outros (padrão administrativo) | Língua Portuguesa, Raciocínio Lógico, Direito Administrativo, Informática, Atualidades |

---

## Configuração em lote (batch_config.json)

```json
[
  {
    "cargo": "Professor Anos Iniciais",
    "orgao": "Prefeitura de Altos",
    "banca": "IGEDUC",
    "nivel": "superior",
    "disciplinas": ["Língua Portuguesa", "Pedagogia", "LDB e BNCC"],
    "questoes_por_disciplina": 5
  }
]
```

---

## Erros comuns

| Erro | Causa | Solução |
|---|---|---|
| `ANTHROPIC_API_KEY não encontrada` | Variável não definida | `export ANTHROPIC_API_KEY=sk-ant-...` |
| `ANTHROPIC_API_KEY inválida` | Chave errada ou expirada | Verifique em console.anthropic.com |
| `Limite de requisições atingido` | Rate limit da API | Aguarde ~1 minuto e tente novamente |
| `Sem conexão com a API` | Problema de internet | Verifique sua conexão |

---

## Expansões sugeridas

- `exportar_pdf.py` — converte o `.md` gerado em PDF formatado
- `exportar_docx.py` — converte para `.docx` com capa e índice
- Interface web com Streamlit (`streamlit run app.py`)
- Integração com edital em PDF: extrai disciplinas automaticamente via Claude
