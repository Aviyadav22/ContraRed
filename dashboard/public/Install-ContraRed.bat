@echo off
title Installing ContraRed Word Add-in...
color 0B

echo ===================================================
echo     ContraRed Word Add-in Auto-Installer
echo ===================================================
echo.
echo Please wait while we configure your Office Add-in folder...
echo.

:: Request Admin Privileges (required to create an SMB Share for Office)
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrative privileges to create the trusted folder...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [1/4] Creating C:\ContraRed-Addin folder...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$folderPath = 'C:\ContraRed-Addin'; if (-not (Test-Path $folderPath)) { New-Item -ItemType Directory -Force -Path $folderPath | Out-Null }"

echo [2/4] Downloading latest manifest from secure server...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$folderPath = 'C:\ContraRed-Addin'; Invoke-WebRequest -Uri 'https://contrared.onrender.com/api/v1/documents/manifest' -OutFile \"$folderPath\manifest.xml\""

:: Check if the download succeeded
if not exist "C:\ContraRed-Addin\manifest.xml" (
    color 0C
    echo.
    echo ERROR: Failed to download the manifest. Please check your internet connection.
    pause
    exit /b
)

echo [3/4] Setting up trusted network share...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$folderPath = 'C:\ContraRed-Addin'; if (-not (Get-SmbShare -Name 'ContraRed-Addin' -ErrorAction SilentlyContinue)) { New-SmbShare -Name 'ContraRed-Addin' -Path $folderPath -ReadAccess 'Everyone' -ErrorAction SilentlyContinue | Out-Null }"

echo [4/4] Registering Trusted Catalog with Office...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$registryPath = 'HKCU:\Software\Microsoft\Office\16.0\WEF\TrustedCatalogs\ContraRedCatalog'; if (-not (Test-Path $registryPath)) { New-Item -Path $registryPath -Force | Out-Null }; Set-ItemProperty -Path $registryPath -Name 'Url' -Value '\\localhost\ContraRed-Addin'; Set-ItemProperty -Path $registryPath -Name 'Flags' -Value 1; Set-ItemProperty -Path $registryPath -Name 'Id' -Value 'ContraRedCatalog';"

echo.
color 0A
echo ===================================================
echo                 INSTALLATION COMPLETE!
echo ===================================================
echo.
echo ContraRed has been successfully installed to your computer.
echo.
echo NEXT STEPS:
echo 1. Please completely close and RESTART Microsoft Word.
echo 2. Open any document, go to the "Insert" tab.
echo 3. Click "Get Add-ins" (or "My Add-ins").
echo 4. Click the "SHARED FOLDER" tab at the top.
echo 5. Select "ContraRed PoC" and click "Add".
echo.
pause
