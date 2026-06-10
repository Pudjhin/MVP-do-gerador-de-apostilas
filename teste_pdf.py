import os
from gerar_apostila import converter_md_para_pdf

# 1. Define a pasta exata onde o seu Markdown completo está salvo
pasta_saida = "apostilas"

# 2. Define o nome do arquivo Markdown
nome_arquivo_md = "assistente_administrativo.md"

# 3. Monta os caminhos completos (lendo da pasta e salvando na mesma pasta)
caminho_md = os.path.join(pasta_saida, nome_arquivo_md)
caminho_pdf = os.path.join(pasta_saida, nome_arquivo_md.replace(".md", ".pdf"))

print(f"⏳ Lendo o arquivo original '{caminho_md}' e convertendo para PDF...")

try:
    # Chama o conversor passando os caminhos corretos
    converter_md_para_pdf(caminho_md, caminho_pdf)
    
    print(f"✅ Sucesso absoluto! O PDF completão foi salvo na mesma pasta em: {caminho_pdf}")

except FileNotFoundError:
    print(f"\n❌ Erro: Não encontrei o arquivo '{caminho_md}'.")
    print("Verifique se o nome da pasta e do arquivo estão exatos, sem espaços extras ou diferenças nas letras maiúsculas/minúsculas!")
except Exception as e:
    print(f"\n❌ Erro inesperado: {e}")