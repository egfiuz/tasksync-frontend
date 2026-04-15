# Usa a imagem oficial do Python
FROM python:3.9-slim

# Define a pasta de trabalho dentro do servidor
WORKDIR /app

# Copia os arquivos de requisitos e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do backend para o servidor
COPY . .

# Comando para ligar o servidor (usando a porta que o Google Cloud exige)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]