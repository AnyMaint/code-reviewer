#!/bin/bash

IMAGE_NAME=lemaxw/code-reviewer
TAG=2.0.1

# Get directory of script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Go one level up to use project root as build context
CONTEXT_DIR="$(dirname "$SCRIPT_DIR")"

docker build -f "$SCRIPT_DIR/Dockerfile" -t "$IMAGE_NAME:$TAG" "$CONTEXT_DIR"

docker login
docker push $IMAGE_NAME:$TAG
