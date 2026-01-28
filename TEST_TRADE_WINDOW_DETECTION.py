"""
Script de diagnóstico para verificar detección de ventana de trade del NPC.

INSTRUCCIONES:
1. Abre Tibia y colócate frente a un NPC
2. Di "hi" y "trade" o "potions" para abrir la ventana de trade
3. Asegúrate que OBS está capturando la ventana correctamente
4. Ejecuta este script: python TEST_TRADE_WINDOW_DETECTION.py
5. El script mostrará si detecta la ventana y dónde está ubicada
"""

import sys
import cv2
import numpy as np
from src.utils.core import getScreenshot, locate, locateMultiScale
from src.repositories.refill.config import npcTradeBarImages, npcTradeOkImages

def main():
    print("=" * 60)
    print("TEST: Detección de ventana de trade del NPC")
    print("=" * 60)
    
    # Capturar screenshot actual
    print("\n[1/4] Capturando screenshot de OBS...")
    screenshot = getScreenshot()
    
    if screenshot is None:
        print("❌ ERROR: No se pudo capturar screenshot de OBS")
        print("   → Verifica que OBS WebSocket esté activo (127.0.0.1:4455)")
        print("   → Verifica que la ventana proyector esté abierta")
        return 1
    
    print(f"✅ Screenshot capturado: {screenshot.shape[1]}x{screenshot.shape[0]} px")
    
    # Guardar screenshot para inspección visual
    cv2.imwrite('debug/TEST_trade_window_current.png', screenshot)
    print(f"   → Guardado en: debug/TEST_trade_window_current.png")
    
    # Buscar barra superior de la ventana de trade
    print("\n[2/4] Buscando barra superior de ventana de trade...")
    print(f"   Templates disponibles: {len(npcTradeBarImages)}")
    
    trade_bar_pos = None
    for i, template in enumerate(npcTradeBarImages):
        print(f"   Probando template #{i+1}...")
        
        # Intentar con multi-scale
        pos = locateMultiScale(
            screenshot,
            template,
            confidence=0.80,
            scales=(0.75, 0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.25)
        )
        
        if pos is not None:
            trade_bar_pos = pos
            print(f"   ✅ Encontrado con multi-scale en posición: {pos}")
            break
            
        # Intentar con escala 1:1
        pos = locate(screenshot, template, confidence=0.80)
        if pos is not None:
            trade_bar_pos = pos
            print(f"   ✅ Encontrado con escala 1:1 en posición: {pos}")
            break
    
    if trade_bar_pos is None:
        print("   ❌ NO DETECTADO")
        print("\n" + "=" * 60)
        print("DIAGNÓSTICO: Ventana de trade NO detectada")
        print("=" * 60)
        print("\nPOSIBLES CAUSAS:")
        print("1. La ventana de trade no está abierta")
        print("2. La ventana de trade está fuera del área de captura de OBS")
        print("3. El estilo/tema de tu cliente Tibia es diferente")
        print("4. La escala de captura es muy diferente")
        print("\nSOLUCIONES:")
        print("A) Asegúrate de decir 'hi' y 'trade'/'potions' al NPC")
        print("B) Ajusta la captura de OBS para incluir toda la ventana de trade")
        print("C) Toma un screenshot de la barra superior de la ventana de trade")
        print("   y guárdala como:")
        print("   src/repositories/refill/images/npcTradeBar_user.png")
        return 1
    
    x, y, w, h = trade_bar_pos
    print(f"\n✅ Barra de trade detectada en: x={x}, y={y}, w={w}, h={h}")
    
    # Buscar botón OK en la parte inferior
    print("\n[3/4] Buscando botón OK...")
    print(f"   Templates disponibles: {len(npcTradeOkImages)}")
    
    # Recortar región donde debería estar el botón OK
    crop_width = 174
    for tpl in npcTradeOkImages:
        try:
            crop_width = max(crop_width, int(tpl.shape[1]) + 20)
        except Exception:
            pass
    
    cropped = screenshot[y:, x:min(x + crop_width, screenshot.shape[1])]
    
    ok_button_pos = None
    for i, template in enumerate(npcTradeOkImages):
        print(f"   Probando template #{i+1}...")
        
        # Intentar con multi-scale
        pos = locateMultiScale(
            cropped,
            template,
            confidence=0.80,
            scales=(0.75, 0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.25)
        )
        
        if pos is not None:
            ok_button_pos = pos
            print(f"   ✅ Encontrado con multi-scale en posición: {pos}")
            break
            
        # Intentar con escala 1:1
        pos = locate(cropped, template, confidence=0.80)
        if pos is not None:
            ok_button_pos = pos
            print(f"   ✅ Encontrado con escala 1:1 en posición: {pos}")
            break
    
    if ok_button_pos is None:
        print("   ⚠️ Botón OK no detectado (puede ser normal si la ventana está vacía)")
    else:
        print(f"\n✅ Botón OK detectado en posición relativa: {ok_button_pos}")
    
    # Dibujar marcadores en el screenshot
    print("\n[4/4] Generando imagen de diagnóstico...")
    debug_img = cv2.cvtColor(screenshot, cv2.COLOR_GRAY2BGR)
    
    # Dibujar rectángulo alrededor de la barra de trade
    cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.putText(debug_img, "Trade Bar", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Dibujar posición del botón X de cierre (donde hace click el bot)
    close_x = x + 165
    close_y = y + 7
    cv2.circle(debug_img, (close_x, close_y), 5, (0, 0, 255), -1)
    cv2.putText(debug_img, "Close (X)", (close_x + 10, close_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    
    if ok_button_pos:
        ok_x, ok_y, ok_w, ok_h = ok_button_pos
        abs_ok_y = y + ok_y
        cv2.rectangle(debug_img, (x + ok_x, abs_ok_y), (x + ok_x + ok_w, abs_ok_y + ok_h), (255, 0, 0), 2)
        cv2.putText(debug_img, "OK Button", (x + ok_x, abs_ok_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        # Calcular y marcar posiciones de interacción
        bx, by = x, y + ok_y + 26
        
        # Searchbox
        search_x, search_y = bx + 160, by - 75
        cv2.circle(debug_img, (search_x, search_y), 3, (255, 255, 0), -1)
        cv2.putText(debug_img, "Search", (search_x + 5, search_y), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 0), 1)
        
        # Amount input
        amount_x, amount_y = bx + 115, by - 42
        cv2.circle(debug_img, (amount_x, amount_y), 3, (255, 165, 0), -1)
        cv2.putText(debug_img, "Amount", (amount_x + 5, amount_y), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 165, 0), 1)
        
        # Confirm button
        confirm_x, confirm_y = bx + 150, by - 18
        cv2.circle(debug_img, (confirm_x, confirm_y), 3, (0, 255, 255), -1)
        cv2.putText(debug_img, "Confirm", (confirm_x + 5, confirm_y), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1)
    
    cv2.imwrite('debug/TEST_trade_window_annotated.png', debug_img)
    print(f"✅ Imagen anotada guardada en: debug/TEST_trade_window_annotated.png")
    
    # Resumen final
    print("\n" + "=" * 60)
    print("RESULTADO DEL TEST")
    print("=" * 60)
    print("✅ Ventana de trade DETECTADA correctamente")
    print(f"\nPosiciones de interacción:")
    print(f"  • Barra de trade: ({x}, {y})")
    print(f"  • Botón cerrar (X): ({close_x}, {close_y})")
    
    if ok_button_pos:
        bx, by = x, y + ok_button_pos[1] + 26
        print(f"  • Searchbox: ({bx + 160}, {by - 75})")
        print(f"  • Amount input: ({bx + 115}, {by - 42})")
        print(f"  • Confirm button: ({bx + 150}, {by - 18})")
    
    print("\n✅ El bot debería poder interactuar con la ventana de trade")
    print("\nSi el bot sigue sin funcionar:")
    print("  1. Verifica que el NPC responda a 'hi' y 'trade'/'potions'")
    print("  2. Verifica que la ventana de trade tenga items para comprar")
    print("  3. Compara TEST_trade_window_current.png con lo que ves en Tibia")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
