#!/bin/bash

export PATH=/opt/conda/envs/heranow/bin:$PATH
source activate heranow

celery -A heranow beat -l INFO
