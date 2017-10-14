#!/bin/bash

cd /home/pi/PlaylistDatabase/frontend

source ./venv/bin/activate
PYTHONPATH=/home/pi/PlaylistDatabase:$PYTHONPATH FLASK_APP=main.py flask run --host=0.0.0.0
