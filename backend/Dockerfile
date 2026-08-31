# Back-end chatbot territorial — image CPU, modèle d'embedding embarqué (fonctionne hors ligne)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf-cache \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TOKENIZERS_PARALLELISM=false \
    CHATBOT_CORPUS_DIR=/corpus \
    CHATBOT_DATA_DIR=/data \
    CHATBOT_SEED_FILE=/app/seed/organizations.json

WORKDIR /app

# torch CPU uniquement (évite ~2 Go de bibliothèques CUDA inutiles sur un serveur standard)
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install -r requirements.txt

# Utilisateur non privilégié, créé AVANT le téléchargement du modèle : un chown -R ultérieur du cache
# dupliquerait ses ~500 Mo dans une nouvelle couche de l'image.
RUN useradd --create-home --uid 1000 chatbot \
    && mkdir -p /data /corpus /opt/hf-cache \
    && chown -R chatbot:chatbot /data /corpus /opt/hf-cache /app
USER chatbot

# Pré-téléchargement du modèle dans l'image : le conteneur n'a besoin d'aucun accès Internet au démarrage
ARG EMBEDDING_MODEL=intfloat/multilingual-e5-small
ENV CHATBOT_EMBEDDING_MODEL=${EMBEDDING_MODEL}
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}', device='cpu')"
ENV HF_HUB_OFFLINE=1

# Fiches documentaires et annuaire de démarrage embarqués ; ./corpus peut être monté par-dessus /corpus
COPY --chown=chatbot:chatbot corpus /corpus
COPY --chown=chatbot:chatbot seed ./seed
COPY --chown=chatbot:chatbot app ./app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
