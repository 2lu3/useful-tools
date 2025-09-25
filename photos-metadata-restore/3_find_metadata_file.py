#!/usr/bin/env python3
"""
3_find_metadata_file.py - Find metadata files for images
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from loguru import logger
from alive_progress import alive_bar


def load_pair_json(pair_file: Path) -> List[Dict[str, Any]]:
    """Load pair.json file to get source-destination mappings."""
    try:
        with open(pair_file, "r", encoding="utf-8") as f:
            pairs = json.load(f)
        logger.info(f"Loaded {len(pairs)} file pairs from {pair_file}")
        return pairs
    except Exception as e:
        logger.error(f"Error loading pair.json: {e}")
        return []


def find_metadata_files_for_image(source_path: Path) -> List[Dict[str, Any]]:
    """Find potential metadata files for a given image source path."""
    metadata_files = []
    
    # Get the directory and filename without extension
    source_dir = source_path.parent
    filename_without_ext = source_path.stem
    
    # Common metadata file patterns to check
    metadata_patterns = [
        # Same directory, same filename with different extensions
        f"{filename_without_ext}.json",
        f"{filename_without_ext}.metadata.json",
        f"{filename_without_ext}.supplemental-metadata.json",
        f"{filename_without_ext}.metadata",
        f"{filename_without_ext}.exif",
        
        # Same directory, different naming patterns
        f"{filename_without_ext}.jpg.json",
        f"{filename_without_ext}.jpeg.json",
        f"{filename_without_ext}.png.json",
        
        # Parent directory patterns
        f"{source_dir.parent.name}.json",
        f"{source_dir.parent.name}.metadata.json",
        
        # Common metadata filenames
        "metadata.json",
        "photo-metadata.json",
        "image-metadata.json",
        "exif-data.json",
        "photo-info.json"
    ]
    
    # Check each pattern
    for pattern in metadata_patterns:
        metadata_path = source_dir / pattern
        if metadata_path.exists():
            metadata_files.append({
                "path": str(metadata_path),
                "filename": pattern,
                "type": "file",
                "found": True,
                "file_exists": True
            })
    
    # Also check for directories that might contain metadata
    metadata_dirs = [
        source_dir / "metadata",
        source_dir / "photo-metadata", 
        source_dir / "image-metadata",
        source_dir.parent / "metadata",
        source_dir.parent / "photo-metadata",
        source_dir.parent / "image-metadata"
    ]
    
    for metadata_dir in metadata_dirs:
        if metadata_dir.exists() and metadata_dir.is_dir():
            # Look for files that might match our image
            for file in metadata_dir.iterdir():
                if file.is_file() and (filename_without_ext in file.name or file.suffix == '.json'):
                    metadata_files.append({
                        "path": str(file),
                        "filename": file.name,
                        "type": "directory",
                        "found": True,
                        "file_exists": True
                    })
    
    return metadata_files


def analyze_metadata_file_structure(metadata_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze the structure of found metadata files to understand patterns."""
    analysis = {
        "total_files": len(metadata_files),
        "file_types": {},
        "common_patterns": {},
        "directory_structure": {},
        "file_extensions": {}
    }
    
    for metadata_file in metadata_files:
        path = Path(metadata_file["path"])
        
        # Count file types
        file_type = metadata_file.get("type", "unknown")
        analysis["file_types"][file_type] = analysis["file_types"].get(file_type, 0) + 1
        
        # Count file extensions
        ext = path.suffix.lower()
        analysis["file_extensions"][ext] = analysis["file_extensions"].get(ext, 0) + 1
        
        # Analyze directory structure
        parent_dir = path.parent.name
        analysis["directory_structure"][parent_dir] = analysis["directory_structure"].get(parent_dir, 0) + 1
        
        # Analyze filename patterns
        filename = path.name
        if "metadata" in filename.lower():
            analysis["common_patterns"]["contains_metadata"] = analysis["common_patterns"].get("contains_metadata", 0) + 1
        if "supplemental" in filename.lower():
            analysis["common_patterns"]["contains_supplemental"] = analysis["common_patterns"].get("contains_supplemental", 0) + 1
        if "exif" in filename.lower():
            analysis["common_patterns"]["contains_exif"] = analysis["common_patterns"].get("contains_exif", 0) + 1
    
    return analysis


