@echo off
REM Script para instalar dependências e executar o AutoClicker

echo Instalando dependencias...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo Erro na instalacao de dependencias
    pause
    exit /b 1
)

echo Iniciando AutoClicker...
python autoclicker.py

pause
