#!/bin/bash

export PATH=/opt/conda/envs/heranow/bin:$PATH
source /opt/conda/envs/heranow/bin/activate heranow

celery -A heranow beat -l INFO
