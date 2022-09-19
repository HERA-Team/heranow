#!/bin/bash

export PATH=/opt/conda/envs/heranow/bin:$PATH
micromamba activate heranow

celery -A heranow beat -l INFO
