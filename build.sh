#!/usr/bin/env sh

docker build -f dockerfiles/docker_conda -t conda_base:latest .
docker build -f dockerfiles/psql .

docker compose build $@
