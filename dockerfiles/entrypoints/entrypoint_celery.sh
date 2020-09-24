#!/bin/bash

export PATH=/opt/conda/envs/heranow/bin:$PATH
source activate heranow

celery -A heranow worker -l INFO --autoscale=10,3
