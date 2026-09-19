# 512 MB RAM ve Düşük Kaynak Tüketimi İçin Optimize Edilmiş Dockerfile
FROM python:3.10-slim

# Gereksiz tamponlamayı ve bytecode üretimini kapatarak RAM tasarrufu sağla
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Sistem paketlerini yükle (git güncelleme için, ffmpeg video remux için)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && git config --global --add safe.directory '*'

# Bağımlılıkları önbellek bırakmadan kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY . .

# Geçici indirme klasörlerini hazırla
RUN mkdir -p downloads tiktok_downloads

EXPOSE 8080

CMD ["python", "main.py"]
