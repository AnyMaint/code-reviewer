#!/bin/bash

# Accept image name and tag as parameters with defaults
[ -n "$1" ] && IMAGE_NAME="$1"
TAG=${2:-2.0.1}


# Get directory of script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Go one level up to use project root as build context
CONTEXT_DIR="$(dirname "$SCRIPT_DIR")"

docker build -f "$SCRIPT_DIR/Dockerfile" -t "$IMAGE_NAME:$TAG" -t "$IMAGE_NAME:latest" "$CONTEXT_DIR"

docker login
# Push both tags
docker push "$IMAGE_NAME:$TAG"
docker push "$IMAGE_NAME:latest"

