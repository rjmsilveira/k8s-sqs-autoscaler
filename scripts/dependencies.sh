#!/bin/bash

set -ex

apt-get update -y

apt-get install -y --no-install-recommends \
        python-setuptools \
        emacs \
        vim \
        jq

rm -rf /var/lib/apt/lists/*
