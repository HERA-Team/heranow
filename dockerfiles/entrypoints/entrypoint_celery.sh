#!/bin/bash

export PATH=/opt/conda/envs/heranow/bin:$PATH
micromamba activate heranow

celery -A heranow worker -l INFO --autoscale=10,3
