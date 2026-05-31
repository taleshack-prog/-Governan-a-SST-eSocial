#!/bin/bash
# SST ESOCIAL GOV — Entrypoint
# Copia o PDF de treinamento se existir no volume

if [ -f "/app/seeds/LTCAT_MAHLER_2024.pdf" ]; then
    cp /app/seeds/LTCAT_MAHLER_2024.pdf /tmp/ltcat_mahler.pdf
fi

exec "$@"
