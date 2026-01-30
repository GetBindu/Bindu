#!/bin/bash

# ==============================================================================
#  BINDU AGENT INSTALLER - ULTIMATE EDITION (Linux/macOS)
# ==============================================================================

# --- 0. TERMINAL SETUP ---
# Define Colors
C_RESET='\033[0m'
C_CYAN='\033[0;36m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[0;33m'
C_RED='\033[0;31m'
C_MAGENTA='\033[0;35m'
C_WHITE='\033[0;37m'
C_GRAY='\033[0;90m'
C_BOLD='\033[1m'
BAR="│"
PREFIX="${C_MAGENTA}${BAR}${C_RESET}"

clear
echo ""
echo -e "${C_CYAN}${C_BOLD}   .______    __  .__   __.  _______   __    __ ${C_RESET}"
echo -e "${C_CYAN}${C_BOLD}   |   _  \  |  | |  \ |  | |       \ |  |  |  |${C_RESET}"
echo -e "${C_CYAN}${C_BOLD}   |  |_)  | |  | |   \|  | |  .--.  ||  |  |  |${C_RESET}"
echo -e "${C_CYAN}${C_BOLD}   |   _  <  |  | |  . \`  | |  |  |  ||  |  |  |${C_RESET}"
echo -e "${C_CYAN}${C_BOLD}   |  |_)  | |  | |  |\   | |  '--'  ||  \`--'  |${C_RESET}"
echo -e "${C_CYAN}${C_BOLD}   |______/  |__| |__| \__| |_______/  \______/ ${C_RESET}"
echo ""
echo -e "    ${C_GRAY}--------------------------------------------------${C_RESET}"
echo -e "    ${C_WHITE} The Identity, Communication & Payments Layer ${C_RESET}"
echo -e "    ${C_GRAY}--------------------------------------------------${C_RESET}"
echo ""

# --- 1. SYSTEM TELEMETRY ---
echo -e "${C_MAGENTA}◇  System Telemetry ────────────────────────────────────╮${C_RESET}"
echo -e "$PREFIX"
echo -e "$PREFIX  ${C_GRAY}[NET]  Checking Uplink...${C_RESET}"

if ! ping -c 1 github.com &> /dev/null; then
    echo -e "$PREFIX  ${C_RED}[FAIL] No Internet Connection.${C_RESET}"
    exit 1
fi
echo -e "$PREFIX  ${C_GREEN}[OK]   Connection Established.${C_RESET}"

echo -e "$PREFIX  ${C_GRAY}[SYS]  Verifying Toolchain (git, uv)...${C_RESET}"
if ! command -v git &> /dev/null; then
    echo -e "$PREFIX  ${C_RED}[FAIL] Git not found.${C_RESET}"
    exit 1
fi

# Check for UV/UVX
if ! command -v uv &> /dev/null; then
    echo -e "$PREFIX  ${C_YELLOW}[WARN] UV not found. Installing...${C_RESET}"
    curl -LsSf https://astral.sh/uv/install.sh | sh > /dev/null 2>&1
    
    # Force add common install paths to PATH for this session
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi

# Ensure UVX is resolvable
if command -v uvx &> /dev/null; then
    UVX_CMD="uvx"
elif command -v uv &> /dev/null; then
    # Fallback if uvx alias isn't set but uv exists
    UVX_CMD="uv tool run"
elif [ -f "$HOME/.cargo/bin/uvx" ]; then
    # Fallback to explicit path
    UVX_CMD="$HOME/.cargo/bin/uvx"
else
    echo -e "$PREFIX  ${C_RED}[FAIL] Could not locate 'uv' or 'uvx' after install.${C_RESET}"
    exit 1
fi

echo -e "$PREFIX  ${C_GREEN}[OK]   Toolchain Ready ($UVX_CMD).${C_RESET}"
echo -e "${C_MAGENTA}├──────────────────────────────────────────────────────╯${C_RESET}"
echo ""

# --- 2. IDENTITY CONFIGURATION ---
echo -e "${C_MAGENTA}◇  Identity Configuration ──────────────────────────────╮${C_RESET}"
echo -e "$PREFIX"
echo -e "$PREFIX  ${C_GRAY}Enter the unique identifier for your agent.${C_RESET}"
read -p "$(echo -e "$PREFIX  ${C_CYAN}Identity Name:${C_RESET} ")" AGENT_NAME

if [ -z "$AGENT_NAME" ]; then AGENT_NAME="my-bindu-agent"; fi

