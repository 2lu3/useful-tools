#!/bin/bash

# Create input directory if it doesn't exist
if [ ! -d "input" ]; then
    mkdir -p input
fi

# Create output directory structure
if [ ! -d "output" ]; then
    mkdir -p output
else
    rm -rf output/*
fi

# Create subdirectories in output
mkdir -p output/image
mkdir -p output/text
mkdir -p output/log
mkdir -p output/pdf
