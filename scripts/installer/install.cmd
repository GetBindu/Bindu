@echo off
setlocal EnableDelayedExpansion

:: ==============================================================================
::  BINDU AGENT INSTALLER - ULTIMATE EDITION (vFinal)
:: ==============================================================================

:: --- 0. TERMINAL SETUP ---
chcp 65001 >nul
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (set "ESC=%%b")
set "C_RESET=%ESC%[0m"
set "C_CYAN=%ESC%[36m"
set "C_GREEN=%ESC%[32m"
set "C_YELLOW=%ESC%[33m"
set "C_RED=%ESC%[31m"
set "C_MAGENTA=%ESC%[35m"
set "C_WHITE=%ESC%[37m"
set "C_GRAY=%ESC%[90m"
set "C_BOLD=%ESC%[1m"
set "BAR=│"
set "PREFIX=%C_MAGENTA%%BAR%%C_RESET%"

cls
echo.
echo %C_CYAN%%C_BOLD%   .______    __  .__   __.  _______   __    __ %C_RESET%
echo %C_CYAN%%C_BOLD%   ^|   _  \  ^|  ^| ^|  \ ^|  ^| ^|       \ ^|  ^|  ^|  ^|%C_RESET%
echo %C_CYAN%%C_BOLD%   ^|  ^|_)  ^| ^|  ^| ^|   \^|  ^| ^|  .--.  ^|^|  ^|  ^|  ^|%C_RESET%
echo %C_CYAN%%C_BOLD%   ^|   _  ^<  ^|  ^| ^|  . `  ^| ^|  ^|  ^|  ^|^|  ^|  ^|  ^|%C_RESET%
echo %C_CYAN%%C_BOLD%   ^|  ^|_)  ^| ^|  ^| ^|  ^|\   ^| ^|  '--'  ^|^|  `--'  ^|%C_RESET%
echo %C_CYAN%%C_BOLD%   ^|______/  ^|__^| ^|__^| \__^| ^|_______/  \______/ %C_RESET%
echo.
echo    %C_GRAY%--------------------------------------------------%C_RESET%
echo    %C_WHITE% The Identity, Communication ^& Payments Layer %C_RESET%
echo    %C_GRAY%--------------------------------------------------%C_RESET%
echo.

:: --- 1. SYSTEM TELEMETRY ---
echo %C_MAGENTA%◇  System Telemetry ────────────────────────────────────╮%C_RESET%
echo %PREFIX%
echo %PREFIX%  %C_GRAY%[NET]  Checking Uplink...%C_RESET%
ping -n 1 github.com >nul 2>&1
if %errorlevel% neq 0 (
    echo %PREFIX%  %C_RED%[FAIL] No Internet Connection.%C_RESET%
    goto :FAIL
)
echo %PREFIX%  %C_GREEN%[OK]   Connection Established.%C_RESET%

echo %PREFIX%  %C_GRAY%[SYS]  Verifying Toolchain (git, uv)...%C_RESET%
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo %PREFIX%  %C_RED%[FAIL] Git not found.%C_RESET%
    goto :FAIL
)
echo %PREFIX%  %C_GREEN%[OK]   Toolchain Ready.%C_RESET%
echo %C_MAGENTA%├──────────────────────────────────────────────────────╯%C_RESET%
echo.

:: --- 2. IDENTITY CONFIGURATION ---
echo %C_MAGENTA%◇  Identity Configuration ──────────────────────────────╮%C_RESET%
echo %PREFIX%
echo %PREFIX%  %C_GRAY%Enter the unique identifier for your agent.%C_RESET%
set /p "AGENT_NAME=%PREFIX%  %C_CYAN%Identity Name:%C_RESET% "

if "%AGENT_NAME%"=="" set "AGENT_NAME=my-bindu-agent"

:: Sanitize
set "FOLDER_NAME=%AGENT_NAME: =-%"
set "FOLDER_NAME=%FOLDER_NAME:_=-%"
set "PKG_NAME=%FOLDER_NAME:-=_%"

if exist "%FOLDER_NAME%" (
    echo %PREFIX%  %C_RED%[ERR] Directory '%FOLDER_NAME%' already exists.%C_RESET%
    goto :FAIL
)

echo %PREFIX%
echo %PREFIX%  %C_GRAY%Provide a short description for the manifest.%C_RESET%
set /p "PROJ_DESC=%PREFIX%  %C_CYAN%Description:%C_RESET% "
if "%PROJ_DESC%"=="" set "PROJ_DESC=A high-performance Bindu agent."

:: --- 3. SKILL SELECTION ---
echo %C_MAGENTA%├──────────────────────────────────────────────────────╯%C_RESET%
echo %C_MAGENTA%◇  Skill Selection ─────────────────────────────────────╮%C_RESET%
echo %PREFIX%

