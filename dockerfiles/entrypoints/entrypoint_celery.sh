#!/bin/bash

export PATH=/opt/conda/envs/heranow/bin:$PATH
source /opt/conda/envs/heranow/binactivate heranow

celery -A heranow worker -l INFO --autoscale=10,3
