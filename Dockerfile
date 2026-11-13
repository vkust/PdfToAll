# Local/server deployment with the LibreOffice bridge available.
# Documents are processed in-container only when you self-host; the desktop
# build does not need this image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-writer-nogui libreoffice-impress-nogui libreoffice-draw-nogui \
        libreoffice-calc-nogui python3-uno python3-pip \
        fonts-dejavu-core fonts-liberation && \
    rm -rf /var/lib/apt/lists/*
# unoconvert must run on the system python: it needs the `uno` module, which has
# no wheel — hence installing unoserver outside the venv.
RUN python3 -m pip install --break-system-packages --no-cache-dir unoserver

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[api]"

EXPOSE 8765
CMD ["uvicorn", "pdftoall.api:app", "--host", "0.0.0.0", "--port", "8765"]
