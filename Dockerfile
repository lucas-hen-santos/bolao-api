# Usa uma imagem leve do Python 3.11
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema operacional necessárias
# (gcc e libpq-dev são úteis para compilar drivers de banco, se necessário)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos para dentro do container
COPY requirements.txt .

# Instala as bibliotecas Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do código para dentro do container
COPY . .

# Expõe a porta 8000 (onde o FastAPI roda)
EXPOSE 8000

# Comando para iniciar o servidor
# --host 0.0.0.0 é crucial para o Docker aceitar conexões externas
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]