@echo off
setlocal enabledelayedexpansion

:: --- Configurações ---
set "VENV_DIR=venv"
set "APP_NAME=treinador"
set "MAIN_FILE=main.py"

echo ====================================================
echo   Configurando Ambiente e Compilando !APP_NAME!
echo ====================================================

:: --- 1. Python e Ambiente Virtual ---
set "PYTHON_VERSION=3.12.10"

echo [1/5] Verificando Python !PYTHON_VERSION! via Python Manager...

:: Verifica se a versao ja esta instalada na listagem do 'py'
py --list | findstr /C:"!PYTHON_VERSION!" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    echo [1/5] Python !PYTHON_VERSION! ja esta pronto para uso.
) else (
    echo [1/5] Python !PYTHON_VERSION! nao encontrado. Instalando via 'py install'...
    
    :: Usa o comando oficial do Python Manager para instalar
    py install !PYTHON_VERSION!
    
    if !ERRORLEVEL! neq 0 (
        echo [ERRO] Falha ao instalar via 'py install'. 
        echo Certifique-se de que o Python Manager (oficial) esta atualizado.
        pause
        exit /b 1
    )
)

if not exist "!VENV_DIR!\Scripts\activate.bat" (
    echo [2/5] Criando ambiente virtual com Python !PYTHON_VERSION!...
    :: Usa o launcher para chamar a versao especifica e criar a venv
    py -!PYTHON_VERSION! -m venv !VENV_DIR!
    
    if !ERRORLEVEL! neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual com a versao !PYTHON_VERSION!.
        pause
        exit /b 1
    )
) else (
    echo [2/5] Ambiente virtual ja existe.
)

echo [3/5] Ativando ambiente e instalando dependencias...
call !VENV_DIR!\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

:: --- 2. Compilacao ---
echo [4/5] Compilando !APP_NAME!...
:: --noconsole: sem janela de terminal
:: --onefile: apenas um executavel
:: --collect-all tensorflow: necessario para apps que usam tensorflow
pyinstaller --noconsole --onefile --collect-all tensorflow --name "!APP_NAME!" "!MAIN_FILE!"

:: --- 3. Limpeza e Finalizacao ---
if exist "dist\!APP_NAME!.exe" (
    echo [5/5] Finalizando: Movendo executavel e limpando arquivos inuteis...
    
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
