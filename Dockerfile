# Imagen del proyecto: Freqtrade oficial + herramientas de desarrollo.
# Fijar FREQTRADE_TAG garantiza que los backtests sean reproducibles (DAS §2).
ARG FREQTRADE_TAG=2026.9
FROM freqtradeorg/freqtrade:${FREQTRADE_TAG}

COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --user --no-cache-dir -r /tmp/requirements-dev.txt
