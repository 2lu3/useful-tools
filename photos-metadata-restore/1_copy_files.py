#!/usr/bin/env python3
"""
1_copy_files.py - Copy image files to output directory with hash-based naming
"""

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any

from loguru import logger
from alive_progress import alive_bar


def get_all_extensions(directory: Path) -> List[str]:
    """Get all file extensions in the directory recursively."""
    extensions = set()
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            extensions.add(file_path.suffix.lower())
    return sorted(list(extensions))


def get_image_extensions() -> List[str]:
    """Get list of image file extensions."""
    return [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", 
        ".webp", ".svg", ".ico", ".heic", ".heif", ".raw", ".cr2", 
        ".nef", ".arw", ".dng", ".orf", ".rw2", ".pef", ".srw"
    ]


def get_video_extensions() -> List[str]:
    """Get list of video file extensions."""
    return [
        ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv", 
        ".m4v", ".3gp", ".ogv", ".mts", ".m2ts", ".ts"
    ]


def is_image_file(file_path: Path) -> bool:
    """Check if file is an image based on extension."""
    return file_path.suffix.lower() in get_image_extensions()


def calculate_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def copy_files_with_hash(input_dir: Path, output_dir: Path) -> List[Dict[str, Any]]:
    """Copy image files to output directory with hash-based naming."""
    pairs = []
    
    # Get all image files
    image_files = [f for f in input_dir.rglob("*") if f.is_file() and is_image_file(f)]
    
    logger.info(f"Found {len(image_files)} image files to process")
    
    with alive_bar(len(image_files), title="Copying files") as bar:
        for file_path in image_files:
            try:
                # Calculate hash
                file_hash = calculate_file_hash(file_path)
                
                # Create new filename
                new_filename = f"{file_hash}{file_path.suffix}"
                output_path = output_dir / new_filename
                
                # Copy file
                shutil.copy2(file_path, output_path)
                
                # Store pair information
                pair = {
                    "source": str(file_path),
                    "destination": str(output_path),
                    "filename": new_filename,
                    "hash": file_hash
                }
                pairs.append(pair)
                
                bar()
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                bar()
    
    return pairs


def main():
    """Main function."""
    # Setup logging
    logger.remove()
    logger.add("output/copy_files.log", rotation="10 MB", level="INFO")
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    
    # Setup paths
    input_dir = Path("input")
    output_dir = Path("output")
    images_dir = output_dir / "images"
    
    # Create output directories
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    images_dir.mkdir()
    
    logger.info("Starting file copy process")
    
    # Check if input directory exists
    if not input_dir.exists():
        logger.error(f"Input directory {input_dir} does not exist")
        return
    
    # Get all extensions in input directory
    all_extensions = get_all_extensions(input_dir)
    image_extensions = get_image_extensions()
    video_extensions = get_video_extensions()
    
    logger.info(f"Found {len(all_extensions)} unique file extensions")
    logger.info(f"Image extensions: {image_extensions}")
    logger.info(f"Video extensions: {video_extensions}")
    
    # Find non-image, non-video extensions
    other_extensions = [ext for ext in all_extensions 
                       if ext not in image_extensions and ext not in video_extensions]
    
    if other_extensions:
        logger.info(f"Non-image, non-video extensions found: {other_extensions}")
    
    # Copy files
    pairs = copy_files_with_hash(input_dir, images_dir)
    
    # Save pairs to JSON
    pairs_file = output_dir / "pair.json"
    with open(pairs_file, "w", encoding="utf-8") as f:
        json.dump(pairs, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Copied {len(pairs)} files to {images_dir}")
    logger.info(f"Pair information saved to {pairs_file}")


if __name__ == "__main__":
    main()