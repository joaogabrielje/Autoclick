#!/usr/bin/env python3
"""
Script de teste para AutoClicker Pro
Verifica se todas as dependências estão instaladas corretamente
"""

import sys

def test_imports():
    """Testa se todas as importações funcionam"""
    
    print("=" * 50)
    print("AutoClicker Pro - Teste de Dependências")
    print("=" * 50)
    print()
    
    tests = [
        ("tkinter", "Interface Gráfica"),
        ("pyautogui", "Controle do Mouse"),
        ("keyboard", "Controle do Teclado"),
        ("threading", "Multi-threading"),
        ("json", "Salvamento de Configurações"),
    ]
    
    all_ok = True
    
    for module_name, description in tests:
        try:
            __import__(module_name)
            print(f"✓ {module_name:15} - {description}")
        except ImportError as e:
            print(f"✗ {module_name:15} - {description} [ERRO]")
            print(f"  └─ {str(e)}")
            all_ok = False
    
    print()
    print("=" * 50)
    
    if all_ok:
        print("✓ Todas as dependências estão OK!")
        print()
        print("Você pode iniciar o aplicativo com:")
        print("  python autoclicker.py")
        return True
    else:
        print("✗ Faltam algumas dependências.")
        print()
        print("Execute o instalador:")
        print("  python install.py")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
