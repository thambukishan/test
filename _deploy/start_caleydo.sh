#!/usr/bin/env bash

chmod +x plugin_scripts.sh
sleep 1
./plugin_scripts pre_start
sleep 1
./gunicorn_start.sh
