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

echo [1/5] Verificando Python !PYTHON_VERSION!...

:: Verifica se o comando 'py' está disponível (Python Launcher)
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [1/5] Usando Python Launcher para garantir Python !PYTHON_VERSION!...
    
    :: Verifica se a versão específica está instalada
    py -0p | findstr /C:"!PYTHON_VERSION!" >nul
    if %ERRORLEVEL% equ 0 (
        echo [1/5] Versão !PYTHON_VERSION! já disponível via Python Launcher
    ) else (
        echo [1/5] Versão !PYTHON_VERSION! não encontrada. Instalando...
        py -m install !PYTHON_VERSION! >nul 2>&1
        if %ERRORLEVEL% equ 0 (
            echo [1/5] Versão !PYTHON_VERSION! instalada com sucesso
        ) else (
            echo [ERRO] Falha ao instalar Python !PYTHON_VERSION!
            pause
            exit /b 1
        )
    )
) else (
    echo [AVISO] Python Launcher (py) nao encontrado.
    echo Por favor, instale o Python Launcher ou verifique a variável de ambiente PATH.
    pause
    exit /b 1
)

:: Cria ou verifica ambiente virtual
if not exist "!VENV_DIR!\Scripts\activate.bat" (
    echo [2/5] Criando ambiente virtual com Python !PYTHON_VERSION!...
    py -!PYTHON_VERSION! -m venv !VENV_DIR!
) else (
    echo [2/5] Ambiente virtual ja existe.
)

echo [3/5] Ativando ambiente e instalando dependencias...
call !VENV_DIR!\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

:: --- 2. Compilacao ---
echo [4/5] Compilando !APP_NAME!...
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