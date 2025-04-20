#!/usr/bin/env python3
"""
Adventure Minecraft Mod Downloader

This script downloads all the mods needed for Adventure Minecraft modpack.
It organizes downloads by category and provides progress tracking.
"""

import os
import sys
import subprocess
import argparse
import json
import time
import zipfile
import io
import requests
import hashlib
from pathlib import Path
import shutil


def get_script_dir():
    """Get the directory where this script is located"""
    return os.path.dirname(os.path.abspath(__file__))


def get_root_dir():
    """Get the root directory of the project"""
    script_dir = get_script_dir()
    return os.path.abspath(os.path.join(script_dir, '..'))


# Define paths
SCRIPT_DIR = get_script_dir()
ROOT_DIR = get_root_dir()
MODS_DIR = os.path.join(ROOT_DIR, "server", "mods")  # Primary mods directory
CACHE_DIR = os.path.join(SCRIPT_DIR, "mod_cache")  # Set to scripts/mod_cache as per request
MODPACK_DIR = os.path.join(SCRIPT_DIR, "modpack_profiles")
PROGRESS_FILE = os.path.join(CACHE_DIR, "download_progress.json")

# Minecraft version and loader
MC_VERSION = "1.21.5"
LOADER = "fabric"


def ensure_directories():
    """Ensure all required directories exist"""
    os.makedirs(MODS_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(MODPACK_DIR, exist_ok=True)


def load_progress():
    """Load download progress from file"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"categories": {}}
    return {"categories": {}}


def save_progress(progress):
    """Save download progress to file"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def clean_mods_directory():
    """Clean existing mods directory, preserving Fabric API"""
    print("Cleaning existing mods directory...")
    
    # Preserve Fabric API
    fabric_api_path = os.path.join(MODS_DIR, "fabric-api-1.21.5.jar")
    fabric_api_backup = None
    
    if os.path.exists(fabric_api_path):
        print("Preserving Fabric API...")
        fabric_api_backup = "/tmp/fabric-api-1.21.5.jar"
        shutil.copy2(fabric_api_path, fabric_api_backup)
    
    # Remove all .jar files
    for item in os.listdir(MODS_DIR):
        if item.endswith('.jar'):
            os.remove(os.path.join(MODS_DIR, item))
    
    # Restore Fabric API if backed up
    if fabric_api_backup and os.path.exists(fabric_api_backup):
        print("Restoring Fabric API...")
        shutil.copy2(fabric_api_backup, fabric_api_path)
        os.remove(fabric_api_backup)


def download_mod(category, search_term, limit=1, force_download=False):
    """Download a specific mod category"""
    print(f"Downloading {category} mods...")
    
    # Build command arguments
    cmd = [
        "python3", 
        os.path.join(SCRIPT_DIR, "mod_explorer.py"),
        "--source", "modrinth",
        "--mc-version", MC_VERSION,
        "--loader", LOADER,
        "--search", search_term,
        "--limit", str(limit),
        "--download",
        "--output", MODS_DIR,
        "--cache-dir", CACHE_DIR
    ]
    
    if force_download:
        cmd.append("--force-download")
    
    # Get list of mods before download
    mods_before = set(os.listdir(MODS_DIR))
    
    # Run the command
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Successfully downloaded mod(s)!")
        
        # Check for newly downloaded .mrpack files and extract them immediately
        mods_after = set(os.listdir(MODS_DIR))
        new_files = mods_after - mods_before
        
        new_mrpack_files = [f for f in new_files if f.endswith('.mrpack')]
        if new_mrpack_files:
            print(f"Found {len(new_mrpack_files)} new .mrpack files, extracting them now...")
            for mrpack_file in new_mrpack_files:
                extract_mrpack(os.path.join(MODS_DIR, mrpack_file), MODS_DIR)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to download mod(s): {e}")
        print(f"Error output: {e.stderr}")
        return False


def download_specific_mod(category, mod_id, source="modrinth", force_download=False):
    """Download a specific mod by ID"""
    print(f"Downloading {category} mod...")
    
    # Build command arguments
    cmd = [
        "python3", 
        os.path.join(SCRIPT_DIR, "mod_explorer.py"),
        "--download-id", mod_id,
        "--download-source", source,
        "--mc-version", MC_VERSION,
        "--loader", LOADER,
        "--output", MODS_DIR,
        "--cache-dir", CACHE_DIR
    ]
    
    if force_download:
        cmd.append("--force-download")
    
    # Get list of mods before download
    mods_before = set(os.listdir(MODS_DIR))
    
    # Run the command
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Successfully downloaded mod!")
        
        # Check for newly downloaded .mrpack files and extract them immediately
        mods_after = set(os.listdir(MODS_DIR))
        new_files = mods_after - mods_before
        
        new_mrpack_files = [f for f in new_files if f.endswith('.mrpack')]
        if new_mrpack_files:
            print(f"Found {len(new_mrpack_files)} new .mrpack files, extracting them now...")
            for mrpack_file in new_mrpack_files:
                extract_mrpack(os.path.join(MODS_DIR, mrpack_file), MODS_DIR)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to download mod: {e}")
        print(f"Error output: {e.stderr}")
        return False


def should_replace_mod(filename, existing_file_path):
    """
    Determine if a mod should be replaced with a newer version.
    Returns True if the mod should be replaced, False otherwise.
    
    This function uses version information in the filename to make a decision.
    """
    # If the file doesn't exist, we should "replace" it (actually add it)
    if not os.path.exists(existing_file_path):
        return True
    
    # Handle specific mods with version numbers in the filename
    try:
        # Most fabric mods follow the pattern modname-x.y.z+mc1.xx.x-fabric.jar
        # Extract the version from the filename
        existing_version = extract_version_from_filename(os.path.basename(existing_file_path))
        new_version = extract_version_from_filename(filename)
        
        # If we successfully extracted versions, compare them
        if existing_version and new_version:
            # Default to not replacing if versions can't be clearly compared
            if existing_version == new_version:
                return False  # Same version, don't replace
            
            # Try to compare version numbers
            try:
                # Split version into parts
                existing_parts = existing_version.split('.')
                new_parts = new_version.split('.')
                
                # Compare parts (if 1.2.3 vs 1.3.0, 1.3.0 is newer)
                for i in range(min(len(existing_parts), len(new_parts))):
                    try:
                        existing_num = int(existing_parts[i])
                        new_num = int(new_parts[i])
                        
                        if new_num > existing_num:
                            return True  # New version is higher
                        elif new_num < existing_num:
                            return False  # Existing version is higher
                    except ValueError:
                        # Not numeric parts, can't compare directly
                        pass
                        
                # If all checked parts are equal but one has more parts, longer is usually newer
                if len(new_parts) > len(existing_parts):
                    return True
            except Exception:
                # If comparison fails, be conservative
                return False
    except Exception:
        # If we can't parse the version, don't replace
        return False
    
    # Default: don't replace if we can't determine
    return False


def extract_version_from_filename(filename):
    """Extract version string from the filename."""
    # Try to extract version using common patterns
    import re
    
    # Pattern 1: modname-1.2.3.jar
    match = re.search(r'-(\d+\.\d+\.\d+(\.\d+)?)', filename)
    if match:
        return match.group(1)
    
    # Pattern 2: modname-fabric-1.2.3.jar
    match = re.search(r'fabric-(\d+\.\d+\.\d+(\.\d+)?)', filename)
    if match:
        return match.group(1)
    
    # Pattern 3: modname-v1.2.3.jar
    match = re.search(r'-v(\d+\.\d+\.\d+(\.\d+)?)', filename)
    if match:
        return match.group(1)
    
    # No version pattern found
    return None


def fix_biome_spreader():
    """Fix for biome-spreader issue"""
    print("Checking for biome-spreader mod filename issues...")
    
    # First check for spaces in BiomeSpreader filenames
    for filename in os.listdir(MODS_DIR):
        if ("biome-spreader" in filename.lower() or "biomespreader" in filename.lower()) and " " in filename and filename.endswith(".jar"):
            biome_spreader_file = os.path.join(MODS_DIR, filename)
            biome_spreader_correct_name = biome_spreader_file.replace(" ", "-")
            
            if biome_spreader_file != biome_spreader_correct_name:
                print(f"Renaming {biome_spreader_file} to {biome_spreader_correct_name}")
                os.rename(biome_spreader_file, biome_spreader_correct_name)
    
    # Check if BiomeSpreader is using the correct filename format
    for filename in os.listdir(MODS_DIR):
        if "BiomeSpreader-1.5.0+mc1.21.5.jar" in filename:
            # Create a symbolic link with the exact name the mod is looking for
            src = os.path.join(MODS_DIR, filename)
            dest = os.path.join(MODS_DIR, "BiomeSpreader-1.5.0 mc1.21.5.jar")
            if not os.path.exists(dest):
                print(f"Creating a copy from {filename} to 'BiomeSpreader-1.5.0 mc1.21.5.jar'")
                shutil.copy2(src, dest)


def cleanup_mods():
    """Clean up duplicate and incompatible mods"""
    print("Cleaning up duplicate mods...")
    
    # Remove files with parentheses in the name (duplicates)
    for filename in os.listdir(MODS_DIR):
        if '(' in filename and ')' in filename and filename.endswith('.jar'):
            os.remove(os.path.join(MODS_DIR, filename))
    
    # Create a dictionary to track duplicates by mod name
    mod_versions = {}
    
    # Identify duplicates by base name
    for filename in os.listdir(MODS_DIR):
        if not filename.endswith('.jar'):
            continue
            
        # Get base mod name by removing version and variants
        base_name = get_base_mod_name(filename)
        if not base_name:
            continue
            
        if base_name not in mod_versions:
            mod_versions[base_name] = []
        
        mod_versions[base_name].append(filename)
    
    # Clean up duplicates, keeping only the newest version
    for base_name, versions in mod_versions.items():
        if len(versions) <= 1:
            continue
            
        print(f"Found {len(versions)} versions of {base_name}: {', '.join(versions)}")
        
        # Sort versions by filename (approximate, but usually works)
        sorted_versions = sorted(versions, key=lambda x: x)
        newest_version = sorted_versions[-1]
        
        # Try to find the newest version by checking the version numbers
        for version in versions:
            for other_version in versions:
                if version != other_version and should_replace_mod(version, os.path.join(MODS_DIR, other_version)):
                    newest_version = version
        
        print(f"  Keeping newest version: {newest_version}")
        
        # Remove other versions
        for version in versions:
            if version != newest_version:
                file_path = os.path.join(MODS_DIR, version)
                if os.path.exists(file_path):
                    print(f"  Removing duplicate: {version}")
                    os.remove(file_path)
    
    print("Filtering out known incompatible mods for the server...")
    incompatible_patterns = [
        # Client-side rendering/UI mods that cause server issues
        "Axiom", "axiom", "dungeondodgeplus", "tweakermore", "mutantmonsters", "MutantMonsters",
        
        # Client-side functionality mods that should only be on client
        "flashside", "visible-entities", "visible", "modelfix", "Gamma-Utils", "gamma",
        "lambdynamiclights", "dynamic-lights", "Zoomify", "zoom", "f3teverywhere", "f3",
        "BetterF3", "morechathistory", "chat_heads", "chat-heads", "iris", "sodium",
        "reeses-sodium", "sodium-extra", "skinlayers3d", "skinlayers", "notenoughanimations",
        "capes", "entity_model_features", "entity_texture_features", "xaerominimap", "Xaeros",
        "minecartsloadchunks",
        
        # Known problematic mods that cause server crashes or issues
        "dungeons-and-taverns", "adventuremodetweaks", "attributerpgfied", "nemos-carpentry",
        "structurevoidable", "structure_void_toggle", "structure_void", "mutantmonsters", "MutantMonsters", 
        "monsters_in_the_closet", "monsters-in-the-closet", "c2me-opts-natives-math",
        
        # Mods with missing dependencies or compatibility issues
        "biomereplacer", "rpg-stash", "takesarmory", "combat-control", 
        "more_tools_and_armor", "mstv-", "dcqinv", "monsters_in_the_closet", 
        "combatamenities", "betterchromakey", "inventoryprofilesnext", "magic-bundle"
    ]
    
    for pattern in incompatible_patterns:
        for filename in os.listdir(MODS_DIR):
            if pattern in filename and filename.endswith('.jar'):
                file_path = os.path.join(MODS_DIR, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)


def get_base_mod_name(filename):
    """
    Extract the base mod name from a filename.
    Examples:
    - fabric-api-0.120.0+1.21.5.jar -> fabric-api
    - lithium-fabric-0.16.2+mc1.21.5.jar -> lithium
    - sodium-fabric-0.6.12+mc1.21.5.jar -> sodium
    """
    import re
    
    # Remove .jar extension
    name = filename.lower().replace('.jar', '')
    
    # Try common patterns
    
    # Pattern: mod-fabric-version
    match = re.match(r'([a-z0-9_-]+)-fabric', name)
    if match:
        return match.group(1)
    
    # Pattern: fabric-mod-version
    match = re.match(r'fabric-([a-z0-9_-]+)', name)
    if match:
        return f"fabric-{match.group(1)}"
    
    # Pattern: mod-version
    match = re.match(r'([a-z0-9_-]+)-\d', name)
    if match:
        return match.group(1)
    
    # Handle special cases
    if "api" in name:
        if "fabric-api" in name:
            return "fabric-api"
    
    # If we can't determine, return None
    return None


def save_mod_list():
    """Save installed mod list to profile"""
    adventure_pack_file = os.path.join(MODPACK_DIR, "adventure_pack.txt")
    
    # Check if adventure_pack.txt file already exists
    if os.path.exists(adventure_pack_file):
        print(f"Using existing mod list from {adventure_pack_file}")
        return
    
    # If it doesn't exist, create a new one
    with open(adventure_pack_file, 'w') as f:
        f.write("# Adventure Minecraft - Adventure Pack 1.21.5\n")
        f.write("# This file contains a list of mods for the Adventure Minecraft modpack\n")
        f.write("# \n")
        f.write("# Mod Categories:\n")
        f.write("# [server] - Server-side only mods\n")
        f.write("# [client] - Client-side only mods\n")
        f.write("# [shared] - Mods needed on both server and client\n\n")
        
        f.write("# --- Mods ---\n")
        for filename in sorted(os.listdir(MODS_DIR)):
            # Include both .jar files and .mrpack files in the profile
            if filename.endswith('.jar') or filename.endswith('.mrpack'):
                f.write(f"[shared] {filename}\n")


def extract_mrpack(mrpack_file, extract_dir):
    """
    Extract and process an .mrpack file
    
    mrpack files are zip archives containing a modrinth.index.json file and mod files.
    This function extracts the mods and configuration files to the appropriate directories.
    """
    print(f"Processing modpack: {os.path.basename(mrpack_file)}")
    
    # Create a temporary directory for extraction
    temp_dir = os.path.join(CACHE_DIR, "temp_mrpack_extract")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    # Extract the mrpack file
    with zipfile.ZipFile(mrpack_file, 'r') as zipf:
        # Extract the index file first
        try:
            zipf.extract("modrinth.index.json", temp_dir)
        except KeyError:
            print(f"Error: Invalid mrpack file format - missing modrinth.index.json in {mrpack_file}")
            return False
        
        # Load and parse the index file
        with open(os.path.join(temp_dir, "modrinth.index.json"), 'r') as f:
            try:
                index = json.load(f)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in modrinth.index.json from {mrpack_file}")
                return False
        
        # Verify format version
        if index.get("formatVersion") != 1:
            print(f"Warning: Unknown modpack format version {index.get('formatVersion')}")
        
        # Print modpack info
        modpack_name = index.get("name", "Unknown Modpack")
        minecraft_version = index.get("dependencies", {}).get("minecraft", "Unknown")
        modloader = index.get("dependencies", {}).get("fabric", index.get("dependencies", {}).get("forge", "Unknown"))
        print(f"  Modpack: {modpack_name}")
        print(f"  Minecraft: {minecraft_version}")
        print(f"  Modloader: {modloader}")
        
        # Process files from the index
        processed_count = 0
        for file_entry in index.get("files", []):
            path = file_entry.get("path", "")
            
            # Skip client-only files when extracting for server
            env = file_entry.get("env", {})
            if env.get("server") == "unsupported":
                print(f"  Skipping client-only file: {path}")
                continue
            
            # Check if path is a mod
            if path.endswith(".jar") and ("mods/" in path or path.startswith("mods/")):
                mod_filename = os.path.basename(path)
                download_urls = file_entry.get("downloads", [])
                
                # Skip if no download URLs
                if not download_urls:
                    print(f"  Warning: No download URLs for {mod_filename}")
                    continue
                
                print(f"  Processing mod: {mod_filename}")
                
                # Check if mod already exists in mods directory
                if os.path.exists(os.path.join(extract_dir, mod_filename)):
                    # Check if the existing mod is an older version
                    if should_replace_mod(mod_filename, os.path.join(extract_dir, mod_filename)):
                        print(f"  Replacing existing mod {mod_filename} with newer version")
                        os.remove(os.path.join(extract_dir, mod_filename))
                    else:
                        print(f"  Mod {mod_filename} already exists in mods directory, skipping")
                        processed_count += 1
                        continue
                
                # Check if mod already exists in cache
                cache_file = os.path.join(CACHE_DIR, mod_filename)
                if os.path.exists(cache_file):
                    print(f"  Using cached version of {mod_filename}")
                    shutil.copy2(cache_file, os.path.join(extract_dir, mod_filename))
                    processed_count += 1
                    continue
                
                # Download the mod
                for download_url in download_urls:
                    try:
                        print(f"  Downloading {mod_filename} from {download_url}")
                        response = requests.get(download_url, stream=True)
                        response.raise_for_status()
                        
                        # Save to mods directory
                        with open(os.path.join(extract_dir, mod_filename), 'wb') as out_file:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    out_file.write(chunk)
                        
                        # Also save to cache
                        shutil.copy2(os.path.join(extract_dir, mod_filename), cache_file)
                        
                        processed_count += 1
                        break  # Stop after successful download
                    except Exception as e:
                        print(f"  Error downloading {mod_filename}: {str(e)}")
                        # Continue to next URL if available
        
        # Extract override files if present
        for override_dir in ["overrides", "server-overrides"]:
            for file_info in zipf.infolist():
                if file_info.filename.startswith(f"{override_dir}/"):
                    # Remove the override directory prefix
                    relative_path = file_info.filename[len(f"{override_dir}/"):]
                    if not relative_path:
                        continue  # Skip the directory itself
                    
                    # Determine the target path
                    target_path = os.path.join(ROOT_DIR, relative_path)
                    
                    # Create directories if needed
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    # Extract the file
                    source = zipf.read(file_info.filename)
                    with open(target_path, 'wb') as target_file:
                        target_file.write(source)
        
        print(f"Modpack processing complete: {processed_count} mods installed from {modpack_name}")
    
    # Clean up temporary directory
    shutil.rmtree(temp_dir)
    
    # Move the original .mrpack file to cache and remove from mods directory
    mrpack_filename = os.path.basename(mrpack_file)
    cache_mrpack = os.path.join(CACHE_DIR, mrpack_filename)
    if not os.path.exists(cache_mrpack):
        shutil.copy2(mrpack_file, cache_mrpack)
    
    # Remove the .mrpack file from the mods directory
    print(f"  Removing {mrpack_filename} from mods directory (saved in cache)")
    os.remove(mrpack_file)
    
    return True


def process_mrpack_files():
    """Process all .mrpack files in the mods directory"""
    mrpack_files = [f for f in os.listdir(MODS_DIR) if f.endswith('.mrpack')]
    if not mrpack_files:
        return
    
    print("\n=== Processing Modpack Files ===")
    for mrpack_file in mrpack_files:
        extract_mrpack(os.path.join(MODS_DIR, mrpack_file), MODS_DIR)


def print_summary():
    """Print summary information about the installation"""
    mod_count = len([f for f in os.listdir(MODS_DIR) if f.endswith('.jar')])
    mrpack_count = len([f for f in os.listdir(MODS_DIR) if f.endswith('.mrpack')])
    cache_count = len([f for f in os.listdir(CACHE_DIR) 
                      if os.path.isfile(os.path.join(CACHE_DIR, f)) and 
                      (f.endswith('.jar') or f.endswith('.mrpack'))])
    
    # Get cache size
    cache_size = sum(os.path.getsize(os.path.join(CACHE_DIR, f)) 
                     for f in os.listdir(CACHE_DIR) 
                     if os.path.isfile(os.path.join(CACHE_DIR, f)))
    cache_size_mb = cache_size / (1024 * 1024)
    
    print("\nUltimate Adventure Mod Pack installation complete!")
    
    # More detailed information about installed mods
    if mrpack_count > 0:
        print(f"Installed {mod_count} individual mods and {mrpack_count} modpacks in {MODS_DIR} directory.")
        print(f"All .mrpack files have been extracted, providing additional mods and configurations.")
    else:
        print(f"Installed {mod_count} mods in {MODS_DIR} directory.")
    
    print("""
=====================================================
ULTIMATE ADVENTURE MOD PACK INSTALLED!
=====================================================

Your adventure pack includes:
- Dungeon exploration and challenges
- Beautiful world generation with unique structures
- Quest and mission systems
- Epic boss battles and improved combat
- Unique animals and creatures
- Maps for navigation
- Performance improvements for smooth gameplay
- Quality of life features
- Furniture and decoration mods to enhance your builds

Restart your server to activate mods and enjoy your adventure!
""")
    
    print("Cache information:")
    print(f"- {cache_count} mods cached in {CACHE_DIR}")
    print(f"- Cache size: {cache_size_mb:.1f} MB")
    print("- To force download from remote sources, use the --force flag")


def download_from_profile(adventure_profile, progress, force=False):
    """Download mods directly from the adventure_pack.txt profile"""
    if not os.path.exists(adventure_profile):
        print(f"Error: Profile file {adventure_profile} not found!")
        return False
    
    success = True
    server_mods = []
    client_mods = []
    shared_mods = []
    
    print("\n=== Downloading mods from profile ===")
    
    # Read the profile and categorize mods
    with open(adventure_profile, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse mod type and filename
            parts = line.split(']', 1)
            print(f"Line {line_num}: {line}")
            print(f"Parts: {parts}")
            
            if len(parts) < 2 or not parts[0].startswith('['):
                print(f"Warning: Line {line_num} does not have the expected [type] format")
                continue
            
            mod_type = parts[0][1:].strip()
            mod_file = parts[1].strip()
            
            print(f"Parsed type: '{mod_type}', file: '{mod_file}'")
            
            if not mod_file:
                continue
            
            # Categorize by type
            if mod_type == "server":
                server_mods.append(mod_file)
            elif mod_type == "client":
                client_mods.append(mod_file)
            elif mod_type == "shared":
                shared_mods.append(mod_file)
    
    print(f"Server mods: {server_mods}")
    print(f"Client mods: {client_mods}")
    print(f"Shared mods: {shared_mods}")
    
    # Download server and shared mods
    for mod_list, mod_type in [(shared_mods, "shared"), (server_mods, "server")]:
        for mod_file in mod_list:
            # Check if mod already exists
            mod_path = os.path.join(MODS_DIR, mod_file)
            cache_path = os.path.join(CACHE_DIR, mod_file)
            
            if os.path.exists(mod_path) and not force:
                print(f"Skipping {mod_file} (already exists)")
                continue
            
            # Try to find the file in cache first
            if os.path.exists(cache_path) and not force:
                print(f"Using cached version of {mod_file}")
                shutil.copy2(cache_path, mod_path)
                continue
            
            # Otherwise, try to download it
            # Extract search terms from filename
            search_term = mod_file.split('-')[0].lower()
            
            if "fabric-api" in mod_file.lower():
                print("WARNING: Using static Fabric API version - do not download dynamically")
                # We assume Fabric API is already in the mods folder or will be downloaded manually
                continue
            
            # Download mod using mod_explorer.py
            if download_mod(f"{mod_type.capitalize()} Mod", search_term, 1, force):
                success = success and True
            else:
                success = False
    
    # Save client-only mods to cache for client pack creation
    for mod_file in client_mods:
        # Check if client mod already exists in cache
        cache_path = os.path.join(CACHE_DIR, mod_file)
        
        if os.path.exists(cache_path) and not force:
            print(f"Client-only mod {mod_file} already in cache")
            continue
        
        # Try to download client-only mod to cache
        search_term = mod_file.split('-')[0].lower()
        
        print(f"Downloading client-only mod {mod_file} to cache...")
        # Use a slightly modified version of download_mod that saves directly to cache
        
        # Build command arguments
        cmd = [
            "python3", 
            os.path.join(SCRIPT_DIR, "mod_explorer.py"),
            "--source", "modrinth",
            "--mc-version", MC_VERSION,
            "--loader", LOADER,
            "--search", search_term,
            "--limit", "1",
            "--download",
            "--output", CACHE_DIR,  # Save directly to cache
            "--cache-dir", CACHE_DIR
        ]
        
        if force:
            cmd.append("--force-download")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"Successfully downloaded client-only mod to cache: {mod_file}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to download client-only mod {mod_file}: {e}")
            print(f"Error output: {e.stderr}")
            success = False
    
    return success


def download_category(name, progress, force=False, profile_name="adventure_pack.txt"):
    """Download a category of mods and update progress"""
    # Check if we have a profile to use
    profile_path = os.path.join(MODPACK_DIR, profile_name)
    if os.path.exists(profile_path):
        if name == "from-profile":
            return download_from_profile(profile_path, progress, force)
        
        # If not explicitly asking for profile, but profile exists,
        # we'll still use it and ignore categories
        if name in progress["categories"] and progress["categories"][name] and not force:
            print(f"Skipping {name} (already downloaded)")
            return True
    else:
        # Use the traditional category-based approach
        if name in progress["categories"] and progress["categories"][name] and not force:
            print(f"Skipping {name} (already downloaded)")
            return True
    
    print(f"\n=== Downloading {name} ===")
    success = True
    
    if name == "essential-dependencies":
        print("WARNING: Using static Fabric API version - do not download dynamically")
        # IMPORTANT: We use a static version of Fabric API (fabric-api-1.21.5.jar)
        # DO NOT uncomment the following line as it might download an incompatible version
        # success = download_mod("Fabric API", "fabric api", 1) and success
    
    elif name == "performance-mods":
        success = download_mod("Performance Mods", "lithium", 1) and success
        success = download_mod("Performance Mods", "ferrite", 1) and success
        success = download_mod("Performance Mods", "starlight", 1) and success
        success = download_mod("Performance Mods", "entityculling", 1) and success
        success = download_mod("Performance Mods", "memo", 1) and success
        success = download_mod("Performance Mods", "lazyDFU", 1) and success
        success = download_mod("Performance Mods", "immediatelyfast", 1) and success
    
    elif name == "adventure-mods":
        success = download_mod("Adventure Mods", "adventure", 5) and success
    
    elif name == "high-quality-mods":
        success = download_mod("Better Combat", "bettercombat", 1) and success
        success = download_mod("Better Villages", "villager", 3) and success
        # Skip magic-bundle as it requires client-side dependencies
        # success = download_mod("Magic Mods", "magic", 3) and success
        success = download_mod("Grind Mods", "grind", 2) and success
        success = download_mod("RPG", "rpg", 3) and success
        # NOTE: RPG Stash will be filtered out in cleanup step due to missing dependency 'lithostitched'
    
    elif name == "world-generation-mods":
        success = download_mod("World Generation", "terrain", 3) and success
        success = download_mod("World Generation", "biome", 3) and success
        # NOTE: Biome Replacer will be filtered out in cleanup step due to incompatibility with Minecraft 1.21.5
        success = download_mod("World Generation", "structure", 3) and success
        success = download_mod("World Generation", "exploration", 3) and success
    
    elif name == "dungeon-exploration-mods":
        success = download_mod("Dungeons", "dungeon", 5) and success
        # NOTE: DungeonDodge+ will be filtered out in cleanup step due to client-side compatibility issues
        success = download_mod("Exploration", "exploration", 5) and success
        success = download_mod("Ruins", "ruins", 3) and success
        # NOTE: Philip's Ruins will be filtered out in cleanup step due to incompatibility with Minecraft 1.21.5
    
    elif name == "quest-mods":
        success = download_mod("Quest Mods", "quest", 3) and success
        success = download_mod("Quest Mods", "mission", 2) and success
    
    elif name == "boss-combat-mods":
        success = download_mod("Boss Mods", "boss", 3) and success
        # Skip combat-control as it requires client-side dependencies
        # success = download_mod("Combat Mods", "combat", 3) and success
        success = download_mod("Combat Mods", "weapon", 3) and success
        # NOTE: More Weapon Variants will be filtered out in cleanup step due to missing dependency 'mstv-base'
    
    elif name == "animal-creature-mods":
        success = download_mod("Animals", "animals", 3) and success
        success = download_mod("Mobs", "creature", 3) and success
        success = download_mod("Mobs", "monster", 3) and success
    
    elif name == "item-equipment-mods":
        success = download_mod("Items", "item", 3) and success
        success = download_mod("Equipment", "equipment", 3) and success
        # NOTE: Take's Armory will be filtered out in cleanup step due to missing dependency 'tlib'
        success = download_mod("Tools", "tools", 3) and success
        # NOTE: More Tools and Armor will be filtered out in cleanup step due to missing dependency 'modmenu'
    
    elif name == "qol-mods":
        # Comment out this client-side mod that's causing issues
        # success = download_mod("QoL", "inventory", 2) and success
        success = download_mod("QoL", "crafting", 2) and success
        success = download_mod("QoL", "minimap", 1) and success
        success = download_mod("QoL", "map", 2) and success
    
    elif name == "furniture-decoration-mods":
        success = download_mod("Furniture", "furniture", 5) and success
        # Comment out Better Chroma Key which is client-side
        # success = download_mod("Decoration", "decoration", 5) and success
        success = download_mod("Decoration", "decoration", 5) and success
        success = download_mod("Polymer", "polymer", 2) and success
        success = download_mod("Furniture Kits", "kits", 3) and success
        success = download_mod("Chairs", "chairs", 2) and success
        success = download_mod("Tables", "tables", 2) and success
    
    elif name == "required-dependencies":
        success = download_mod("Dependencies", "collective", 1) and success
        success = download_mod("Dependencies", "cloth-config fabric", 1) and success
        success = download_mod("Dependencies", "extended_drawers", 1) and success
        success = download_mod("Dependencies", "quad", 1) and success
    
    # Mark category as downloaded if successful
    if success:
        progress["categories"][name] = True
        save_progress(progress)
    
    return success


def create_client_pack(profile_name="adventure_pack.txt"):
    """Create a client modpack zip file"""
    # Define client pack variables
    MC_VERSION = "1.21.5"
    LOADER = "fabric"
    FABRIC_VERSION = "0.16.13"
    CLIENT_PACK_DIR = os.path.join(ROOT_DIR, "client_pack")
    CLIENT_MODS_DIR = os.path.join(CLIENT_PACK_DIR, "mods")
    # Use the profile name in the output file name (without .txt extension)
    pack_name = profile_name.replace('.txt', '')
    OUTPUT_ZIP = os.path.join(ROOT_DIR, f"{pack_name}-{MC_VERSION}-{LOADER}.zip")
    
    print("\n===================================================")
    print("Creating Minecraft Adventure Client Pack")
    print("===================================================")
    
    # Check for installed mods
    if not os.path.exists(MODS_DIR):
        print("Error: Server mods directory does not exist.")
        return False
    
    # Check for modpack profile
    profile_path = os.path.join(MODPACK_DIR, profile_name)
    if not os.path.exists(profile_path):
        print(f"Profile {profile_name} not found. Creating from installed mods...")
        save_mod_list()
    
    # Clean and create client pack directory
    print("Setting up client pack directory...")
    if os.path.exists(CLIENT_PACK_DIR):
        shutil.rmtree(CLIENT_PACK_DIR)
    os.makedirs(CLIENT_MODS_DIR)
    
    # Create README for clients
    readme_content = f"""=====================================================
MINECRAFT ADVENTURE MODPACK - {MC_VERSION} ({LOADER})
=====================================================

This modpack contains an exciting adventure experience with:
- Dungeon exploration and challenges
- Beautiful world generation with unique structures
- Quest and mission systems
- Epic boss battles and improved combat
- Unique animals and creatures
- Maps for navigation
- Performance improvements for smooth gameplay
- Quality of life features
- Furniture and decoration mods to enhance your builds

INSTALLATION INSTRUCTIONS:
1. Install Minecraft {MC_VERSION}
2. Install Fabric Loader version {FABRIC_VERSION} from https://fabricmc.net/
3. Copy all mods from the 'mods' folder to:
   - Windows: %APPDATA%\\.minecraft\\mods
   - Mac: ~/Library/Application Support/minecraft/mods
   - Linux: ~/.minecraft/mods
4. Launch Minecraft with the Fabric profile

ENJOY YOUR ADVENTURE!
"""
    
    with open(os.path.join(CLIENT_PACK_DIR, "README.txt"), 'w') as f:
        f.write(readme_content)
    
    # Copy client-compatible mods
    print("Copying mods to client pack...")
    
    # Count of copied mods
    copied_count = 0
    client_only_count = 0
    shared_count = 0
    
    # Create a set to track mods we've already added to avoid duplicates
    added_mods = set()
    
    # Read the profile and copy mods
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Parse mod type and filename
                parts = line.split(']', 1)
                if len(parts) < 2 or not parts[0].startswith('['):
                    continue
                
                mod_type = parts[0][1:].strip()
                mod_file = parts[1].strip()
                
                if not mod_file:
                    continue
                
                # Skip server-only mods
                if mod_type == "server":
                    print(f"Skipping server-only mod: {mod_file}")
                    continue
                
                # Process shared mods and client-only mods
                if mod_type in ["shared", "client"]:
                    # Download from cache directory first
                    cache_file_path = os.path.join(CACHE_DIR, mod_file)
                    server_file_path = os.path.join(MODS_DIR, mod_file)
                    
                    # Check if the mod is already in our added set
                    if mod_file in added_mods:
                        print(f"Skipping already added mod: {mod_file}")
                        continue
                    
                    added_mods.add(mod_file)
                    
                    if mod_file.endswith('.mrpack'):
                        # For .mrpack files, create a temporary directory to extract client mods
                        temp_extract_dir = os.path.join(CACHE_DIR, "temp_client_extract")
                        os.makedirs(temp_extract_dir, exist_ok=True)
                        
                        source_path = None
                        if os.path.exists(cache_file_path):
                            source_path = cache_file_path
                        elif os.path.exists(server_file_path):
                            source_path = server_file_path
                        
                        if source_path:
                            print(f"Extracting client mods from {mod_file}...")
                            
                            # Extract client-only mods from the mrpack
                            with zipfile.ZipFile(source_path, 'r') as zipf:
                                # Extract and parse the index file
                                try:
                                    zipf.extract("modrinth.index.json", temp_extract_dir)
                                    
                                    with open(os.path.join(temp_extract_dir, "modrinth.index.json"), 'r') as f:
                                        index = json.load(f)
                                    
                                    # Process files from the index
                                    for file_entry in index.get("files", []):
                                        path = file_entry.get("path", "")
                                        
                                        # Include files that are usable by clients
                                        env = file_entry.get("env", {})
                                        if env.get("client") != "unsupported":
                                            if path.endswith(".jar") and ("mods/" in path or path.startswith("mods/")):
                                                mod_filename = os.path.basename(path)
                                                
                                                # Check if file exists in the cache directory first
                                                cache_mod_path = os.path.join(CACHE_DIR, mod_filename)
                                                if os.path.exists(cache_mod_path):
                                                    print(f"  Including cached mod: {mod_filename}")
                                                    shutil.copy2(cache_mod_path, os.path.join(CLIENT_MODS_DIR, mod_filename))
                                                    copied_count += 1
                                                # Check if file exists in the server mods directory
                                                elif os.path.exists(os.path.join(MODS_DIR, mod_filename)):
                                                    print(f"  Including mod from server mods directory: {mod_filename}")
                                                    shutil.copy2(os.path.join(MODS_DIR, mod_filename), 
                                                               os.path.join(CLIENT_MODS_DIR, mod_filename))
                                                    copied_count += 1
                                                else:
                                                    # Otherwise download it
                                                    download_urls = file_entry.get("downloads", [])
                                                    if download_urls:
                                                        for download_url in download_urls:
                                                            try:
                                                                print(f"  Downloading client mod: {mod_filename}")
                                                                response = requests.get(download_url, stream=True)
                                                                response.raise_for_status()
                                                                
                                                                with open(os.path.join(CLIENT_MODS_DIR, mod_filename), 'wb') as out_file:
                                                                    for chunk in response.iter_content(chunk_size=8192):
                                                                        if chunk:
                                                                            out_file.write(chunk)
                                                                
                                                                # Also save to cache
                                                                shutil.copy2(os.path.join(CLIENT_MODS_DIR, mod_filename), 
                                                                           os.path.join(CACHE_DIR, mod_filename))
                                                                
                                                                copied_count += 1
                                                                break  # Stop after successful download
                                                            except Exception as e:
                                                                print(f"  Error downloading client mod {mod_filename}: {str(e)}")
                                    
                                    # Extract client-specific override files
                                    for override_dir in ["overrides"]:  # Just use client overrides, not server-overrides
                                        client_override_dir = os.path.join(CLIENT_PACK_DIR, "overrides")
                                        os.makedirs(client_override_dir, exist_ok=True)
                                        
                                        for file_info in zipf.infolist():
                                            if file_info.filename.startswith(f"{override_dir}/"):
                                                # Remove the override directory prefix
                                                relative_path = file_info.filename[len(f"{override_dir}/"):]
                                                if not relative_path:
                                                    continue  # Skip the directory itself
                                                
                                                # Determine the target path
                                                target_path = os.path.join(client_override_dir, relative_path)
                                                
                                                # Create directories if needed
                                                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                                                
                                                # Extract the file
                                                source = zipf.read(file_info.filename)
                                                with open(target_path, 'wb') as target_file:
                                                    target_file.write(source)
                                        
                                    # Create a client installation instructions file
                                    with open(os.path.join(CLIENT_PACK_DIR, "OVERRIDES_INSTRUCTIONS.txt"), 'w') as f:
                                        f.write("""
OVERRIDES INSTALLATION INSTRUCTIONS:
------------------------------------
The "overrides" folder contains additional configuration files and resources.
Copy all contents from the "overrides" folder to your .minecraft directory:

- Windows: %APPDATA%\\.minecraft\\
- Mac: ~/Library/Application Support/minecraft/
- Linux: ~/.minecraft/

This will install all necessary configuration files for the modpack.
""")
                                
                                except Exception as e:
                                    print(f"Error processing modpack for client: {str(e)}")
                                
                                finally:
                                    # Clean up temp directory
                                    shutil.rmtree(temp_extract_dir, ignore_errors=True)
                        else:
                            print(f"Warning: Could not find .mrpack file: {mod_file}")
                    else:
                        # For normal .jar files, try to find the file
                        source_path = None
                        if os.path.exists(cache_file_path):
                            source_path = cache_file_path
                        elif os.path.exists(server_file_path):
                            source_path = server_file_path
                        
                        if source_path:
                            print(f"Adding mod to client pack: {mod_file}")
                            shutil.copy2(source_path, os.path.join(CLIENT_MODS_DIR, mod_file))
                            
                            if mod_type == "shared":
                                shared_count += 1
                            else:  # client
                                client_only_count += 1
                                
                            copied_count += 1
                        else:
                            # If mod not found, try to download it from the Internet
                            print(f"Warning: Mod file not found in cache or server mods: {mod_file}")
                            # Here you could implement additional download logic for common mods
    
    # If no mods were copied, exit with error
    if copied_count == 0:
        print("Error: No mods copied to client pack!")
        return False
    
    # Create zip file
    print("Creating client modpack zip file...")
    shutil.make_archive(os.path.splitext(OUTPUT_ZIP)[0], 'zip', CLIENT_PACK_DIR)
    
    # Get zip size
    zip_size = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)  # Size in MB
    
    # Print summary
    print("===================================================")
    print("Client modpack creation complete!")
    print("===================================================")
    print(f"- {copied_count} total mods included in the client pack")
    print(f"  - {shared_count} shared mods (server + client)")
    print(f"  - {client_only_count} client-only mods")
    print(f"- Client pack saved to: {OUTPUT_ZIP}")
    print(f"- Size: {zip_size:.1f}M")
    print()
    print("Distribute this zip file to your players, who should")
    print("extract it and follow the README.txt instructions.")
    
    return True


