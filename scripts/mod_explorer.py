#!/usr/bin/env python3
"""
Minecraft Mod Downloader - A tool for searching and downloading Minecraft mods from Modrinth and CurseForge

This script allows you to:
- Search for mods by keywords across both platforms
- Filter by Minecraft version and mod loader
- Limit the number of search results
- Download mods directly with automatic dependency resolution
- Download specific older versions as needed
- Cache downloaded mods to avoid re-downloading
- View detailed information about mods
"""

import requests
import json
import os
import sys
import argparse
import hashlib
import shutil
from tqdm import tqdm
import time
import webbrowser
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored terminal output
init()

# ================= CONFIGURATION =================
# Your Modrinth API key (Project Authorization Token)
# This can be obtained from https://modrinth.com/settings/pats
MODRINTH_API_KEY = "mrp_wsVIgH747NJ7zaACF3o27LXKO6Ovr9PnowcDjW4rkYl07SFTPmCR40LXfVj7"

# Your CurseForge API key
# This can be obtained from https://console.curseforge.com/
CURSEFORGE_API_KEY = "$2a$10$Ml/ijVvjaWaNiQetMHMqrevxRhu2OTUSbTe0/BPBPXizUGu83SSJa"

# Base URLs for APIs
MODRINTH_API = "https://api.modrinth.com/v2"
CURSEFORGE_API = "https://api.curseforge.com"
USER_AGENT = "MinecraftModDownloader/1.0"

# Game ID for Minecraft in CurseForge
MINECRAFT_GAME_ID = 432

# Class ID for Minecraft Mods in CurseForge
MC_MODS_CLASS_ID = 6

# Cache directory for downloaded mods
DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mod_cache")

# ================= HELPER FUNCTIONS =================

def print_colored(text, color=Fore.WHITE, style=Style.NORMAL, end='\n'):
    """Print text with specified color and style."""
    print(f"{style}{color}{text}{Style.RESET_ALL}", end=end)

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print_colored(f" {text} ", Fore.CYAN, Style.BRIGHT)
    print("=" * 80)

def print_mod_info(mod, source="modrinth", detailed=False):
    """Display information about a mod."""
    if source == "modrinth":
        title = mod.get('title', 'Unknown')
        slug = mod.get('slug', 'unknown')
        mod_id = mod.get('project_id', mod.get('id', 'unknown'))
        
        print_colored(f"{title} ({slug}) [Modrinth]", Fore.GREEN, Style.BRIGHT)
        
        team = mod.get('team', [])
        if team:
            authors = ', '.join([author.get('name', 'Unknown') for author in team])
            print_colored(f"Author: {authors}", Fore.YELLOW)
        
        downloads = mod.get('downloads', 0)
        print_colored(f"Downloads: {downloads:,}", Fore.BLUE)
        
        if 'updated' in mod:
            print_colored(f"Updated: {mod['updated'][:10]}", Fore.BLUE)
        
        if 'description' in mod:
            description = mod['description']
            if len(description) > 150 and not detailed:
                description = description[:147] + "..."
            print_colored(f"Description: {description}", Fore.WHITE)
        
        print_colored(f"URL: https://modrinth.com/mod/{slug}", Fore.CYAN)
        print_colored(f"ID: {mod_id}", Fore.CYAN)
    
    elif source == "curseforge":
        title = mod.get('name', 'Unknown')
        mod_id = mod.get('id', 'unknown')
        
        print_colored(f"{title} [CurseForge]", Fore.GREEN, Style.BRIGHT)
        print_colored(f"ID: {mod_id}", Fore.CYAN)
        
        authors = mod.get('authors', [])
        if authors:
            authors_str = ', '.join([author.get('name', 'Unknown') for author in authors])
            print_colored(f"Author: {authors_str}", Fore.YELLOW)
        
        downloads = mod.get('downloadCount', 0)
        print_colored(f"Downloads: {downloads:,}", Fore.BLUE)
        
        if 'dateModified' in mod:
            print_colored(f"Updated: {mod['dateModified'][:10]}", Fore.BLUE)
        
        summary = mod.get('summary', 'No description available')
        if summary:
            if len(summary) > 150 and not detailed:
                summary = summary[:147] + "..."
            print_colored(f"Summary: {summary}", Fore.WHITE)
        
        website_url = mod.get('links', {}).get('websiteUrl', f"https://www.curseforge.com/minecraft/mc-mods/{mod_id}")
        print_colored(f"URL: {website_url}", Fore.CYAN)
    
    print()

