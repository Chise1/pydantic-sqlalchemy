#!/usr/bin/env bash

set -e
set -x

mypy sqlalchemy_dantic
black sqlalchemy_dantic tests --check
isort --multi-line=3 --trailing-comma --force-grid-wrap=0 --combine-as --line-width 88 --recursive --check-only --thirdparty sqlalchemy_dantic pydantic_sqlalchemy tests