def check_and_process_mrpack_downloads():
    """Check for new .mrpack files and process them immediately after download"""
    mrpack_files = [f for f in os.listdir(MODS_DIR) if f.endswith('.mrpack')]
    if not mrpack_files:
        return
    
    print("\n=== Processing New Modpack Files ===")
    for mrpack_file in mrpack_files:
        extract_mrpack(os.path.join(MODS_DIR, mrpack_file), MODS_DIR)


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Adventure Minecraft Mod Downloader")
    parser.add_argument("--reset", action="store_true", help="Reset download progress")
    parser.add_argument("--force", action="store_true", help="Force download of all mods")
    parser.add_argument("--category", help="Download only this category")
    parser.add_argument("--clean", action="store_true", help="Just clean up and organize mods")
    parser.add_argument("--client", action="store_true", help="Create client modpack")
    parser.add_argument("--all", action="store_true", help="Download mods and create client pack")
    parser.add_argument("--profile", action="store_true", help="Use profile-based download")
    parser.add_argument("--profile-name", default="adventure_pack.txt", help="Specify profile name to use (default: adventure_pack.txt)")
    args = parser.parse_args()
    
    # Ensure all directories exist
    ensure_directories()
    
    # If --client is specified, just create the client pack
    if args.client:
        create_client_pack(args.profile_name)
        return
    
    # Load progress
    progress = load_progress()
    
    # Reset progress if requested
    if args.reset:
        progress = {"categories": {}}
        save_progress(progress)
        print("Download progress reset.")
    
    # Clean up if requested and exit
    if args.clean:
        fix_biome_spreader()
        cleanup_mods()
        save_mod_list()
        print_summary()
        return
    
    # Clean mods directory at start
    clean_mods_directory()
    
    # Check if profile exists
    profile_name = args.profile_name
    profile_path = os.path.join(MODPACK_DIR, profile_name)
    use_profile = args.profile or os.path.exists(profile_path)
    
    print(f"Profile path: {profile_path}")
    print(f"Profile exists: {os.path.exists(profile_path)}")
    print(f"Using profile: {use_profile}")
    
    if use_profile:
        # Using profile-based approach
        if not os.path.exists(profile_path):
            print(f"Error: Profile {profile_name} not found at path {profile_path}")
            return
            
        print("Reading profile content:")
        with open(profile_path, 'r') as f:
            print(f.read())
        
        download_from_profile(profile_path, progress, args.force)
        check_and_process_mrpack_downloads()
    else:
        # Categories to download
        all_categories = [
            "essential-dependencies",
            "performance-mods",
            "adventure-mods",
            "high-quality-mods",
            "world-generation-mods",
            "dungeon-exploration-mods",
            "quest-mods",
            "boss-combat-mods",
            "animal-creature-mods", 
            "item-equipment-mods",
            "qol-mods",
            "furniture-decoration-mods",
            "required-dependencies"
        ]
        
        # If a specific category is provided, only download that one
        if args.category:
            if args.category in all_categories:
                success = download_category(args.category, progress, args.force)
                if not success:
                    print(f"Failed to download category {args.category}")
                # Process any mrpack files immediately after this category download
                check_and_process_mrpack_downloads()
            else:
                print(f"Unknown category: {args.category}")
                print(f"Available categories: {', '.join(all_categories)}")
                return
        else:
            # Download all categories
            for category in all_categories:
                download_category(category, progress, args.force)
                # Process any mrpack files after each category
                check_and_process_mrpack_downloads()
    
    # Final steps
    fix_biome_spreader()
    cleanup_mods()
    
    # Process any remaining mrpack files (redundant but ensures nothing is missed)
    process_mrpack_files()
    
    # Print summary
    print_summary()
    
    # Create client pack if --all is specified
    if args.all:
        create_client_pack(args.profile_name)


if __name__ == "__main__":
    main()