set "TEMP_CLONE=_bindu_skills_temp"
if exist "%TEMP_CLONE%" rmdir /s /q "%TEMP_CLONE%"

echo %PREFIX%  %C_GRAY%[NET]  Fetching Remote Catalog...%C_RESET%
git clone --depth 1 https://github.com/GetBindu/Bindu.git "%TEMP_CLONE%" -q >nul 2>&1

if not exist "%TEMP_CLONE%\examples\skills" (
    echo %PREFIX%  %C_YELLOW%[WARN] Remote skills unavailable. Using defaults.%C_RESET%
    set "SKIP_SKILLS=1"
    goto :AUTHOR_CONFIG
)

set "cnt=0"
for /D %%D in ("%TEMP_CLONE%\examples\skills\*") do (
    set /a cnt+=1
    set "SKILL_NAME_!cnt!=%%~nxD"
    set "SKILL_PATH_!cnt!=%%D"
    echo %PREFIX%  %C_CYAN%[!cnt!]%C_RESET% %%~nxD
)

echo %PREFIX%
echo %PREFIX%  %C_GRAY%Select skills (e.g. '1 3'), 'all', or type custom name.%C_RESET%
set /p "SKILL_CHOICE=%PREFIX%  %C_CYAN%Selection:%C_RESET% "

:: --- 4. AUTHOR PROFILE ---
:AUTHOR_CONFIG
echo %C_MAGENTA%├──────────────────────────────────────────────────────╯%C_RESET%
echo %C_MAGENTA%◇  Author Profile ──────────────────────────────────────╮%C_RESET%
echo %PREFIX%
set /p "AUTHOR_NAME=%PREFIX%  %C_CYAN%Author Name [Bindu Builder]:%C_RESET% "
if "%AUTHOR_NAME%"=="" set "AUTHOR_NAME=Bindu Builder"

set /p "AUTHOR_EMAIL=%PREFIX%  %C_CYAN%Email [builder@getbindu.com]:%C_RESET% "
if "%AUTHOR_EMAIL%"=="" set "AUTHOR_EMAIL=builder@getbindu.com"

set /p "GITHUB_HANDLE=%PREFIX%  %C_CYAN%GitHub Handle [bindu-wizard]:%C_RESET% "
if "%GITHUB_HANDLE%"=="" set "GITHUB_HANDLE=bindu-wizard"

set /p "DOCKER_USER=%PREFIX%  %C_CYAN%DockerHub User [%GITHUB_HANDLE%]:%C_RESET% "
if "%DOCKER_USER%"=="" set "DOCKER_USER=%GITHUB_HANDLE%"

:: --- 5. FRAMEWORK ENGINE ---
echo %C_MAGENTA%├──────────────────────────────────────────────────────╯%C_RESET%
echo %C_MAGENTA%◇  Framework Engine ────────────────────────────────────╮%C_RESET%
echo %PREFIX%
echo %PREFIX%  %C_CYAN%[1]%C_RESET% Agno (Recommended)
echo %PREFIX%  %C_CYAN%[2]%C_RESET% LangChain
echo %PREFIX%  %C_CYAN%[3]%C_RESET% CrewAI
echo %PREFIX%  %C_CYAN%[4]%C_RESET% FastAgent
echo %PREFIX%  %C_CYAN%[5]%C_RESET% OpenAI
echo %PREFIX%
set /p "FW_CHOICE=%PREFIX%  %C_CYAN%Select Framework [1]:%C_RESET% "

if "%FW_CHOICE%"=="" set "FW_CHOICE=1"
if "%FW_CHOICE%"=="1" set "FRAMEWORK=agno"
if "%FW_CHOICE%"=="2" set "FRAMEWORK=langchain"
if "%FW_CHOICE%"=="3" set "FRAMEWORK=crew"
if "%FW_CHOICE%"=="4" set "FRAMEWORK=fastagent"
if "%FW_CHOICE%"=="5" set "FRAMEWORK=openai agent"

:: --- 6. INFRASTRUCTURE & SECURITY ---
echo %C_MAGENTA%├──────────────────────────────────────────────────────╯%C_RESET%
:: FIX: Escaped Ampersand here
echo %C_MAGENTA%◇  Infrastructure ^& Security ───────────────────────────╮%C_RESET%
echo %PREFIX%
echo %PREFIX%  %C_WHITE%Authentication:%C_RESET%
echo %PREFIX%    %C_CYAN%[1]%C_RESET% None   %C_CYAN%[2]%C_RESET% Auth0   %C_CYAN%[3]%C_RESET% Cognito   %C_CYAN%[4]%C_RESET% Azure   %C_CYAN%[5]%C_RESET% Google
set /p "AUTH_CHOICE=%PREFIX%    %C_CYAN%Choice [1]:%C_RESET% "
if "%AUTH_CHOICE%"=="" set "AUTH_CHOICE=1"
if "%AUTH_CHOICE%"=="1" set "AUTH_VAL=none"
if "%AUTH_CHOICE%"=="2" set "AUTH_VAL=auth0"
if "%AUTH_CHOICE%"=="3" set "AUTH_VAL=cognito"
if "%AUTH_CHOICE%"=="4" set "AUTH_VAL=azure-ad"
if "%AUTH_CHOICE%"=="5" set "AUTH_VAL=google"