def get_cache_path(filename, create=True):
    """Get the path to a cached file and create the cache directory if needed."""
    if create and not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    
    return os.path.join(CACHE_DIR, filename)

def is_in_cache(filename):
    """Check if a file exists in the cache."""
    return os.path.exists(get_cache_path(filename, create=False))

def copy_from_cache(filename, output_dir):
    """Copy a file from the cache to the output directory."""
    cache_path = get_cache_path(filename)
    output_path = os.path.join(output_dir, filename)
    
    if os.path.exists(cache_path):
        shutil.copy2(cache_path, output_path)
        return True
    
    return False

def save_to_cache(filename, from_path):
    """Save a file to the cache."""
    cache_path = get_cache_path(filename)
    
    if os.path.exists(from_path) and not os.path.exists(cache_path):
        shutil.copy2(from_path, cache_path)
        return True
    
    return False

# ================= MODRINTH API FUNCTIONS =================

def modrinth_search_mods(query, mc_version=None, loader=None, limit=10, offset=0):
    """Search for mods on Modrinth with the given criteria."""
    facets = []
    if mc_version:
        facets.append(["versions:" + mc_version])
    if loader:
        facets.append(["categories:" + loader])
    
    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "index": "relevance"
    }
    
    if facets:
        params["facets"] = json.dumps(facets)
    
    headers = {
        "User-Agent": USER_AGENT,
        "Authorization": MODRINTH_API_KEY
    }
    
    try:
        response = requests.get(f"{MODRINTH_API}/search", params=params, headers=headers)
        response.raise_for_status()
        results = response.json()
        return results['hits']
    except requests.exceptions.RequestException as e:
        print_colored(f"Error searching for mods on Modrinth: {e}", Fore.RED, Style.BRIGHT)
        return []

def modrinth_get_mod_details(mod_id):
    """Get detailed information about a specific mod from Modrinth."""
    headers = {
        "User-Agent": USER_AGENT,
        "Authorization": MODRINTH_API_KEY
    }
    
    try:
        response = requests.get(f"{MODRINTH_API}/project/{mod_id}", headers=headers)
        response.raise_for_status()
        mod_data = response.json()
        
        # Get mod versions
        versions_response = requests.get(f"{MODRINTH_API}/project/{mod_id}/version", headers=headers)
        versions_response.raise_for_status()
        mod_data['version_data'] = versions_response.json()
        mod_data['versions'] = [v['version_number'] for v in versions_response.json()]
        
        return mod_data
    except requests.exceptions.RequestException as e:
        print_colored(f"Error getting mod details from Modrinth: {e}", Fore.RED, Style.BRIGHT)
        return None

def modrinth_list_mod_versions(mod_id, mc_version=None, loader=None):
    """List available versions for a mod with optional filtering from Modrinth."""
    headers = {
        "User-Agent": USER_AGENT,
        "Authorization": MODRINTH_API_KEY
    }
    
    try:
        response = requests.get(f"{MODRINTH_API}/project/{mod_id}/version", headers=headers)
        response.raise_for_status()
        versions = response.json()
        
        # Filter versions if needed
        if mc_version or loader:
            filtered_versions = []
            for version in versions:
                game_versions = version.get('game_versions', [])
                loaders = version.get('loaders', [])
                
                if (not mc_version or mc_version in game_versions) and \
                   (not loader or loader in loaders):
                    filtered_versions.append(version)
            return filtered_versions
        
        return versions
    except requests.exceptions.RequestException as e:
        print_colored(f"Error listing mod versions from Modrinth: {e}", Fore.RED, Style.BRIGHT)
        return []

