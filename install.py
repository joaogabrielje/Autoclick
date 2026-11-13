#!/usr/bin/env python3
"""
Script de instalação para AutoClicker Pro
Instala todas as dependências necessárias
"""

import subprocess
import sys
import os

def install_dependencies():
    """Instala as dependências do projeto"""
    
    print("=" * 50)
    print("AutoClicker Pro - Instalador de Dependências")
    print("=" * 50)
    print()
    
    dependencies = [
        "pyautogui==0.9.53",
        "keyboard==0.13.5"
    ]
    
    print(f"Instalando {len(dependencies)} dependência(s)...")
    print()
    
    failed = False
    
    for dep in dependencies:
        print(f"Instalando: {dep}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✓ {dep} instalado com sucesso!\n")
        except subprocess.CalledProcessError:
            print(f"✗ Erro ao instalar {dep}\n")
            failed = True
    
    print("=" * 50)
    
    if failed:
        print("⚠️  Alguns pacotes falharam na instalação.")
        print("Tente instalar manualmente:")
        print(f"  python -m pip install {' '.join(dependencies)}")
        return False
    else:
        print("✓ Todas as dependências foram instaladas com sucesso!")
        print()
        print("Você pode agora executar o aplicativo com:")
        print("  python autoclicker.py")
        return True

if __name__ == "__main__":
    success = install_dependencies()
    sys.exit(0 if success else 1)
