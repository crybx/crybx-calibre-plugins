@echo off
REM Build script for NovelUpdates plugin (Windows)

SET PLUGIN_DIR=%~dp0..
SET COMMON_DIR=%~dp0..\..\common

cd /d "%PLUGIN_DIR%"

echo Copying common files for zip
copy "%COMMON_DIR%\common_*.py" .

echo Building zip
python "%COMMON_DIR%\build.py"

echo Deleting common files after zip
del /q common_compatibility.py common_dialogs.py common_icons.py common_menus.py common_widgets.py 2>nul

echo Installing plugin
calibre-customize -a ..\installs\NovelUpdates.zip

echo Build and install completed.
