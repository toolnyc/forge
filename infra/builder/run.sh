#!/bin/bash
set -a
source ~/forge/infra/builder/.env
set +a
cd ~/forge
exec python3 infra/builder/forge_builder.py 2>&1 | tee ~/forge/infra/builder/builder.log
