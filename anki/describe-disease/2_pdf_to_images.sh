#!/bin/bash

pdftoppm -jpeg -r 300 input/data.pdf "tmp/image/"

# convert jpg to jpeg and remove leading dash
for file in tmp/image/-*.jpg; do
    # Remove leading dash and convert to jpeg
    new_name=$(echo "$file" | sed 's|tmp/image/-|tmp/image/|' | sed 's|\.jpg$|.jpeg|')
    mv "$file" "$new_name"
done