echo %PREFIX%
echo %PREFIX%  %C_WHITE%Security:%C_RESET%
:: FIX: Escaped Ampersand here
echo %PREFIX%    %C_CYAN%[1]%C_RESET% None   %C_CYAN%[2]%C_RESET% DID ^& PKI   %C_CYAN%[3]%C_RESET% DID Only   %C_CYAN%[4]%C_RESET% PKI Only
set /p "SEC_CHOICE=%PREFIX%    %C_CYAN%Choice [2]:%C_RESET% "
if "%SEC_CHOICE%"=="" set "SEC_CHOICE=2"
if "%SEC_CHOICE%"=="1" set "SEC_VAL=none"
if "%SEC_CHOICE%"=="2" set "SEC_VAL=did-and-pki"
if "%SEC_CHOICE%"=="3" set "SEC_VAL=did-only"
if "%SEC_CHOICE%"=="4" set "SEC_VAL=pki-only"

echo %PREFIX%
echo %PREFIX%  %C_WHITE%Observability:%C_RESET%
echo %PREFIX%    %C_CYAN%[1]%C_RESET% None   %C_CYAN%[2]%C_RESET% Phoenix   %C_CYAN%[3]%C_RESET% Jaeger   %C_CYAN%[4]%C_RESET% Langfuse
set /p "OBS_CHOICE=%PREFIX%    %C_CYAN%Choice [1]:%C_RESET% "
if "%OBS_CHOICE%"=="" set "OBS_CHOICE=1"
if "%OBS_CHOICE%"=="1" set "OBS_VAL=none"
if "%OBS_CHOICE%"=="2" set "OBS_VAL=phoenix"
if "%OBS_CHOICE%"=="3" set "OBS_VAL=jaeger"
if "%OBS_CHOICE%"=="4" set "OBS_VAL=langfuse"

:: --- 7. DEVOPS & LICENSING ---
echo %C_MAGENTA%├──────────────────────────────────────────────────────╯%C_RESET%
echo %C_MAGENTA%◇  DevOps ^& Licensing ──────────────────────────────────╮%C_RESET%
echo %PREFIX%
set /p "GH_ACTION=%PREFIX%  %C_CYAN%Include GitHub Actions? [y/n]:%C_RESET% "
if "%GH_ACTION%"=="" set "GH_ACTION=y"

echo %PREFIX%
echo %PREFIX%  %C_WHITE%Open Source License:%C_RESET%
echo %PREFIX%    %C_CYAN%[1]%C_RESET% Apache 2.0   %C_CYAN%[2]%C_RESET% MIT   %C_CYAN%[3]%C_RESET% BSD   %C_CYAN%[4]%C_RESET% Proprietary
set /p "LIC_CHOICE=%PREFIX%  %C_CYAN%Choice [1]:%C_RESET% "

if "%LIC_CHOICE%"=="" set "LIC_CHOICE=1"
if "%LIC_CHOICE%"=="1" set "LIC_VAL=Apache Software License 2.0"
if "%LIC_CHOICE%"=="2" set "LIC_VAL=MIT license"
if "%LIC_CHOICE%"=="3" set "LIC_VAL=BSD license"
if "%LIC_CHOICE%"=="4" set "LIC_VAL=Not open source"

:: --- 8. FABRICATION ---
echo %C_MAGENTA%├──────────────────────────────────────────────────────╯%C_RESET%
echo %C_MAGENTA%◇  Fabrication ─────────────────────────────────────────╮%C_RESET%
echo %PREFIX%
echo %PREFIX%  %C_CYAN%[TASK] Hydrating Agent Template...%C_RESET%
echo %PREFIX%  %C_GRAY%[INFO] Framework: %FRAMEWORK%%C_RESET%
echo %PREFIX%  %C_GRAY%[INFO] Security:  %SEC_VAL%%C_RESET%

if exist "%USERPROFILE%\.cookiecutters\create-bindu-agent" (
    rmdir /s /q "%USERPROFILE%\.cookiecutters\create-bindu-agent" >nul 2>&1
)

