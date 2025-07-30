#!/bin/bash

pdftoppm -jpeg -r 300 $1 "tmp/image"

# convert jpg to jpeg

for file in tmp/image-*.jpg; do
    mv "$file" "${file%.jpg}.jpeg"
done
