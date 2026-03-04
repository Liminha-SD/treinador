@echo off
setlocal enabledelayedexpansion

:: --- Configurações ---
set "VENV_DIR=venv"
set "APP_NAME=treinador"
set "MAIN_FILE=main.py"

echo ====================================================
echo   Configurando Ambiente e Compilando !APP_NAME!
echo ====================================================

:: --- 1. Ambiente Virtual ---
if not exist "!VENV_DIR!\Scripts\activate.bat" (
    echo [1/4] Criando ambiente virtual...
    python -m venv !VENV_DIR!
) else (
    echo [1/4] Ambiente virtual ja existe.
)

echo [2/4] Ativando ambiente e instalando dependencias...
call !VENV_DIR!\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

:: --- 2. Compilacao ---
echo [3/4] Compilando !APP_NAME!...
:: --noconsole: sem janela de terminal
:: --onefile: apenas um executavel
:: --collect-all tensorflow: necessario para apps que usam tensorflow
pyinstaller --noconsole --onefile --collect-all tensorflow --name "!APP_NAME!" "!MAIN_FILE!"

:: --- 3. Limpeza e Finalizacao ---
if exist "dist\!APP_NAME!.exe" (
    echo [4/4] Finalizando: Movendo executavel e limpando arquivos inuteis...
    
    :: Move o exe para a raiz
    move /y "dist\!APP_NAME!.exe" "." >nul
    
    :: Remove pastas de build
    if exist "build" rmdir /s /q "build"
    if exist "dist" rmdir /s /q "dist"
    
    :: Remove arquivos .spec
    if exist "!APP_NAME!.spec" del /q "!APP_NAME!.spec"
    if exist "main.spec" del /q "main.spec"

    echo.
    echo ====================================================
    echo   SUCESSO !APP_NAME!.exe pronto na raiz.
    echo ====================================================
) else (
    echo.
    echo [ERRO] Falha na compilacao. Verifique as mensagens acima.
)

echo.
echo Pressione qualquer tecla para fechar...
pause >nul