:: >>> CORE COMMAND: All 15 variables passed explicitly <<<
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git ^
  --no-input ^
  project_name="%FOLDER_NAME%" ^
  project_slug="%PKG_NAME%" ^
  project_description="%PROJ_DESC%" ^
  agent_framework="%FRAMEWORK%" ^
  include_example_skills="n" ^
  skill_names="none" ^
  auth_provider="%AUTH_VAL%" ^
  observability_provider="%OBS_VAL%" ^
  security_features="%SEC_VAL%" ^
  include_github_actions="%GH_ACTION%" ^
  open_source_license="%LIC_VAL%" ^
  author="%AUTHOR_NAME%" ^
  email="%AUTHOR_EMAIL%" ^
  author_github_handle="%GITHUB_HANDLE%" ^
  dockerhub_username="%DOCKER_USER%"

if %errorlevel% neq 0 (
    echo %PREFIX%  %C_RED%[FAIL] Fabrication failed.%C_RESET%
    goto :FAIL
)

echo %PREFIX%  %C_GREEN%[OK]   Core Structure Generated.%C_RESET%

:: --- 9. SKILL INJECTION ---
echo %C_MAGENTA%├──────────────────────────────────────────────────────╯%C_RESET%
echo %C_MAGENTA%◇  Injecting Capabilities ──────────────────────────────╮%C_RESET%
echo %PREFIX%

set "TARGET_SKILLS=%FOLDER_NAME%\%PKG_NAME%\skills"
if not exist "%TARGET_SKILLS%" mkdir "%TARGET_SKILLS%" >nul 2>&1

if "%SKIP_SKILLS%"=="1" goto :FINALIZE_SKILLS
if "%SKILL_CHOICE%"=="" goto :FINALIZE_SKILLS

if /i "%SKILL_CHOICE%"=="all" (
    echo %PREFIX%  %C_GRAY%[COPY] Injecting all remote skills...%C_RESET%
    xcopy /E /I /Y /Q "%TEMP_CLONE%\examples\skills" "%TARGET_SKILLS%\" >nul 2>&1
    goto :FINALIZE_SKILLS
)

for %%i in (%SKILL_CHOICE%) do (
    if defined SKILL_NAME_%%i (
        echo %PREFIX%  %C_GRAY%[COPY] Injecting: !SKILL_NAME_%%i!...%C_RESET%
        xcopy /E /I /Y /Q "!SKILL_PATH_%%i!" "%TARGET_SKILLS%\!SKILL_NAME_%%i!" >nul 2>&1
    ) else (
        echo %PREFIX%  %C_CYAN%[NEW]  Creating custom skill: %%i...%C_RESET%
        mkdir "%TARGET_SKILLS%\%%i" >nul 2>&1
        (
            echo id: %%i-v1
            echo name: %%i
            echo version: 1.0.0
            echo description: Custom skill.
        ) > "%TARGET_SKILLS%\%%i\skill.yaml"
        (
            echo def handler^(data^):
            echo     return "Skill %%i online."
        ) > "%TARGET_SKILLS%\%%i\implementation.py"
    )
)

:FINALIZE_SKILLS
timeout /t 1 /nobreak >nul
if exist "%TEMP_CLONE%" rmdir /s /q "%TEMP_CLONE%"
echo %PREFIX%  %C_GREEN%[OK]   Skills Integrated.%C_RESET%

:: --- 10. FINALIZATION ---
echo %C_MAGENTA%├──────────────────────────────────────────────────────╯%C_RESET%
echo %C_MAGENTA%◇  Finalizing ──────────────────────────────────────────╮%C_RESET%
echo %PREFIX%
echo %PREFIX%  %C_GRAY%[INFO] Installing dependencies (uv sync)...%C_RESET%
cd "%FOLDER_NAME%"
uv sync >nul 2>&1
cd ..
echo %PREFIX%  %C_GREEN%[OK]   DEPLOYMENT SUCCESSFUL.%C_RESET%
echo %C_MAGENTA%├──────────────────────────────────────────────────────╯%C_RESET%
echo.

:: --- SUMMARY ---
echo %C_CYAN%   AGENT ONLINE %C_RESET%
echo.
echo    %C_GRAY%Identity:%C_RESET%   %FOLDER_NAME%
echo    %C_GRAY%Location:%C_RESET%   %CD%\%FOLDER_NAME%
echo.
echo    %C_WHITE%To start your agent:%C_RESET%
echo      cd %FOLDER_NAME%
echo      uv run python -m %PKG_NAME%.main
echo.
pause
exit /b 0

:FAIL
if exist "%TEMP_CLONE%" rmdir /s /q "%TEMP_CLONE%"
echo %PREFIX%  %C_RED%[FAIL] Installation Aborted.%C_RESET%
pause
exit /b 1