def modrinth_download_file(url, filename, output_dir, force_download=False):
    """Download a file from Modrinth with caching support."""
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Authorization": MODRINTH_API_KEY
        }
        
        # Check if the file is in cache and we're not forcing a download
        if not force_download and is_in_cache(filename):
            print_colored(f"Using cached version of {filename}...", Fore.YELLOW)
            if copy_from_cache(filename, output_dir):
                return True
        
        # Check if the file already exists in the output directory
        file_path = os.path.join(output_dir, filename)
        if os.path.exists(file_path) and not force_download:
            print_colored(f"File {filename} already exists in output directory, skipping...", Fore.YELLOW)
            # Still save to cache if it's not there
            save_to_cache(filename, file_path)
            return True
        
        print_colored(f"Downloading {filename} from Modrinth...", Fore.CYAN)
        
        response = requests.get(url, stream=True, headers=headers)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(file_path, 'wb') as f, tqdm(
            total=total_size, unit='B', unit_scale=True, unit_divisor=1024,
            desc=filename, ncols=100
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        # Save to cache
        save_to_cache(filename, file_path)
        
        print_colored(f"Downloaded {filename} to {output_dir}", Fore.GREEN, Style.BRIGHT)
        return True
    except requests.exceptions.RequestException as e:
        print_colored(f"Error downloading file from Modrinth: {e}", Fore.RED, Style.BRIGHT)
        return False
    except Exception as e:
        print_colored(f"Error: {e}", Fore.RED, Style.BRIGHT)
        return False

def modrinth_download_mod(mod_id, mc_version=None, loader=None, output_dir=".", specific_version=None, force_download=False):
    """Download a mod from Modrinth with optional version specification and dependency resolution."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Get versions of the mod
    versions = modrinth_list_mod_versions(mod_id, mc_version, loader)
    
    if not versions:
        print_colored(f"No compatible versions found for {mod_id} with Minecraft {mc_version} and {loader} loader on Modrinth", 
                      Fore.RED, Style.BRIGHT)
        return False
    
    # Find the version to download
    version = None
    if specific_version:
        # Find the specific version
        for v in versions:
            if v.get('version_number') == specific_version:
                version = v
                break
        
        if not version:
            print_colored(f"Version {specific_version} not found for mod {mod_id} on Modrinth", Fore.RED, Style.BRIGHT)
            print_colored("Available versions:", Fore.YELLOW)
            for v in versions:
                print(f"  - {v.get('version_number')} ({v.get('name')})")
            return False
    else:
        # Use the newest version
        version = versions[0]  # Versions should be sorted newest first
    
    # Download the primary file
    files = version.get('files', [])
    if not files:
        print_colored(f"No files found for version {version.get('version_number')} on Modrinth", Fore.RED, Style.BRIGHT)
        return False
    
    # Use the primary file
    primary_files = [f for f in files if f.get('primary', False)]
    file_info = primary_files[0] if primary_files else files[0]
    
    # Download the file
    filename = file_info['filename']
    url = file_info['url']
    
    success = modrinth_download_file(url, filename, output_dir, force_download)
    
    # Process dependencies
    if success and 'dependencies' in version:
        print_colored(f"Processing dependencies for {version['name']} from Modrinth...", Fore.CYAN)
        for dependency in version['dependencies']:
            if dependency.get('dependency_type') == 'required':
                dep_project_id = dependency.get('project_id')
                dep_version_id = dependency.get('version_id')
                
                if dep_project_id:
                    print_colored(f"Resolving dependency: {dependency.get('project_id')}", Fore.CYAN)
                    
                    if dep_version_id:
                        # Get the version details
                        dep_version = None
                        dep_versions = modrinth_list_mod_versions(dep_project_id)
                        for v in dep_versions:
                            if v.get('id') == dep_version_id:
                                dep_version = v
                                break
                        
                        if dep_version:
                            # Download the file
                            dep_files = dep_version.get('files', [])
                            if dep_files:
                                dep_primary_files = [f for f in dep_files if f.get('primary', False)]
                                dep_file_info = dep_primary_files[0] if dep_primary_files else dep_files[0]
                                
                                dep_filename = dep_file_info['filename']
                                dep_url = dep_file_info['url']
                                
                                modrinth_download_file(dep_url, dep_filename, output_dir, force_download)
                    else:
                        # Find latest compatible version
                        dep_versions = modrinth_list_mod_versions(dep_project_id, mc_version, loader)
                        if dep_versions:
                            # Use the first version (should be latest)
                            dep_version = dep_versions[0]
                            
                            # Download the file
                            dep_files = dep_version.get('files', [])
                            if dep_files:
                                dep_primary_files = [f for f in dep_files if f.get('primary', False)]
                                dep_file_info = dep_primary_files[0] if dep_primary_files else dep_files[0]
                                
                                dep_filename = dep_file_info['filename']
                                dep_url = dep_file_info['url']
                                
                                modrinth_download_file(dep_url, dep_filename, output_dir, force_download)
    
    return success

# ================= CURSEFORGE API FUNCTIONS =================

def curseforge_make_api_request(endpoint, method="GET", params=None, data=None):
    """Make an API request to CurseForge API."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "x-api-key": CURSEFORGE_API_KEY
    }
    
    url = f"{CURSEFORGE_API}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print_colored(f"CurseForge API request error ({url}): {e}", Fore.RED, Style.BRIGHT)
        return None