def main():
    """Main function."""
    # Setup logging
    logger.remove()
    logger.add("output/find_metadata.log", rotation="10 MB", level="INFO")
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    
    # Setup paths
    output_dir = Path("output")
    pair_file = output_dir / "pair.json"
    metadata_location_file = output_dir / "metadata_location.json"
    
    logger.info("Starting metadata file search")
    
    # Check if pair.json exists
    if not pair_file.exists():
        logger.error(f"Pair file {pair_file} does not exist. Run 1_copy_files.py first.")
        return
    
    # Load pair information
    pairs = load_pair_json(pair_file)
    if not pairs:
        logger.error("No pairs found in pair.json")
        return
    
    logger.info(f"Searching for metadata files for {len(pairs)} images")
    
    # Find metadata files for each image
    metadata_locations = {}
    all_metadata_files = []
    
    with alive_bar(len(pairs), title="Finding metadata files") as bar:
        for pair in pairs:
            try:
                source_path = Path(pair["source"])
                filename = pair["filename"]
                
                # Find metadata files for this image
                metadata_files = find_metadata_files_for_image(source_path)
                
                if metadata_files:
                    # Use the first found metadata file
                    primary_metadata = metadata_files[0]
                    metadata_locations[filename] = {
                        "original_source": str(source_path),
                        "metadata_file": primary_metadata["path"],
                        "metadata_type": primary_metadata["type"],
                        "found": True,
                        "file_exists": True,
                        "all_metadata_files": metadata_files
                    }
                    all_metadata_files.extend(metadata_files)
                else:
                    metadata_locations[filename] = {
                        "original_source": str(source_path),
                        "metadata_file": None,
                        "metadata_type": None,
                        "found": False,
                        "file_exists": False,
                        "all_metadata_files": []
                    }
                
                bar()
                
            except Exception as e:
                logger.error(f"Error processing {pair.get('source', 'unknown')}: {e}")
                bar()
    
    # Analyze metadata file structure
    if all_metadata_files:
        analysis = analyze_metadata_file_structure(all_metadata_files)
        logger.info("Metadata file structure analysis:")
        logger.info(f"Total metadata files found: {analysis['total_files']}")
        logger.info(f"File types: {analysis['file_types']}")
        logger.info(f"File extensions: {analysis['file_extensions']}")
        logger.info(f"Directory structure: {analysis['directory_structure']}")
        logger.info(f"Common patterns: {analysis['common_patterns']}")
    
    # Save metadata locations
    with open(metadata_location_file, "w", encoding="utf-8") as f:
        json.dump(metadata_locations, f, indent=2, ensure_ascii=False)
    
    # Log summary
    total_images = len(metadata_locations)
    images_with_metadata = sum(1 for m in metadata_locations.values() if m["found"])
    images_without_metadata = total_images - images_with_metadata
    
    logger.info(f"Metadata file search complete")
    logger.info(f"Total images: {total_images}")
    logger.info(f"Images with metadata files: {images_with_metadata}")
    logger.info(f"Images without metadata files: {images_without_metadata}")
    logger.info(f"Metadata locations saved to {metadata_location_file}")
    
    if images_without_metadata > 0:
        logger.warning(f"{images_without_metadata} images have no associated metadata files")
        logger.info("Consider checking the following patterns for metadata files:")
        logger.info("- Same directory, same filename with .json extension")
        logger.info("- Same directory, filename with .metadata.json extension")
        logger.info("- Same directory, filename with .supplemental-metadata.json extension")
        logger.info("- Parent directory with metadata/ or photo-metadata/ subdirectories")


if __name__ == "__main__":
    main()