import cv2
from pathlib import Path
from src.utils.core import locateMultiScale
from src.repositories.chat.config import images

img_path = Path('debug/chat_fail_1769458148.png')
screenshot = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
print('screenshot', getattr(screenshot,'shape',None))
h, w = screenshot.shape[:2]
roi = screenshot[int(h*0.55):h, 0:int(w*0.9)]
print('roi', roi.shape)
scales = (0.40,0.45,0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90,0.95,1.0,1.05,1.10,1.15,1.20)
for tab_key, name in [('loot','loot'),('localChat','local chat'),('npcs','npcs')]:
    best=None
    for variant, templ in images['tabs'][tab_key].items():
        bbox = locateMultiScale(roi, templ, confidence=0.60, scales=scales)
        if bbox:
            best=(variant,bbox)
            break
    print(name, best)