def curseforge_search_mods(query, mc_version=None, loader=None, limit=10, offset=0):
    """Search for mods on CurseForge with the given criteria."""
    # Get modloader ID if provided
    modloader_id = None
    if loader:
        loader_map = {
            "forge": 1,
            "cauldron": 2,
            "liteloader": 3,
            "fabric": 4,
            "quilt": 5
        }
        modloader_id = loader_map.get(loader.lower())
    
    # Prepare search data
    search_data = {
        "gameId": MINECRAFT_GAME_ID,
        "classId": MC_MODS_CLASS_ID,
        "searchFilter": query,
        "pageSize": limit,
        "index": offset,
        "sortField": 2,  # Popularity
        "sortOrder": "desc"
    }
    
    if mc_version:
        search_data["gameVersion"] = mc_version
    
    if modloader_id:
        search_data["modLoaderType"] = modloader_id
    
    # Make the API request
    response = curseforge_make_api_request("/v1/mods/search", method="GET", params=search_data)
    
    if response and 'data' in response:
        return response['data']
    return []

def curseforge_get_mod_details(mod_id):
    """Get detailed information about a specific mod from CurseForge."""
    response = curseforge_make_api_request(f"/v1/mods/{mod_id}")
    
    if response and 'data' in response:
        # Get mod files
        files_response = curseforge_make_api_request(f"/v1/mods/{mod_id}/files")
        if files_response and 'data' in files_response:
            response['data']['latestFiles'] = files_response['data']
        
        return response['data']
    return None

def curseforge_get_mod_files(mod_id, mc_version=None, loader=None):
    """Get all files for a mod with optional filtering from CurseForge."""
    params = {}
    
    if mc_version:
        params["gameVersion"] = mc_version
    
    if loader:
        loader_map = {
            "forge": 1,
            "cauldron": 2,
            "liteloader": 3,
            "fabric": 4,
            "quilt": 5
        }
        modloader_id = loader_map.get(loader.lower())
        if modloader_id:
            params["modLoaderType"] = modloader_id
    
    response = curseforge_make_api_request(f"/v1/mods/{mod_id}/files", params=params)
    
    if response and 'data' in response:
        return response['data']
    return []

