#!/usr/bin/env sh

docker build -f dockerfiles/docker_conda -t conda_base:latest .

docker-compose build $@
