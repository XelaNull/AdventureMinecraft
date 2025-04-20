#!/bin/bash

# Get the absolute path of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Set up test environment
TEST_MODS_DIR="$ROOT_DIR/server/mods/test"
TEST_CACHE_DIR="$SCRIPT_DIR/mod_cache/test"

# Activate virtual environment if it exists
if [ -f "$ROOT_DIR/venv/bin/activate" ]; then
    echo "Activating Python virtual environment..."
    source "$ROOT_DIR/venv/bin/activate"
fi

# Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}Testing Mod Categorization System${NC}"
echo -e "${BLUE}==============================================${NC}"

# Test function to run a test and report results
run_test() {
    test_name="$1"
    test_command="$2"
    
    echo -e "\n${BLUE}=== TEST: $test_name ===${NC}"
    
    # Run the test command and capture output and exit code
    output=$(eval "$test_command" 2>&1)
    exit_code=$?
    
    # Print truncated output
    echo "$output" | head -n 10
    if [[ $(echo "$output" | wc -l) -gt 10 ]]; then
        echo -e "${YELLOW}... (output truncated) ...${NC}"
    fi
    
    # Check test result
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED: $test_name${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED: $test_name (Exit code: $exit_code)${NC}"
        return 1
    fi
}

# Initialize counters
passed_tests=0
failed_tests=0
total_tests=0

# Test 1: Check if adventure_pack.txt exists
echo -e "\n${BLUE}=== TEST: Checking adventure_pack.txt ===${NC}"
PROFILE_PATH="$SCRIPT_DIR/modpack_profiles/adventure_pack.txt"

if [ -f "$PROFILE_PATH" ]; then
    echo -e "${GREEN}✓ PASSED: adventure_pack.txt exists${NC}"
    ((passed_tests++))
else
    echo -e "${RED}✗ FAILED: adventure_pack.txt not found at $PROFILE_PATH${NC}"
    ((failed_tests++))
fi
((total_tests++))

# Test 2: Check profile format - each line should have proper categorization
echo -e "\n${BLUE}=== TEST: Checking profile format ===${NC}"
if [ -f "$PROFILE_PATH" ]; then
    incorrect_lines=0
    line_number=0
    while IFS= read -r line; do
        ((line_number++))
        # Skip empty lines and comments
        if [[ -z "$line" || "$line" == \#* ]]; then
            continue
        fi
        
        # Check for proper format [type] filename.jar
        if ! [[ "$line" =~ ^\[(server|client|shared)\]\ .+\.jar$ ]]; then
            echo -e "${RED}Line $line_number has incorrect format: $line${NC}"
            ((incorrect_lines++))
        fi
    done < "$PROFILE_PATH"
    
    if [ $incorrect_lines -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED: All mod lines in adventure_pack.txt have correct format${NC}"
        ((passed_tests++))
    else
        echo -e "${RED}✗ FAILED: Found $incorrect_lines lines with incorrect format${NC}"
        ((failed_tests++))
    fi
else
    echo -e "${YELLOW}SKIPPED: Cannot check profile format - file not found${NC}"
fi
((total_tests++))

# Test 3: Check that all [server] mods are only in server/mods and not in client_pack/mods
echo -e "\n${BLUE}=== TEST: Checking server-only mods distribution ===${NC}"
if [ -f "$PROFILE_PATH" ]; then
    server_mods_in_client=0
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -z "$line" || "$line" == \#* ]]; then
            continue
        fi
        
        # Process server-only mods
        if [[ "$line" =~ ^\[server\]\ (.+\.jar)$ ]]; then
            mod_file="${BASH_REMATCH[1]}"
            if [ -f "$ROOT_DIR/client_pack/mods/$mod_file" ]; then
                echo -e "${RED}Server-only mod found in client pack: $mod_file${NC}"
                ((server_mods_in_client++))
            fi
        fi
    done < "$PROFILE_PATH"
    
    if [ $server_mods_in_client -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED: No server-only mods found in client pack${NC}"
        ((passed_tests++))
    else
        echo -e "${RED}✗ FAILED: Found $server_mods_in_client server-only mods in client pack${NC}"
        ((failed_tests++))
    fi
else
    echo -e "${YELLOW}SKIPPED: Cannot check mod distribution - profile file not found${NC}"
fi
((total_tests++))

# Test 4: Check that all [client] mods are in client_pack/mods only, not server/mods
echo -e "\n${BLUE}=== TEST: Checking client-only mods distribution ===${NC}"
if [ -f "$PROFILE_PATH" ]; then
    client_mods_in_server=0
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -z "$line" || "$line" == \#* ]]; then
            continue
        fi
        
        # Process client-only mods
        if [[ "$line" =~ ^\[client\]\ (.+\.jar)$ ]]; then
            mod_file="${BASH_REMATCH[1]}"
            if [ -f "$ROOT_DIR/server/mods/$mod_file" ]; then
                echo -e "${RED}Client-only mod found in server: $mod_file${NC}"
                ((client_mods_in_server++))
            fi
        fi
    done < "$PROFILE_PATH"
    
    if [ $client_mods_in_server -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED: No client-only mods found in server${NC}"
        ((passed_tests++))
    else
        echo -e "${RED}✗ FAILED: Found $client_mods_in_server client-only mods in server${NC}"
        ((failed_tests++))
    fi
else
    echo -e "${YELLOW}SKIPPED: Cannot check mod distribution - profile file not found${NC}"
fi
((total_tests++))

# Test 5: Check that installed mods match their category in the profile
echo -e "\n${BLUE}=== TEST: Checking mod categorization of installed mods ===${NC}"
if [ -f "$PROFILE_PATH" ]; then
    categorization_errors=0
    
    # Check server mods
    echo -e "${BLUE}Checking server mods against profile...${NC}"
    for mod_file in "$ROOT_DIR/server/mods"/*.jar; do
        if [ -f "$mod_file" ]; then
            # Get just the filename
            mod_name=$(basename "$mod_file")
            
            # Check mod classification in profile
            mod_type=""
            found=false
            
            while IFS= read -r line; do
                if [[ "$line" =~ ^\[(server|shared|client)\]\ $mod_name$ ]]; then
                    found=true
                    mod_type="${BASH_REMATCH[1]}"
                    break
                fi
            done < "$PROFILE_PATH"
            
            # Report results
            if ! $found; then
                echo -e "${YELLOW}Warning: Mod in server not found in profile: $mod_name${NC}"
            elif [ "$mod_type" == "client" ]; then
                echo -e "${RED}Error: Client-only mod found in server: $mod_name${NC}"
                ((categorization_errors++))
            fi
        fi
    done
    
    # Check client mods
    echo -e "${BLUE}Checking client mods against profile...${NC}"
    for mod_file in "$ROOT_DIR/client_pack/mods"/*.jar; do
        if [ -f "$mod_file" ]; then
            # Get just the filename
            mod_name=$(basename "$mod_file")
            
            # Check mod classification in profile
            mod_type=""
            found=false
            
            while IFS= read -r line; do
                if [[ "$line" =~ ^\[(server|shared|client)\]\ $mod_name$ ]]; then
                    found=true
                    mod_type="${BASH_REMATCH[1]}"
                    break
                fi
            done < "$PROFILE_PATH"
            
            # Report results
            if ! $found; then
                echo -e "${YELLOW}Warning: Mod in client not found in profile: $mod_name${NC}"
            elif [ "$mod_type" == "server" ]; then
                echo -e "${RED}Error: Server-only mod found in client: $mod_name${NC}"
                ((categorization_errors++))
            fi
        fi
    done
    
    if [ $categorization_errors -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED: All installed mods properly categorized${NC}"
        ((passed_tests++))
    else
        echo -e "${RED}✗ FAILED: Found $categorization_errors mods with incorrect categorization${NC}"
        ((failed_tests++))
    fi
else
    echo -e "${YELLOW}SKIPPED: Cannot check mod distribution - profile file not found${NC}"
fi
((total_tests++))

# Test 6: Run client pack creation and verify it correctly categorizes mods
run_test "Client pack creation from profile" "python3 $SCRIPT_DIR/download_mods.py --client"
if [ $? -eq 0 ]; then ((passed_tests++)); else ((failed_tests++)); fi
((total_tests++))

# Test 7: Check for known incompatible mods in server directory
echo -e "\n${BLUE}=== TEST: Checking for incompatible mods in server ===${NC}"
PROBLEM_MODS=("dungeondodgeplus" "Axiom" "tweakermore" "mutantmonsters" "sodium" "Xaeros" "iris")
problem_found=0

for pattern in "${PROBLEM_MODS[@]}"; do
    for file in "$ROOT_DIR/server/mods"/*.jar; do
        if [ -f "$file" ] && [[ "$(basename "$file")" == *"$pattern"* ]]; then
            echo -e "${RED}Incompatible mod found in server: $(basename "$file")${NC}"
            ((problem_found++))
        fi
    done
done

if [ $problem_found -eq 0 ]; then
    echo -e "${GREEN}✓ PASSED: No known incompatible mods found in server${NC}"
    ((passed_tests++))
else
    echo -e "${RED}✗ FAILED: Found $problem_found incompatible mods in server${NC}"
    ((failed_tests++))
fi
((total_tests++))

# Test Summary
echo -e "\n${BLUE}==============================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}==============================================${NC}"
echo -e "Total tests: $total_tests"
echo -e "${GREEN}Passed: $passed_tests${NC}"
echo -e "${RED}Failed: $failed_tests${NC}"

# Exit with error if any tests failed
if [ $failed_tests -gt 0 ]; then
    exit 1
else
    exit 0
fi