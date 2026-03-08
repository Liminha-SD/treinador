@echo off
setlocal enabledelayedexpansion

:: --- Configurações ---
set "VENV_DIR=venv"
set "APP_NAME=treinador"
set "MAIN_FILE=main.py"
set "PYTHON_VERSION=3.12.10"

echo ====================================================
echo   DEBUG: Iniciando script...
echo ====================================================

:: 1. Verifica se o comando 'py' existe
where py >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [ERRO] Comando 'py' nao encontrado no PATH.
    echo Certifique-se de que o Python Launcher ou Python Manager esta instalado.
    pause
    exit /b 1
)

echo [1/5] Verificando Python !PYTHON_VERSION! via Python Manager...

:: Tenta listar as versoes instaladas. 
:: O Python Manager oficial usa 'py --list', o Launcher antigo usa 'py -0'
set "PY_LIST_CMD=py --list"
!PY_LIST_CMD! >nul 2>&1
if !ERRORLEVEL! neq 0 (
    set "PY_LIST_CMD=py -0"
)

echo DEBUG: Usando comando '!PY_LIST_CMD!' para listagem.

!PY_LIST_CMD! | findstr /C:"!PYTHON_VERSION!" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    echo [1/5] Python !PYTHON_VERSION! ja esta instalado.
) else (
    echo [1/5] Python !PYTHON_VERSION! nao encontrado. Tentando instalar...
    
    :: Tenta o comando de instalacao do Python Manager
    py install !PYTHON_VERSION!
    
    if !ERRORLEVEL! neq 0 (
        echo [ERRO] Falha ao instalar via 'py install !PYTHON_VERSION!'.
        echo Verifique se voce tem o Python Manager atualizado (via Microsoft Store ou Winget).
        pause
        exit /b 1
    )
)

:: 2. Criacao da Venv
if not exist "!VENV_DIR!\Scripts\activate.bat" (
    echo [2/5] Criando ambiente virtual com Python !PYTHON_VERSION!...
    py -!PYTHON_VERSION! -m venv !VENV_DIR!
    
    if !ERRORLEVEL! neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual. 
        echo Tentando comando alternativo...
        python -m venv !VENV_DIR!
    )
    
    if not exist "!VENV_DIR!\Scripts\activate.bat" (
        echo [ERRO] Nao foi possivel criar a venv.
        pause
        exit /b 1
    )
) else (
    echo [2/5] Ambiente virtual ja existe.
)

echo [3/5] Ativando ambiente e instalando dependencias...
call !VENV_DIR!\Scripts\activate.bat
if !ERRORLEVEL! neq 0 (
    echo [ERRO] Falha ao ativar a venv.
    pause
    exit /b 1
)

python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo [4/5] Compilando !APP_NAME!...
pyinstaller --noconsole --onefile --collect-all tensorflow --name "!APP_NAME!" "!MAIN_FILE!"

if exist "dist\!APP_NAME!.exe" (
    echo [5/5] Finalizando: Movendo executavel...
    move /y "dist\!APP_NAME!.exe" "." >nul
    if exist "build" rmdir /s /q "build"
    if exist "dist" rmdir /s /q "dist"
    if exist "!APP_NAME!.spec" del /q "!APP_NAME!.spec"
    echo ====================================================
    echo   SUCESSO !APP_NAME!.exe pronto na raiz.
    echo ====================================================
) else (
    echo [ERRO] Falha na compilacao.
)

echo.
echo Pressione qualquer tecla para fechar...
pause >nul