# Sanitize
FOLDER_NAME=$(echo "$AGENT_NAME" | tr ' ' '-')
FOLDER_NAME=${FOLDER_NAME//_/-}
FOLDER_NAME=$(echo "$FOLDER_NAME" | tr -cd '[:alnum:]-')
PKG_NAME=$(echo "$FOLDER_NAME" | tr '-' '_')

if [ -d "$FOLDER_NAME" ]; then
    echo -e "$PREFIX  ${C_RED}[ERR] Directory '$FOLDER_NAME' already exists.${C_RESET}"
    exit 1
fi

echo -e "$PREFIX"
echo -e "$PREFIX  ${C_GRAY}Provide a short description for the manifest.${C_RESET}"
read -p "$(echo -e "$PREFIX  ${C_CYAN}Description:${C_RESET} ")" PROJ_DESC
if [ -z "$PROJ_DESC" ]; then PROJ_DESC="A high-performance Bindu agent."; fi

# --- 3. SKILL SELECTION ---
echo -e "${C_MAGENTA}├──────────────────────────────────────────────────────╯${C_RESET}"
echo -e "${C_MAGENTA}◇  Skill Selection ─────────────────────────────────────╮${C_RESET}"
echo -e "$PREFIX"

TEMP_CLONE="_bindu_skills_temp"
rm -rf "$TEMP_CLONE"

echo -e "$PREFIX  ${C_GRAY}[NET]  Fetching Remote Catalog...${C_RESET}"
git clone --depth 1 https://github.com/GetBindu/Bindu.git "$TEMP_CLONE" -q > /dev/null 2>&1

if [ ! -d "$TEMP_CLONE/examples/skills" ]; then
    echo -e "$PREFIX  ${C_YELLOW}[WARN] Remote skills unavailable. Using defaults.${C_RESET}"
    SKIP_SKILLS=1
else
    cnt=0
    declare -A SKILL_MAP
    declare -A SKILL_PATH_MAP
    
    # Loop through directories
    for d in "$TEMP_CLONE/examples/skills"/*; do
        if [ -d "$d" ]; then
            ((cnt++))
            dirname=$(basename "$d")
            SKILL_MAP[$cnt]="$dirname"
            SKILL_PATH_MAP[$cnt]="$d"
            echo -e "$PREFIX  ${C_CYAN}[$cnt]${C_RESET} $dirname"
        fi
    done
fi

echo -e "$PREFIX"
echo -e "$PREFIX  ${C_GRAY}Select skills (e.g. '1 3'), 'all', or type custom name.${C_RESET}"
read -p "$(echo -e "$PREFIX  ${C_CYAN}Selection:${C_RESET} ")" SKILL_CHOICE

# --- 4. AUTHOR PROFILE ---
echo -e "${C_MAGENTA}├──────────────────────────────────────────────────────╯${C_RESET}"
echo -e "${C_MAGENTA}◇  Author Profile ──────────────────────────────────────╮${C_RESET}"
echo -e "$PREFIX"
read -p "$(echo -e "$PREFIX  ${C_CYAN}Author Name [Bindu Builder]:${C_RESET} ")" AUTHOR_NAME
if [ -z "$AUTHOR_NAME" ]; then AUTHOR_NAME="Bindu Builder"; fi

read -p "$(echo -e "$PREFIX  ${C_CYAN}Email [builder@getbindu.com]:${C_RESET} ")" AUTHOR_EMAIL
if [ -z "$AUTHOR_EMAIL" ]; then AUTHOR_EMAIL="builder@getbindu.com"; fi

read -p "$(echo -e "$PREFIX  ${C_CYAN}GitHub Handle [bindu-wizard]:${C_RESET} ")" GITHUB_HANDLE
if [ -z "$GITHUB_HANDLE" ]; then GITHUB_HANDLE="bindu-wizard"; fi

read -p "$(echo -e "$PREFIX  ${C_CYAN}DockerHub User [$GITHUB_HANDLE]:${C_RESET} ")" DOCKER_USER
if [ -z "$DOCKER_USER" ]; then DOCKER_USER="$GITHUB_HANDLE"; fi

# --- 5. FRAMEWORK ENGINE ---
echo -e "${C_MAGENTA}├──────────────────────────────────────────────────────╯${C_RESET}"
echo -e "${C_MAGENTA}◇  Framework Engine ────────────────────────────────────╮${C_RESET}"
echo -e "$PREFIX"
echo -e "$PREFIX  ${C_CYAN}[1]${C_RESET} Agno (Recommended)"
echo -e "$PREFIX  ${C_CYAN}[2]${C_RESET} LangChain"
echo -e "$PREFIX  ${C_CYAN}[3]${C_RESET} CrewAI"
echo -e "$PREFIX  ${C_CYAN}[4]${C_RESET} FastAgent"
echo -e "$PREFIX  ${C_CYAN}[5]${C_RESET} OpenAI"
echo -e "$PREFIX"
read -p "$(echo -e "$PREFIX  ${C_CYAN}Select Framework [1]:${C_RESET} ")" FW_CHOICE

case $FW_CHOICE in
    2) FRAMEWORK="langchain" ;;
    3) FRAMEWORK="crew" ;;
    4) FRAMEWORK="fastagent" ;;
    5) FRAMEWORK="openai agent" ;;
    *) FRAMEWORK="agno" ;;
esac

# --- 6. INFRASTRUCTURE & SECURITY ---
echo -e "${C_MAGENTA}├──────────────────────────────────────────────────────╯${C_RESET}"
echo -e "${C_MAGENTA}◇  Infrastructure & Security ───────────────────────────╮${C_RESET}"
echo -e "$PREFIX"
echo -e "$PREFIX  ${C_WHITE}Authentication:${C_RESET}"
echo -e "$PREFIX    ${C_CYAN}[1]${C_RESET} None   ${C_CYAN}[2]${C_RESET} Auth0   ${C_CYAN}[3]${C_RESET} Cognito   ${C_CYAN}[4]${C_RESET} Azure   ${C_CYAN}[5]${C_RESET} Google"
read -p "$(echo -e "$PREFIX    ${C_CYAN}Choice [1]:${C_RESET} ")" AUTH_CHOICE

case $AUTH_CHOICE in
    2) AUTH_VAL="auth0" ;;
    3) AUTH_VAL="cognito" ;;
    4) AUTH_VAL="azure-ad" ;;
    5) AUTH_VAL="google" ;;
    *) AUTH_VAL="none" ;;
esac

echo -e "$PREFIX"
echo -e "$PREFIX  ${C_WHITE}Security:${C_RESET}"
echo -e "$PREFIX    ${C_CYAN}[1]${C_RESET} None   ${C_CYAN}[2]${C_RESET} DID & PKI   ${C_CYAN}[3]${C_RESET} DID Only   ${C_CYAN}[4]${C_RESET} PKI Only"
read -p "$(echo -e "$PREFIX    ${C_CYAN}Choice [2]:${C_RESET} ")" SEC_CHOICE

case $SEC_CHOICE in
    1) SEC_VAL="none" ;;
    3) SEC_VAL="did-only" ;;
    4) SEC_VAL="pki-only" ;;
    *) SEC_VAL="did-and-pki" ;;
esac

echo -e "$PREFIX"
echo -e "$PREFIX  ${C_WHITE}Observability:${C_RESET}"
echo -e "$PREFIX    ${C_CYAN}[1]${C_RESET} None   ${C_CYAN}[2]${C_RESET} Phoenix   ${C_CYAN}[3]${C_RESET} Jaeger   ${C_CYAN}[4]${C_RESET} Langfuse"
read -p "$(echo -e "$PREFIX    ${C_CYAN}Choice [1]:${C_RESET} ")" OBS_CHOICE

case $OBS_CHOICE in
    2) OBS_VAL="phoenix" ;;
    3) OBS_VAL="jaeger" ;;
    4) OBS_VAL="langfuse" ;;
    *) OBS_VAL="none" ;;
esac

# --- 7. DEVOPS & LICENSING ---
echo -e "${C_MAGENTA}├──────────────────────────────────────────────────────╯${C_RESET}"
echo -e "${C_MAGENTA}◇  DevOps & Licensing ──────────────────────────────────╮${C_RESET}"
echo -e "$PREFIX"
read -p "$(echo -e "$PREFIX  ${C_CYAN}Include GitHub Actions? [y/n]:${C_RESET} ")" GH_ACTION
if [ -z "$GH_ACTION" ]; then GH_ACTION="y"; fi

echo -e "$PREFIX"
echo -e "$PREFIX  ${C_WHITE}Open Source License:${C_RESET}"
echo -e "$PREFIX    ${C_CYAN}[1]${C_RESET} Apache 2.0   ${C_CYAN}[2]${C_RESET} MIT   ${C_CYAN}[3]${C_RESET} BSD   ${C_CYAN}[4]${C_RESET} Proprietary"
read -p "$(echo -e "$PREFIX  ${C_CYAN}Choice [1]:${C_RESET} ")" LIC_CHOICE

case $LIC_CHOICE in
    2) LIC_VAL="MIT license" ;;
    3) LIC_VAL="BSD license" ;;
    4) LIC_VAL="Not open source" ;;
    *) LIC_VAL="Apache Software License 2.0" ;;
esac

# --- 8. FABRICATION ---
echo -e "${C_MAGENTA}├──────────────────────────────────────────────────────╯${C_RESET}"
echo -e "${C_MAGENTA}◇  Fabrication ─────────────────────────────────────────╮${C_RESET}"
echo -e "$PREFIX"
echo -e "$PREFIX  ${C_CYAN}[TASK] Hydrating Agent Template...${C_RESET}"
echo -e "$PREFIX  ${C_GRAY}[INFO] Framework: $FRAMEWORK${C_RESET}"
echo -e "$PREFIX  ${C_GRAY}[INFO] Security:  $SEC_VAL${C_RESET}"

# Clear cache
rm -rf "$HOME/.cookiecutters/create-bindu-agent" > /dev/null 2>&1

# >>> FIXED: Use the detected UVX_CMD <<<
$UVX_CMD cookiecutter https://github.com/getbindu/create-bindu-agent.git \
  --no-input \
  project_name="$FOLDER_NAME" \
  project_slug="$PKG_NAME" \
  project_description="$PROJ_DESC" \
  agent_framework="$FRAMEWORK" \
  include_example_skills="n" \
  skill_names="none" \
  auth_provider="$AUTH_VAL" \
  observability_provider="$OBS_VAL" \
  security_features="$SEC_VAL" \
  include_github_actions="$GH_ACTION" \
  open_source_license="$LIC_VAL" \
  author="$AUTHOR_NAME" \
  email="$AUTHOR_EMAIL" \
  author_github_handle="$GITHUB_HANDLE" \
  dockerhub_username="$DOCKER_USER"

if [ $? -ne 0 ]; then
    echo -e "$PREFIX  ${C_RED}[FAIL] Fabrication failed.${C_RESET}"
    rm -rf "$TEMP_CLONE"
    exit 1
fi

echo -e "$PREFIX  ${C_GREEN}[OK]   Core Structure Generated.${C_RESET}"

# --- 9. SKILL INJECTION ---
echo -e "${C_MAGENTA}├──────────────────────────────────────────────────────╯${C_RESET}"
echo -e "${C_MAGENTA}◇  Injecting Capabilities ──────────────────────────────╮${C_RESET}"
echo -e "$PREFIX"

TARGET_SKILLS="$FOLDER_NAME/$PKG_NAME/skills"
mkdir -p "$TARGET_SKILLS"

if [ -z "$SKILL_CHOICE" ] || [ "$SKIP_SKILLS" == "1" ]; then
    : # Do nothing
elif [ "$SKILL_CHOICE" == "all" ]; then
    echo -e "$PREFIX  ${C_GRAY}[COPY] Injecting all remote skills...${C_RESET}"
    cp -r "$TEMP_CLONE/examples/skills/"* "$TARGET_SKILLS/"
else
    # Split by space
    for i in $SKILL_CHOICE; do
        if [ -n "${SKILL_MAP[$i]}" ]; then
            NAME="${SKILL_MAP[$i]}"
            PATH="${SKILL_PATH_MAP[$i]}"
            echo -e "$PREFIX  ${C_GRAY}[COPY] Injecting: $NAME...${C_RESET}"
            cp -r "$PATH" "$TARGET_SKILLS/$NAME"
        else
            echo -e "$PREFIX  ${C_CYAN}[NEW]  Creating custom skill: $i...${C_RESET}"
            mkdir -p "$TARGET_SKILLS/$i"
            echo -e "id: $i-v1\nname: $i\nversion: 1.0.0\ndescription: Custom skill." > "$TARGET_SKILLS/$i/skill.yaml"
            echo -e "def handler(data):\n    return \"Skill $i online.\"" > "$TARGET_SKILLS/$i/implementation.py"
        fi
    done
fi

rm -rf "$TEMP_CLONE"
echo -e "$PREFIX  ${C_GREEN}[OK]   Skills Integrated.${C_RESET}"

# --- 10. FINALIZATION ---
echo -e "${C_MAGENTA}├──────────────────────────────────────────────────────╯${C_RESET}"
echo -e "${C_MAGENTA}◇  Finalizing ──────────────────────────────────────────╮${C_RESET}"
echo -e "$PREFIX"
echo -e "$PREFIX  ${C_GRAY}[INFO] Installing dependencies (uv sync)...${C_RESET}"
cd "$FOLDER_NAME"
# Fallback if uv command not found in shell
if command -v uv &> /dev/null; then
    uv sync > /dev/null 2>&1
else
    "$HOME/.cargo/bin/uv" sync > /dev/null 2>&1
fi
cd ..
echo -e "$PREFIX  ${C_GREEN}[OK]   DEPLOYMENT SUCCESSFUL.${C_RESET}"
echo -e "${C_MAGENTA}├──────────────────────────────────────────────────────╯${C_RESET}"
echo ""

# --- SUMMARY ---
echo -e "${C_CYAN}   AGENT ONLINE ${C_RESET}"
echo ""
echo -e "   ${C_GRAY}Identity:${C_RESET}   $FOLDER_NAME"
echo -e "   ${C_GRAY}Location:${C_RESET}   $(pwd)/$FOLDER_NAME"
echo ""
echo -e "   ${C_WHITE}To start your agent:${C_RESET}"
echo -e "     cd $FOLDER_NAME"
echo -e "     uv run python -m $PKG_NAME.main"
echo ""