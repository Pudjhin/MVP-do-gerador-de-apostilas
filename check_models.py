import os
import httpx
from dotenv import load_dotenv

# Carrega a chave limpa do seu .env
load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")

print("⏳ Vasculhando os servidores da Anthropic...\n")

headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01"
}

try:
    # Faz uma requisição direta para listar os modelos permitidos
    response = httpx.get("https://api.anthropic.com/v1/models", headers=headers)
    dados = response.json()
    
    if "data" in dados:
        print("✅ Modelos liberados para esta chave:")
        for modelo in dados["data"]:
            print(f"  - {modelo['id']}")
    else:
        print(f"❌ Resposta inesperada ou bloqueio: {dados}")
        
except Exception as e:
    print(f"❌ Erro de conexão: {e}")