def curseforge_download_file(url, filename, output_dir, force_download=False):
    """Download a file from CurseForge with caching support."""
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/octet-stream",
            "x-api-key": CURSEFORGE_API_KEY
        }
        
        # Check if the file is in cache and we're not forcing a download
        if not force_download and is_in_cache(filename):
            print_colored(f"Using cached version of {filename}...", Fore.YELLOW)
            if copy_from_cache(filename, output_dir):
                return True
        
        # Check if the file already exists in the output directory
        file_path = os.path.join(output_dir, filename)
        if os.path.exists(file_path) and not force_download:
            print_colored(f"File {filename} already exists in output directory, skipping...", Fore.YELLOW)
            # Still save to cache if it's not there
            save_to_cache(filename, file_path)
            return True
        
        print_colored(f"Downloading {filename} from CurseForge...", Fore.CYAN)
        
        response = requests.get(url, stream=True, headers=headers)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(file_path, 'wb') as f, tqdm(
            total=total_size, unit='B', unit_scale=True, unit_divisor=1024,
            desc=filename, ncols=100
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        # Save to cache
        save_to_cache(filename, file_path)
        
        print_colored(f"Downloaded {filename} to {output_dir}", Fore.GREEN, Style.BRIGHT)
        return True
    except requests.exceptions.RequestException as e:
        print_colored(f"Error downloading file from CurseForge: {e}", Fore.RED, Style.BRIGHT)
        return False
    except Exception as e:
        print_colored(f"Error: {e}", Fore.RED, Style.BRIGHT)
        return False

def curseforge_process_dependencies(mod_id, file_id, output_dir, force_download=False):
    """Process and download dependencies for a mod file from CurseForge."""
    file_data = curseforge_make_api_request(f"/v1/mods/{mod_id}/files/{file_id}")
    if not file_data or 'data' not in file_data:
        return False
    
    file_data = file_data['data']
    dependencies = file_data.get('dependencies', [])
    if not dependencies:
        return True
    
    print_colored(f"Processing dependencies for {file_data.get('fileName', 'Unknown')} from CurseForge...", Fore.CYAN)
    
    for dependency in dependencies:
        if dependency.get('relationType') == 3:  # Required dependency
            dep_mod_id = dependency.get('modId')
            
            if dep_mod_id:
                print_colored(f"Resolving dependency: Mod ID {dep_mod_id}", Fore.CYAN)
                
                # Get the mod details
                dep_mod = curseforge_get_mod_details(dep_mod_id)
                if not dep_mod:
                    print_colored(f"Could not find dependency mod ID {dep_mod_id}", Fore.RED)
                    continue
                
                print_colored(f"Found dependency: {dep_mod.get('name', 'Unknown')}", Fore.GREEN)
                
                # Get compatible files
                dep_files = curseforge_get_mod_files(dep_mod_id)
                if not dep_files:
                    print_colored(f"No files found for dependency {dep_mod.get('name', 'Unknown')}", Fore.RED)
                    continue
                
                # Filter files by game version
                game_versions = file_data.get('gameVersions', [])
                
                compatible_files = []
                for dep_file in dep_files:
                    dep_game_versions = dep_file.get('gameVersions', [])
                    # Check if any game version matches
                    if any(version in dep_game_versions for version in game_versions):
                        compatible_files.append(dep_file)
                
                if not compatible_files:
                    print_colored(f"No compatible files found for dependency {dep_mod.get('name', 'Unknown')}", Fore.RED)
                    continue
                
                # Sort by date (newest first)
                compatible_files.sort(key=lambda f: f.get('fileDate', ''), reverse=True)
                
                # Use the newest compatible file
                dep_file = compatible_files[0]
                
                # Download the dependency
                dep_url = dep_file.get('downloadUrl')
                if not dep_url:
                    print_colored(f"No download URL found for dependency {dep_mod.get('name', 'Unknown')}", Fore.RED)
                    continue
                
                dep_filename = dep_file.get('fileName', f"mod_{dep_mod_id}_{dep_file.get('id')}.jar")
                
                success = curseforge_download_file(dep_url, dep_filename, output_dir, force_download)
                
                if success:
                    # Recursively process its dependencies
                    curseforge_process_dependencies(dep_mod_id, dep_file.get('id'), output_dir, force_download)
    
    return True

def curseforge_download_mod(mod_id, mc_version=None, loader=None, output_dir=".", specific_file_id=None, force_download=False):
    """Download a mod from CurseForge with optional version specification and dependency resolution."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if we need to download a specific file
    if specific_file_id:
        # Get file details
        file_data = curseforge_make_api_request(f"/v1/mods/{mod_id}/files/{specific_file_id}")
        if not file_data or 'data' not in file_data:
            print_colored(f"Could not find file ID {specific_file_id} for mod ID {mod_id} on CurseForge", Fore.RED, Style.BRIGHT)
            return False
        
        file_data = file_data['data']
        
        # Get download URL
        download_url = file_data.get('downloadUrl')
        if not download_url:
            print_colored(f"No download URL found for file ID {specific_file_id} on CurseForge", Fore.RED, Style.BRIGHT)
            return False
        
        # Download the file
        filename = file_data.get('fileName', f"mod_{mod_id}_{specific_file_id}.jar")
        
        success = curseforge_download_file(download_url, filename, output_dir, force_download)
        
        # Process dependencies
        if success:
            curseforge_process_dependencies(mod_id, specific_file_id, output_dir, force_download)
        
        return success
    
    # Get mod details
    mod_data = curseforge_get_mod_details(mod_id)
    if not mod_data:
        print_colored(f"Could not find mod with ID: {mod_id} on CurseForge", Fore.RED, Style.BRIGHT)
        return False
    
    # Get mod files
    files = curseforge_get_mod_files(mod_id, mc_version, loader)
    if not files:
        print_colored(f"No files found for mod: {mod_id} on CurseForge", Fore.RED, Style.BRIGHT)
        return False
    
    # Sort files by date (newest first)
    files.sort(key=lambda f: f.get('fileDate', ''), reverse=True)
    
    # Use the newest file
    file = files[0]
    file_id = file.get('id')
    
    # Get download URL
    download_url = file.get('downloadUrl')
    if not download_url:
        print_colored(f"No download URL found for file ID {file_id} on CurseForge", Fore.RED, Style.BRIGHT)
        return False
    
    # Download the file
    filename = file.get('fileName', f"mod_{mod_id}_{file_id}.jar")
    
    success = curseforge_download_file(download_url, filename, output_dir, force_download)
    
    # Process dependencies
    if success:
        curseforge_process_dependencies(mod_id, file_id, output_dir, force_download)
    
    return success

# ================= COMBINED FUNCTIONS =================

def download_mod(mod_id, source="modrinth", mc_version=None, loader=None, output_dir=".", specific_version=None, force_download=False):
    """Download a mod from the specified source."""
    if source == "modrinth":
        return modrinth_download_mod(mod_id, mc_version, loader, output_dir, specific_version, force_download)
    elif source == "curseforge":
        return curseforge_download_mod(mod_id, mc_version, loader, output_dir, specific_version, force_download)
    else:
        print_colored(f"Unknown source: {source}", Fore.RED, Style.BRIGHT)
        return False

def search_mods(query, source="both", mc_version=None, loader=None, limit=10):
    """Search for mods across both platforms."""
    results = []
    
    if source == "both" or source == "modrinth":
        modrinth_results = modrinth_search_mods(query, mc_version, loader, limit)
        for mod in modrinth_results:
            results.append({"source": "modrinth", "data": mod})
    
    if source == "both" or source == "curseforge":
        curseforge_results = curseforge_search_mods(query, mc_version, loader, limit)
        for mod in curseforge_results:
            results.append({"source": "curseforge", "data": mod})
    
    # Sort by popularity (downloads)
    results.sort(key=lambda r: r["data"].get("downloads", 0) if r["source"] == "modrinth" else r["data"].get("downloadCount", 0), reverse=True)
    
    return results[:limit]

# ================= COMMAND LINE INTERFACE =================

def main():
    parser = argparse.ArgumentParser(description="Minecraft Mod Downloader - Search and download Minecraft mods from Modrinth and CurseForge")
    parser.add_argument("--source", choices=["modrinth", "curseforge", "both"], default="both", help="Source to search for mods (default: both)")
    parser.add_argument("--mc-version", help="Minecraft version to filter by")
    parser.add_argument("--loader", help="Mod loader to filter by (e.g., fabric, forge, quilt)")
    parser.add_argument("--search", help="Search term")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of search results (default: 10)")
    parser.add_argument("--download", action="store_true", help="Download the mods")
    parser.add_argument("--download-id", help="Download a specific mod by ID")
    parser.add_argument("--download-source", choices=["modrinth", "curseforge"], help="Source for the mod ID when using --download-id")
    parser.add_argument("--version", help="Specific version to download (instead of latest)")
    parser.add_argument("--output", default=".", help="Output directory for downloads (default: current directory)")
    parser.add_argument("--force-download", action="store_true", help="Force download even if the file is in cache")
    parser.add_argument("--cache-dir", help="Custom cache directory (default: mod_cache in the script directory)")
    
    args = parser.parse_args()
    
    # Set custom cache directory if provided
    global CACHE_DIR
    CACHE_DIR = args.cache_dir if args.cache_dir else DEFAULT_CACHE_DIR
    
    # Download a specific mod by ID
    if args.download_id:
        if not args.download_source:
            print_colored("Please specify a source (--download-source) when using --download-id", Fore.RED, Style.BRIGHT)
            sys.exit(1)
        
        print_colored(f"Downloading mod {args.download_id} from {args.download_source}...", Fore.CYAN)
        success = download_mod(
            args.download_id, 
            args.download_source, 
            args.mc_version, 
            args.loader, 
            args.output, 
            args.version, 
            args.force_download
        )
        
        if success:
            print_colored(f"Successfully downloaded mod {args.download_id}", Fore.GREEN, Style.BRIGHT)
        else:
            print_colored(f"Failed to download mod {args.download_id}", Fore.RED, Style.BRIGHT)
        sys.exit(0)
    
    # Search for mods
    if args.search:
        results = search_mods(args.search, args.source, args.mc_version, args.loader, args.limit)
        
        if results:
            print_colored(f"Found {len(results)} results for '{args.search}':", Fore.GREEN, Style.BRIGHT)
            for result in results:
                print_mod_info(result["data"], result["source"])
                
                # Download the mod if requested
                if args.download:
                    mod_id = result["data"].get("id", result["data"].get("slug", ""))
                    
                    if not args.mc_version or not args.loader:
                        print_colored("MC version and loader are required for downloads", Fore.RED)
                        continue
                    
                    print_colored(f"Downloading {mod_id} from {result['source']}...", Fore.CYAN)
                    download_mod(
                        mod_id, 
                        result["source"], 
                        args.mc_version, 
                        args.loader, 
                        args.output, 
                        args.version, 
                        args.force_download
                    )
        else:
            print_colored(f"No results found for '{args.search}'", Fore.YELLOW)
        sys.exit(0)
    
    # Show help if no options provided
    if not args.search and not args.download_id:
        parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting Minecraft Mod Downloader. Goodbye!")
    except Exception as e:
        print_colored(f"An unexpected error occurred: {e}", Fore.RED, Style.BRIGHT)
        sys.exit(1) 