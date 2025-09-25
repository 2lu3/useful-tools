#!/usr/bin/env python3
"""
2_filter_missing_metadata.py - Check for missing metadata in image files
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from loguru import logger
from alive_progress import alive_bar
from PIL import Image
from PIL.ExifTags import TAGS
import exifread


def get_exif_datetime(image_path: Path) -> Optional[str]:
    """Extract datetime information from EXIF data."""
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            
        datetime_fields = [
            'EXIF DateTime',
            'EXIF DateTimeOriginal', 
            'EXIF DateTimeDigitized',
            'Image DateTime'
        ]
        
        for field in datetime_fields:
            if field in tags:
                return str(tags[field])
                
    except Exception as e:
        logger.debug(f"Error reading EXIF datetime from {image_path}: {e}")
    
    return None


def get_exif_location(image_path: Path) -> Optional[Tuple[float, float, Optional[float]]]:
    """Extract GPS location from EXIF data."""
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            
        # Check for GPS tags
        gps_latitude = tags.get('GPS GPSLatitude')
        gps_latitude_ref = tags.get('GPS GPSLatitudeRef')
        gps_longitude = tags.get('GPS GPSLongitude')
        gps_longitude_ref = tags.get('GPS GPSLongitudeRef')
        gps_altitude = tags.get('GPS GPSAltitude')
        
        if gps_latitude and gps_longitude:
            # Convert to decimal degrees
            lat = convert_to_decimal_degrees(gps_latitude, gps_latitude_ref)
            lon = convert_to_decimal_degrees(gps_longitude, gps_longitude_ref)
            alt = float(gps_altitude) if gps_altitude else None
            
            return (lat, lon, alt)
            
    except Exception as e:
        logger.debug(f"Error reading EXIF GPS from {image_path}: {e}")
    
    return None


def convert_to_decimal_degrees(coord, ref):
    """Convert GPS coordinates to decimal degrees."""
    try:
        # Parse the coordinate string
        coord_str = str(coord)
        ref_str = str(ref)
        
        # Extract degrees, minutes, seconds
        parts = coord_str.replace('[', '').replace(']', '').split(', ')
        degrees = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        
        # Calculate decimal degrees
        decimal = degrees + minutes/60 + seconds/3600
        
        # Apply reference (N/S, E/W)
        if ref_str in ['S', 'W']:
            decimal = -decimal
            
        return decimal
        
    except Exception as e:
        logger.debug(f"Error converting coordinates: {e}")
        return None


def get_file_creation_time(file_path: Path) -> Optional[str]:
    """Get file creation time."""
    try:
        stat = file_path.stat()
        return str(stat.st_ctime)
    except Exception as e:
        logger.debug(f"Error getting file creation time for {file_path}: {e}")
        return None


def analyze_image_metadata(image_path: Path) -> Dict[str, Any]:
    """Analyze metadata for a single image file."""
    result = {
        "datetime": {
            "exif_datetime": None,
            "exif_datetime_original": None,
            "exif_datetime_digitized": None,
            "file_creation_time": None,
            "json_datetime": None
        },
        "location": {
            "latitude": None,
            "longitude": None,
            "altitude": None,
            "exif_gps": False,
            "json_location": False
        },
        "has_datetime": False,
        "has_location": False,
        "metadata_sources": []
    }
    
    # Check EXIF datetime
    exif_datetime = get_exif_datetime(image_path)
    if exif_datetime:
        result["datetime"]["exif_datetime"] = exif_datetime
        result["metadata_sources"].append("exif")
        result["has_datetime"] = True
    
    # Check EXIF location
    location = get_exif_location(image_path)
    if location:
        lat, lon, alt = location
        result["location"]["latitude"] = lat
        result["location"]["longitude"] = lon
        result["location"]["altitude"] = alt
        result["location"]["exif_gps"] = True
        result["has_location"] = True
        if "exif" not in result["metadata_sources"]:
            result["metadata_sources"].append("exif")
    
    # Check file creation time
    file_time = get_file_creation_time(image_path)
    if file_time:
        result["datetime"]["file_creation_time"] = file_time
        if not result["has_datetime"]:
            result["has_datetime"] = True
    
    return result


def main():
    """Main function."""
    # Setup logging
    logger.remove()
    logger.add("output/filter_metadata.log", rotation="10 MB", level="INFO")
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    
    # Setup paths
    output_dir = Path("output")
    images_dir = output_dir / "images"
    metadata_file = output_dir / "metadata.json"
    
    logger.info("Starting metadata analysis")
    
    # Check if images directory exists
    if not images_dir.exists():
        logger.error(f"Images directory {images_dir} does not exist")
        return
    
    # Get all image files
    image_files = [f for f in images_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif']]
    
    logger.info(f"Found {len(image_files)} image files to analyze")
    
    # Analyze metadata for each image
    metadata = {}
    
    with alive_bar(len(image_files), title="Analyzing metadata") as bar:
        for image_path in image_files:
            try:
                filename = image_path.name
                metadata[filename] = analyze_image_metadata(image_path)
                bar()
                
            except Exception as e:
                logger.error(f"Error analyzing {image_path}: {e}")
                bar()
    
    # Save metadata to JSON
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Log summary
    total_images = len(metadata)
    images_with_datetime = sum(1 for m in metadata.values() if m["has_datetime"])
    images_with_location = sum(1 for m in metadata.values() if m["has_location"])
    
    logger.info(f"Metadata analysis complete")
    logger.info(f"Total images: {total_images}")
    logger.info(f"Images with datetime: {images_with_datetime}")
    logger.info(f"Images with location: {images_with_location}")
    logger.info(f"Metadata saved to {metadata_file}")


if __name__ == "__main__":
    main()