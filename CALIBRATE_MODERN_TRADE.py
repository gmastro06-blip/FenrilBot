"""
Script de calibración para la UI moderna de trade.

Este script te permite probar paso a paso cada acción del proceso de compra
para verificar que las coordenadas son correctas.

INSTRUCCIONES:
1. Abre Tibia y colócate frente al NPC
2. Di "hi" y "trade" manualmente
3. Ejecuta: python CALIBRATE_MODERN_TRADE.py
4. Sigue las instrucciones en pantalla
"""

import sys
from time import sleep
from src.utils.core import getScreenshot
from src.repositories.refill.modern_ui import (
    clickModernTradeSearchBox,
    searchItemInModernTrade,
    clickFirstItemInModernTrade,
    setAmountInModernTrade,
    clickBuyButtonInModernTrade,
    closeModernTradeWindow
)

def pause_for_user(message: str):
    """Pausa para que el usuario pueda ver el resultado."""
    input(f"\n{message}\nPresiona ENTER para continuar...")

def main():
    print("=" * 70)
    print("CALIBRACIÓN DE UI MODERNA DE TRADE")
    print("=" * 70)
    print("\nEste script probará cada paso del proceso de compra.")
    print("Verifica que las acciones se ejecuten correctamente en Tibia.")
    print("\nASEGÚRATE DE:")
    print("  1. Estar en Tibia frente a un NPC")
    print("  2. Haber dicho 'hi' y 'trade' para abrir la ventana")
    print("  3. La ventana de trade esté visible y capturada por OBS")
    
    pause_for_user("\n¿Listo para empezar?")
    
    # Capturar screenshot inicial
    print("\n[Paso 0] Capturando screenshot...")
    screenshot = getScreenshot()
    
    if screenshot is None:
        print("❌ ERROR: No se pudo capturar screenshot")
        return 1
    
    print(f"✅ Screenshot capturado: {screenshot.shape[1]}x{screenshot.shape[0]} px")
    
    # Paso 1: Click en searchbox
    print("\n" + "=" * 70)
    print("[Paso 1] CLICK EN SEARCHBOX")
    print("=" * 70)
    print("El bot hará click en el searchbox y lo limpiará.")
    print("Verifica que:")
    print("  - El cursor aparezca en el campo 'Type to search'")
    print("  - El texto previo se borre")
    
    pause_for_user("Presiona ENTER para probar...")
    
    result = clickModernTradeSearchBox(screenshot)
    print(f"Resultado: {'✅ Éxito' if result else '❌ Falló'}")
    
    sleep(1)
    
    # Paso 2: Escribir nombre de item
    print("\n" + "=" * 70)
    print("[Paso 2] BUSCAR ITEM")
    print("=" * 70)
    print("El bot escribirá 'mana potion' en el searchbox.")
    print("Verifica que:")
    print("  - El texto aparezca en el searchbox")
    print("  - La lista se filtre mostrando solo mana potions")
    
    pause_for_user("Presiona ENTER para probar...")
    
    result = searchItemInModernTrade(screenshot, "mana potion")
    print(f"Resultado: {'✅ Éxito' if result else '❌ Falló'}")
    
    sleep(1)
    
    # Paso 3: Click en el primer item
    print("\n" + "=" * 70)
    print("[Paso 3] CLICK EN PRIMER ITEM")
    print("=" * 70)
    print("El bot hará click en el primer item de la lista filtrada.")
    print("Verifica que:")
    print("  - Se seleccione el primer mana potion de la lista")
    print("  - El item aparezca seleccionado/resaltado")
    
    pause_for_user("Presiona ENTER para probar...")
    
    result = clickFirstItemInModernTrade(screenshot)
    print(f"Resultado: {'✅ Éxito' if result else '❌ Falló'}")
    
    sleep(1)
    
    # Paso 4: Establecer cantidad
    print("\n" + "=" * 70)
    print("[Paso 4] ESTABLECER CANTIDAD")
    print("=" * 70)
    print("El bot establecerá la cantidad a 10.")
    print("Verifica que:")
    print("  - El campo 'Amount' se llene con el número 10")
    print("  - El precio total se actualice")
    
    pause_for_user("Presiona ENTER para probar...")
    
    result = setAmountInModernTrade(screenshot, 10)
    print(f"Resultado: {'✅ Éxito' if result else '❌ Falló'}")
    
    sleep(1)
    
    # Paso 5: Click en Buy
    print("\n" + "=" * 70)
    print("[Paso 5] CLICK EN BUY")
    print("=" * 70)
    print("⚠️ ATENCIÓN: Esto COMPRARÁ realmente las pociones!")
    print("Si no quieres comprar, cancela ahora con Ctrl+C")
    print("\nEl bot hará click en el botón 'Buy'.")
    print("Verifica que:")
    print("  - Las pociones se compren")
    print("  - Tu gold disminuya")
    print("  - Las pociones aparezcan en tu inventario")
    
    try:
        pause_for_user("Presiona ENTER para COMPRAR (Ctrl+C para cancelar)...")
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado por el usuario")
        return 0
    
    result = clickBuyButtonInModernTrade(screenshot)
    print(f"Resultado: {'✅ Éxito' if result else '❌ Falló'}")
    
    sleep(2)
    
    # Paso 6: Limpiar searchbox (opcional, ya lo hace clickModernTradeSearchBox)
    print("\n" + "=" * 70)
    print("[Paso 6] LIMPIAR SEARCHBOX")
    print("=" * 70)
    print("El bot limpiará el searchbox.")
    
    pause_for_user("Presiona ENTER para probar...")
    
    result = clickModernTradeSearchBox(screenshot)
    print(f"Resultado: {'✅ Éxito' if result else '❌ Falló'}")
    
    sleep(1)
    
    # Paso 7: Cerrar ventana
    print("\n" + "=" * 70)
    print("[Paso 7] CERRAR VENTANA")
    print("=" * 70)
    print("El bot hará click en el botón X para cerrar la ventana.")
    print("Verifica que:")
    print("  - La ventana de trade se cierre")
    
    pause_for_user("Presiona ENTER para probar...")
    
    result = closeModernTradeWindow(screenshot)
    print(f"Resultado: {'✅ Éxito' if result else '❌ Falló'}")
    
    # Resumen final
    print("\n" + "=" * 70)
    print("CALIBRACIÓN COMPLETADA")
    print("=" * 70)
    print("\n¿Todos los pasos funcionaron correctamente?")
    print("\nSi algún paso falló:")
    print("  1. Anota qué paso falló y qué sucedió")
    print("  2. Las coordenadas pueden necesitar ajuste manual")
    print("  3. Verifica que la resolución sea 1920x1080")
    print("  4. Verifica que OBS capture toda la ventana de trade")
    print("\nSi todo funcionó:")
    print("  ✅ El bot está listo para hacer refills automáticamente!")
    print("  → Ejecuta: python run_bot_persistent.py")
    print("  → Presiona INSERT para activar")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
