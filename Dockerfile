FROM python:3.11-slim

WORKDIR /app

# Installa le dipendenze di sistema necessarie per fastf1
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copia i file dei requisiti prima (per sfruttare la cache Docker)
COPY requirements.txt .

# Installa le dipendenze Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto del codice
COPY . .

# Crea la cartella per la cache
RUN mkdir -p /app/f1_cache

# Porta esposta
EXPOSE 5000

# Comando di avvio
CMD gunicorn app:app --bind 0.0.0.0:$PORT
