#!/bin/bash

export PATH=/opt/conda/envs/heranow/bin:$PATH
micromamba activate heranow
python manage.py migrate
python manage.py collectstatic --noinput


if [ "$INITIALIZE" -eq "1" ]; then
python manage.py generate_antennas
python manage.py initialize_issues

fi

if [ "$DJANGO_DEBUG" -eq  "1" ]; then
    echo "DEBUG MODE"
    uvicorn heranow.asgi:application --host 0.0.0.0 --port ${PORT} --reload
else
    gunicorn -k uvicorn.workers.UvicornWorker -w 14 --threads 24 heranow.asgi:application -b :${PORT} --timeout 300 --max-requests 100000 --max-requests-jitter 10000
fi
