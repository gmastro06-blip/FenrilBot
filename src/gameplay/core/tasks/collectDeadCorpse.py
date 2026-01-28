from typing import Any, Optional
import os
import time

from src.gameplay.typings import Context
from src.gameplay.utils import coordinatesAreEqual
import src.repositories.gameWindow.slot as gameWindowSlot
import src.repositories.gameWindow.core as gameWindowCore
import src.utils.keyboard as utilsKeyboard
from .common.base import BaseTask
from src.utils.runtime_settings import get_int, get_str
from src.repositories.inventory.core import images as inv_images
from src.utils.core import locate, locateMultiScale, locateMultiple, getScreenshot
from src.utils.mouse import drag
from src.utils.console_log import log_throttled
import pathlib
import cv2
import numpy as np

from src.shared.typings import GrayImage


# ===== CONSTANTES DE CONFIGURACIÓN =====
# Umbrales para detección de slots vacíos en loot
EMPTY_SLOT_SCORE_THRESHOLD = 0.94  # Correlación mínima para considerar slot vacío
EMPTY_SLOT_MAD_THRESHOLD = 10.0    # MAD máximo para confirmar similitud visual
EMPTY_SLOT_CONFIDENCE = 0.86       # Confianza mínima en template matching


# TODO: check if something was looted or exactly count was looted
class CollectDeadCorpseTask(BaseTask):
    def __init__(self: "CollectDeadCorpseTask", creature: Any) -> None:
        # Non-terminable: looting may require multiple ticks (open corpse -> drag items).
        super().__init__(delayOfTimeout=8.0, shouldTimeoutTreeWhenTimeout=True)
        self.name = 'collectDeadCorpse'
        self.delayBeforeStart = 0.85
        self.creature = creature
        self.terminable = False
        self.timeout_config_path = 'ng_runtime.task_timeouts.collectDeadCorpse'
        self.timeout_env_var = 'FENRIL_COLLECT_DEAD_CORPSE_TIMEOUT'
        self.timeout_default = 8.0
        self._no_item_ticks = 0
        self._alt_click_attempted = False
        self._modifier_pressed: Optional[str] = None

    def __del__(self) -> None:
        """Safety: ensure modifiers are released even if task is destroyed mid-execution."""
        if self._modifier_pressed is not None:
            try:
                utilsKeyboard.keyUp(self._modifier_pressed)
            except Exception:
                pass
    
    def onTimeout(self, context: Context) -> Context:
        """CRÍTICO: Limpiar corpse de la cola cuando falla para evitar bucles infinitos."""
        try:
            queue = context.get('loot', {}).get('corpsesToLoot', [])
            if isinstance(queue, list) and self.creature in queue:
                queue.remove(self.creature)
                log_throttled(
                    'loot.corpse.timeout_removed',
                    'warn',
                    'collectDeadCorpse timeout: removed corpse from queue to prevent loop',
                    2.0,
                )
        except Exception:
            pass
        return context

    def _dump_loot_debug(self, context: Context, tag: str, extra: Optional[dict] = None) -> None:
        if not get_str(context, 'ng_runtime.dump_loot_debug', env_var='FENRIL_DUMP_LOOT_DEBUG', default='0').strip() in {'1', 'true', 'yes'}:
            return
        screenshot = context.get('ng_screenshot')
        if screenshot is None:
            return
        try:
            debug_dir = pathlib.Path('debug')
            debug_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime('%Y%m%d_%H%M%S')
            img_path = debug_dir / f'loot_debug_{tag}_{ts}.png'
            meta_path = debug_dir / f'loot_debug_{tag}_{ts}.json'
            cv2.imwrite(str(img_path), np.ascontiguousarray(screenshot))
            try:
                import json

                meta = extra or {}

                # Resolve effective settings so debug dumps match actual behavior.
                account = get_str(
                    context,
                    'ng_runtime.account_type',
                    env_var='FENRIL_ACCOUNT_TYPE',
                    default='premium',
                    prefer_env=True,
                ).strip().lower()
                default_method = 'open_drag' if account in {'free', 'facc', 'freeaccount', 'free_account'} else 'quick'
                loot_method = get_str(
                    context,
                    'ng_runtime.loot_method',
                    env_var='FENRIL_LOOT_METHOD',
                    default=default_method,
                    prefer_env=True,
                ).strip().lower()

                default_modifier = 'none' if loot_method == 'open_drag' else 'shift'
                loot_modifier_raw = get_str(
                    context,
                    'ng_runtime.loot_modifier',
                    env_var='FENRIL_LOOT_MODIFIER',
                    default=default_modifier,
                ).strip().lower()
                if loot_modifier_raw in {'control', 'ctl'}:
                    loot_modifier_raw = 'ctrl'
                loot_modifier = loot_modifier_raw
                if loot_method == 'open_drag' and loot_modifier == 'shift' and not os.getenv('FENRIL_LOOT_MODIFIER'):
                    loot_modifier = 'none'

                default_click = 'left' if loot_method == 'open_drag' else 'right'
                loot_click_raw = get_str(
                    context,
                    'ng_runtime.loot_click',
                    env_var='FENRIL_LOOT_CLICK',
                    default=default_click,
                    prefer_env=True,
                ).strip().lower()
                loot_click = loot_click_raw if loot_click_raw in {'left', 'right'} else default_click
                # Per user requirement: opening corpses should be left-click.
                # In open+drag mode we enforce left-click to avoid classic/modern scheme ambiguity.
                if loot_method == 'open_drag':
                    loot_click = 'left'

                meta.update({
                    'tag': tag,
                    'account_type': account,
                    'loot_method': loot_method,
                    'loot_click': loot_click,
                    'loot_modifier': loot_modifier,
                    'loot_click_raw': loot_click_raw,
                    'loot_modifier_raw': loot_modifier_raw,
                    'ng_backpacks': context.get('ng_backpacks'),
                })
                meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
            except Exception:
                pass
            log_throttled('loot.debug.dump', 'info', f'loot debug dump: {img_path}', 2.0)
        except Exception:
            return

    def _empty_slot_score(self, slot_img: GrayImage, empty_tpl: GrayImage) -> float:
        try:
            if slot_img.shape[:2] != empty_tpl.shape[:2]:
                return -1.0
            match = cv2.matchTemplate(slot_img, empty_tpl, cv2.TM_CCOEFF_NORMED)
            return float(match[0][0])
        except Exception:
            return -1.0

    def _empty_slot_mad(self, slot_img: GrayImage, empty_tpl: GrayImage) -> float:
        """Mean absolute difference between slot and empty template (same size).

        Useful when template correlation is too forgiving (items still match the empty border).
        """
        try:
            if slot_img.shape[:2] != empty_tpl.shape[:2]:
                return 1e9
            diff = cv2.absdiff(slot_img, empty_tpl)
            return float(np.mean(diff))
        except Exception:
            return 1e9

    def _subtract_bboxes(
        self,
        after: list[tuple[int, int, int, int]],
        before: list[tuple[int, int, int, int]],
        *,
        tol: int = 8,
    ) -> list[tuple[int, int, int, int]]:
        if not after:
            return []
        if not before:
            return after

        out: list[tuple[int, int, int, int]] = []
        for ax, ay, aw, ah in after:
            found = False
            for bx, by, bw, bh in before:
                if abs(ax - bx) <= tol and abs(ay - by) <= tol and abs(aw - bw) <= tol and abs(ah - bh) <= tol:
                    found = True
                    break
            if not found:
                out.append((ax, ay, aw, ah))
        return out

    def _locate_container_bar(
        self: "CollectDeadCorpseTask",
        screenshot: Optional[GrayImage],
        bar_img: Optional[GrayImage],
    ) -> Optional[tuple[int, int, int, int]]:
        if screenshot is None or bar_img is None:
            return None
        pos = locate(screenshot, bar_img, confidence=0.82)
        if pos is not None:
            return pos
        return locateMultiScale(
            screenshot,
            bar_img,
            confidence=0.78,
            scales=(0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20),
        )

    def _locate_container_bar_by_name(
        self: "CollectDeadCorpseTask",
        screenshot: Optional[GrayImage],
        name: Optional[str],
    ) -> Optional[tuple[int, int, int, int]]:
        if screenshot is None or not name:
            return None
        candidate_keys = [name]
        try:
            candidate_keys.extend(
                [
                    k
                    for k in inv_images.get('containersBars', {}).keys()
                    if isinstance(k, str) and k != name and k.startswith(name + ' ')
                ]
            )
        except Exception:
            pass

        for k in candidate_keys:
            bar_img = inv_images.get('containersBars', {}).get(k)
            if bar_img is None:
                continue
            pos = self._locate_container_bar(screenshot, bar_img)
            if pos is not None:
                return pos
        return None

    def _open_nearby_corpses(
        self,
        context: Context,
        *,
        click: str,
        modifier: str,
        target_coordinate: Optional[tuple[int, int, int]] = None,
        current_coordinate: Optional[tuple[int, int, int]] = None,
        max_clicks: int = 2,
    ) -> None:
        game_window_pos = context.get('gameWindow', {}).get('coordinate')
        if game_window_pos is None:
            log_throttled('loot.open_corpses.no_game_window', 'warn', 'Loot: game window not detected; skipping corpse open clicks', 5.0)
            return

        # Avoid clicking under open container windows (backpacks) that overlap the game window.
        screenshot = context.get('ng_screenshot')
        exclusions: list[tuple[int, int, int, int]] = []
        try:
            bps = context.get('ng_backpacks', {})
            main_bp = bps.get('main')
            loot_bp = bps.get('loot')
        except Exception:
            main_bp = None
            loot_bp = None

        if screenshot is not None:
            for bp_name in [main_bp, loot_bp]:
                if not bp_name:
                    continue
                bar = self._locate_container_bar_by_name(screenshot, str(bp_name))
                if bar is None:
                    continue
                bx, by, bw, bh = bar
                exclusions.append((int(bx - 20), int(by - 20), int(bx + bw + 420), int(by + 520)))

        def _in_exclusion(pt: tuple[int, int]) -> bool:
            x, y = int(pt[0]), int(pt[1])
            for (l, t, r, b) in exclusions:
                if l <= x <= r and t <= y <= b:
                    return True
            return False

        def _slot_click_point(slot: tuple[int, int]) -> Optional[tuple[int, int]]:
            try:
                x, y = gameWindowSlot.getSlotPosition(slot, game_window_pos)
            except Exception:
                return None
            if click == 'left':
                # Match gameWindowSlot.clickUseBySlot() offset.
                return (int(x + 15), int(y + 25))
            return (int(x), int(y))

        pressed_modifier = bool(modifier) and modifier != 'none'
        if pressed_modifier:
            utilsKeyboard.keyDown(modifier)
            self._modifier_pressed = modifier
        try:
            # Critical: don't spam-click random ground tiles.
            # Left-click on empty ground tends to move the character, which prevents looting.
            # Prefer the *known corpse tile* (if available), then player's tile, then a small safe ring.
            slots: list[tuple[int, int]] = []
            
            # ERROR 4: Búsqueda en espiral alrededor del corpse target para encontrarlo visualmente
            # en lugar de asumir que el player está siempre en (7,5).
            if target_coordinate is not None and current_coordinate is not None:
                try:
                    corpse_slot = gameWindowCore.getSlotFromCoordinate(current_coordinate, target_coordinate)
                except Exception:
                    corpse_slot = None
                
                if corpse_slot is not None:
                    # Prioridad 1: slot calculado del corpse
                    try:
                        slots.append((int(corpse_slot[0]), int(corpse_slot[1])))
                    except Exception:
                        pass
                    
                    # Prioridad 2: Búsqueda en espiral alrededor del slot calculado (para compensar errores)
                    # Espiral: centro, arriba, derecha, abajo, izquierda, luego diagonal
                    try:
                        cx, cy = int(corpse_slot[0]), int(corpse_slot[1])
                        spiral = [
                            (cx, cy-1), (cx+1, cy), (cx, cy+1), (cx-1, cy),  # cruz
                            (cx+1, cy-1), (cx+1, cy+1), (cx-1, cy+1), (cx-1, cy-1),  # diagonales
                        ]
                        for sx, sy in spiral:
                            if 0 <= sx <= 14 and 0 <= sy <= 10:  # bounds check
                                slots.append((sx, sy))
                    except Exception:
                        pass

            # Player tile (corpse often ends up under us after walkToCoordinate).
            slots.append((7, 5))

            # Fallback ring around player (kept small to minimize unintended walking).
            slots.extend([(7, 4), (6, 5), (8, 5), (7, 6)])

            # De-duplicate while preserving order.
            seen: set[tuple[int, int]] = set()
            deduped: list[tuple[int, int]] = []
            for s in slots:
                if s in seen:
                    continue
                seen.add(s)
                deduped.append(s)
            slots = deduped
            clicked = 0
            skipped = 0
            if max_clicks < 1:
                max_clicks = 1
            if max_clicks > 6:
                max_clicks = 6

            for s in slots:
                if clicked >= max_clicks:
                    break
                pt = _slot_click_point(s)
                if pt is None:
                    continue
                if exclusions and _in_exclusion(pt):
                    skipped += 1
                    log_throttled(
                        f'loot.open.skip_{s[0]}_{s[1]}',
                        'debug',
                        f'Loot: skipped click at slot {s} (blocked by backpack at {pt})',
                        5.0,
                    )
                    continue
                if click == 'left':
                    gameWindowSlot.clickUseBySlot(s, game_window_pos)
                else:
                    gameWindowSlot.rightClickSlot(s, game_window_pos)
                clicked += 1
                log_throttled(
                    f'loot.open.click_{clicked}',
                    'info',
                    f'Loot: clicked slot {s} ({clicked}/{max_clicks}) at screen pos {pt}',
                    2.0,
                )
                
                # CRÍTICO: Siempre dar tiempo al servidor para procesar CADA click
                # Evita que el input queue de Tibia descarte clicks en ráfaga
                time.sleep(0.15)
                if clicked >= max_clicks:
                    break

            if clicked == 0 and exclusions:
                log_throttled(
                    'loot.open_corpses.blocked',
                    'warn',
                    'Loot: corpse open clicks were blocked by overlapping backpack windows; move backpacks away from the center of the game window',
                    5.0,
                )
        finally:
            if pressed_modifier:
                try:
                    utilsKeyboard.keyUp(modifier)
                    self._modifier_pressed = None
                except Exception:
                    # Aún en caso de error, limpiar el flag para evitar doble-release
                    self._modifier_pressed = None

    def _drag_one_item_from_open_corpse(
        self,
        context: Context,
        *,
        empties_hint: Optional[list[tuple[int, int, int, int]]] = None,
        debug_extra: Optional[dict] = None,
    ) -> bool:
        screenshot = context.get('ng_screenshot')
        if screenshot is None:
            log_throttled('loot.drag.no_screenshot', 'warn', 'Loot drag: no screenshot available', 5.0)
            return False

        loot_bp = None
        try:
            loot_bp = context.get('ng_backpacks', {}).get('loot')
        except Exception:
            loot_bp = None
        if not loot_bp:
            return False

        loot_bar = self._locate_container_bar_by_name(screenshot, loot_bp)
        if loot_bar is None:
            log_throttled('loot.open_drag.no_loot_bp', 'warn', 'Loot open+drag: loot backpack bar not found (is loot backpack open/visible?)', 5.0)
            self._dump_loot_debug(context, 'no_loot_backpack')
            return False
        loot_x, loot_y, loot_w, loot_h = loot_bar
        empty_tpl = inv_images.get('slots', {}).get('empty')
        if empty_tpl is None:
            return False

        # Pick a precise drop target: center of the first empty slot inside the loot backpack.
        # This is much more reliable than a fixed offset (different container sizes/positions).
        drop_to: tuple[int, int]
        loot_content = (
            int(loot_x - 20),
            int(loot_y + loot_h + 2),
            int(loot_x + loot_w + 420),
            int(loot_y + 520),
        )
        empties_all = locateMultiple(screenshot, empty_tpl, confidence=EMPTY_SLOT_CONFIDENCE)
        loot_empties = [
            b
            for b in empties_all
            if loot_content[0] <= int(b[0]) <= loot_content[2] and loot_content[1] <= int(b[1]) <= loot_content[3]
        ]
        if loot_empties:
            # Top-to-bottom, left-to-right.
            loot_empties.sort(key=lambda b: (int(b[1]), int(b[0])))
            ex, ey, ew, eh = loot_empties[0]
            drop_to = (int(ex + ew // 2), int(ey + eh // 2))
        else:
            # ERROR 5: Fallback más seguro usando center del loot bar
            drop_to = (int(loot_x + loot_w // 2), int(loot_y + loot_h + 40))
            # Validar que esté dentro de loot_content
            if not (loot_content[0] <= drop_to[0] <= loot_content[2] and
                    loot_content[1] <= drop_to[1] <= loot_content[3]):
                log_throttled('loot.drop.invalid', 'warn', 'Loot backpack too small or offscreen; cannot drop safely', 2.0)
                self._dump_loot_debug(context, 'drop_target_outside_backpack', extra={'drop_to': list(drop_to), 'loot_content': list(loot_content)})
                return False

        # Exclude known container windows to avoid dragging from our own backpacks.
        exclusions: list[tuple[int, int, int, int]] = []
        try:
            main_bp = context.get('ng_backpacks', {}).get('main')
        except Exception:
            main_bp = None
        for bp_name in [main_bp, loot_bp]:
            if not bp_name:
                continue
            bar = self._locate_container_bar_by_name(screenshot, bp_name)
            if bar is None:
                continue
            bx, by, bw, bh = bar
            # Heuristic: container content sits below the bar.
            # Keep this generous; excluding too much is safer than dragging from the wrong container.
            # CRÍTICO: Ampliar exclusión para cubrir completamente el backpack y evitar clicks accidentales
            exclusions.append((int(bx - 30), int(by - 30), int(bx + bw + 450), int(by + 550)))

        empties = empties_hint if empties_hint else locateMultiple(screenshot, empty_tpl, confidence=EMPTY_SLOT_CONFIDENCE)
        if not empties:
            self._dump_loot_debug(context, 'no_empty_slots', extra=debug_extra)
            return False

        def _in_exclusion(x: int, y: int) -> bool:
            for (l, t, r, b) in exclusions:
                if l <= x <= r and t <= y <= b:
                    return True
            return False

        candidates = [b for b in empties if not _in_exclusion(int(b[0]), int(b[1]))]
        if len(candidates) < 3:
            log_throttled(
                'loot.drag.no_candidates',
                'warn',
                f'Loot drag: not enough non-excluded empty slots found ({len(candidates)}/3 needed); corpse may not be open or is covered by backpacks',
                2.0,
            )
            self._dump_loot_debug(context, 'no_candidates', extra=debug_extra)
            return False

        # Cluster by coarse grid cell so we pick the container-like cluster.
        clusters: dict[tuple[int, int], list[tuple[int, int, int, int]]] = {}
        cell = 220
        for b in candidates:
            key = (int(b[0]) // cell, int(b[1]) // cell)
            clusters.setdefault(key, []).append(b)
        cluster = max(clusters.values(), key=lambda v: len(v))

        xs = sorted({int(b[0]) for b in cluster})
        ys = sorted({int(b[1]) for b in cluster})
        if not xs or not ys:
            self._dump_loot_debug(context, 'empty_cluster', extra=debug_extra)
            return False

        # Try to drag the first non-empty slot we can find within this container grid.
        tpl_w = int(cluster[0][2]) if cluster else 32
        tpl_h = int(cluster[0][3]) if cluster else 32
        for y in ys:
            for x in xs:
                if x < 0 or y < 0:
                    continue
                if (y + tpl_h) > int(screenshot.shape[0]) or (x + tpl_w) > int(screenshot.shape[1]):
                    continue
                slot_img = screenshot[y:y + tpl_h, x:x + tpl_w]

                # Consider slot empty only if it matches the empty template strongly AND looks
                # visually close (MAD low). This reduces false "empty" when an item overlays the slot.
                score = self._empty_slot_score(slot_img, empty_tpl)
                mad = self._empty_slot_mad(slot_img, empty_tpl)
                if score >= EMPTY_SLOT_SCORE_THRESHOLD and mad <= EMPTY_SLOT_MAD_THRESHOLD:
                    continue
                drag((int(x + tpl_w // 2), int(y + tpl_h // 2)), drop_to)
                time.sleep(0.35)
                return True

        extra2 = dict(debug_extra or {})
        try:
            extra2.update({
                'drop_to': [int(drop_to[0]), int(drop_to[1])],
                'loot_bar': [int(loot_x), int(loot_y), int(loot_w), int(loot_h)],
                'empty_count': int(len(empties)),
                'candidate_count': int(len(candidates)),
                'cluster_size': int(len(cluster)),
            })
        except Exception:
            pass
        self._dump_loot_debug(context, 'no_nonempty_slot_found', extra=extra2)
        return False

    def do(self, context: Context) -> Context:
        # MEJORA 1: Validar precondiciones críticas
        screenshot = context.get('ng_screenshot')
        game_window_pos = context.get('gameWindow', {}).get('coordinate')
        if screenshot is None:
            log_throttled('loot.precond.no_screenshot', 'warn', 'collectDeadCorpse: no screenshot available; skipping tick', 2.0)
            return context
        if game_window_pos is None:
            log_throttled('loot.precond.no_gamewindow', 'warn', 'collectDeadCorpse: game window not detected; skipping tick', 2.0)
            return context
        
        # ERROR 1: Forzar captura fresca para evitar race condition screenshot/OBS
        # El screenshot en context podría ser del frame anterior, causando misdetection.
        try:
            fresh_screenshot = getScreenshot()
            if fresh_screenshot is not None:
                context['ng_screenshot'] = fresh_screenshot
                screenshot = fresh_screenshot
        except Exception:
            pass
        
        # Account type drives the default method.
        account = get_str(
            context,
            'ng_runtime.account_type',
            env_var='FENRIL_ACCOUNT_TYPE',
            default='premium',
            prefer_env=True,
        ).strip().lower()
        default_method = 'open_drag' if account in {'free', 'facc', 'freeaccount', 'free_account'} else 'quick'
        loot_method = get_str(
            context,
            'ng_runtime.loot_method',
            env_var='FENRIL_LOOT_METHOD',
            default=default_method,
            prefer_env=True,
        ).strip().lower()

        # Modifier is only needed for premium quick-loot.
        # For free/open-drag, holding Shift while clicking corpses can prevent opening them.
        default_modifier = 'none' if loot_method == 'open_drag' else 'shift'
        loot_modifier = get_str(
            context,
            'ng_runtime.loot_modifier',
            env_var='FENRIL_LOOT_MODIFIER',
            default=default_modifier,
        ).strip().lower()
        if loot_modifier in {'control', 'ctl'}:
            loot_modifier = 'ctrl'

        # UI/runtime defaults set this to "shift"; treat that as "unset" for open_drag unless the
        # user explicitly overrides via env var.
        if loot_method == 'open_drag' and loot_modifier == 'shift' and not os.getenv('FENRIL_LOOT_MODIFIER'):
            loot_modifier = 'none'

        # How to interact with corpses on the ground.
        # - Modern controls: left-click usually "Use" (opens corpse)
        # - Classic controls: right-click usually "Use" (opens corpse)
        default_click = 'left' if loot_method == 'open_drag' else 'right'
        loot_click = get_str(
            context,
            'ng_runtime.loot_click',
            env_var='FENRIL_LOOT_CLICK',
            default=default_click,
            prefer_env=True,
        ).strip().lower()
        if loot_click not in {'left', 'right'}:
            loot_click = default_click
        # Requirement: to open corpses we should left-click.
        # Enforce for open+drag mode so we don't accidentally open context menus.
        if loot_method == 'open_drag':
            loot_click = 'left'

        # Step 1: attempt to open the corpse container.
        # Prefer clicking the corpse tile coordinate when available.
        from src.utils.coordinate import is_valid_coordinate
        current_coord = context.get('ng_radar', {}).get('coordinate')
        cur3: Optional[tuple[int, int, int]] = None
        if is_valid_coordinate(current_coord):
            try:
                cur3 = (int(current_coord[0]), int(current_coord[1]), int(current_coord[2]))
            except Exception:
                cur3 = None

        tgt3: Optional[tuple[int, int, int]] = None
        try:
            if isinstance(self.creature, dict):
                tc = self.creature.get('coordinate')
                if is_valid_coordinate(tc) and tc is not None:
                    tgt3 = (int(tc[0]), int(tc[1]), int(tc[2]))
        except Exception:
            tgt3 = None

        self._open_nearby_corpses(
            context,
            click=loot_click,
            modifier=loot_modifier,
            target_coordinate=tgt3,
            current_coordinate=cur3,
            max_clicks=get_int(
                context,
                'ng_runtime.loot_open_clicks_per_tick',
                env_var='FENRIL_LOOT_OPEN_CLICKS_PER_TICK',
                default=2,
                prefer_env=True,
            ),
        )

        log_loot = get_str(context, 'ng_runtime.log_loot_events', env_var='FENRIL_LOG_LOOT_EVENTS', default='0').strip().lower() in {
            '1',
            'true',
            'yes',
        }

        # Step 2: if we're in free/open-drag mode, try to move items into loot backpack.
        if loot_method == 'open_drag':
            empty_tpl = inv_images.get('slots', {}).get('empty')

            # Take a "before" snapshot so we can find the *new* slot grid that appears when a corpse
            # window opens.
            screenshot_before = context.get('ng_screenshot')
            empties_before: list[tuple[int, int, int, int]] = []
            if screenshot_before is not None and empty_tpl is not None:
                empties_before = locateMultiple(screenshot_before, empty_tpl, confidence=EMPTY_SLOT_CONFIDENCE)

            # Refresh screenshot after interacting (OBS/Websocket capture updates are not necessarily
            # in sync with the task tick).
            time.sleep(0.25)
            screenshot_after = getScreenshot()
            if screenshot_after is not None:
                context['ng_screenshot'] = screenshot_after

            empties_after: list[tuple[int, int, int, int]] = []
            if screenshot_after is not None and empty_tpl is not None:
                empties_after = locateMultiple(screenshot_after, empty_tpl, confidence=EMPTY_SLOT_CONFIDENCE)

            delta_empties = self._subtract_bboxes(empties_after, empties_before, tol=10)
            empties_hint = delta_empties if len(delta_empties) >= 3 else None
            debug_extra = {
                'empties_before': int(len(empties_before)),
                'empties_after': int(len(empties_after)),
                'delta_empties': int(len(delta_empties)),
                'used_delta': bool(empties_hint is not None),
            }

            # CRÍTICO: Si no hay delta de empty slots, significa que NO se abrió ningún corpse.
            # No intentar loot en este caso para evitar clickear en el loot backpack por error.
            if len(delta_empties) < 3:
                log_throttled(
                    'loot.no_corpse_opened',
                    'info',
                    'Loot: no new empty slots detected after corpse clicks (corpse may not have opened)',
                    2.0,
                )
                return context

            max_moves = get_int(
                context,
                'ng_runtime.loot_max_moves_per_tick',
                env_var='FENRIL_LOOT_MAX_MOVES_PER_TICK',
                default=3,
                prefer_env=True,
            )
            if max_moves < 1:
                max_moves = 1
            if max_moves > 10:
                max_moves = 10

            moved_count = 0
            for i in range(max_moves):
                moved = False
                try:
                    moved = self._drag_one_item_from_open_corpse(
                        context,
                        empties_hint=(empties_hint if i == 0 else None),
                        debug_extra=(debug_extra if i == 0 else None),
                    )
                except Exception:
                    moved = False

                if not moved:
                    break

                moved_count += 1

                # After dragging one item, refresh screenshot to reflect inventory changes.
                time.sleep(0.15)
                screenshot_after_move = getScreenshot()
                if screenshot_after_move is not None:
                    context['ng_screenshot'] = screenshot_after_move

            if moved_count > 0:
                self._no_item_ticks = 0
                self._alt_click_attempted = False
                if log_loot:
                    log_throttled(
                        'loot.open_drag.moved',
                        'info',
                        f'Loot open+drag: moved {moved_count} item(s) to loot backpack',
                        0.75,
                    )
                return context

            # No item moved this tick; after a few tries, consider the corpse looted.
            self._no_item_ticks += 1

            # Optional robustness: some setups might require right-click to open.
            # Default OFF because for open+drag we want to enforce left-click.
            try_alt = get_str(context, 'ng_runtime.loot_try_alt_click', env_var='FENRIL_LOOT_TRY_ALT_CLICK', default='0').strip().lower() in {
                '1',
                'true',
                'yes',
            }
            if try_alt and not self._alt_click_attempted and self._no_item_ticks == 1:
                alt = 'right' if loot_click == 'left' else 'left'
                self._alt_click_attempted = True
                self._open_nearby_corpses(context, click=alt, modifier=loot_modifier)
                time.sleep(0.25)
                screenshot_after2 = getScreenshot()
                if screenshot_after2 is not None:
                    context['ng_screenshot'] = screenshot_after2

            if self._no_item_ticks >= 4:
                if log_loot:
                    log_throttled('loot.open_drag.done', 'info', 'Loot open+drag: no more items detected; finishing corpse', 2.0)
                self.terminable = True
            return context

        # Premium/quick mode: keep the old behavior as a one-shot action.
        self.terminable = True
        return context

    def onComplete(self, context: Context) -> Context:
        from src.utils.coordinate import is_valid_coordinate
        # CRÍTICO: Limpiar el corpse actual de la cola primero
        try:
            queue = context.get('loot', {}).get('corpsesToLoot', [])
            if isinstance(queue, list) and self.creature in queue:
                queue.remove(self.creature)
        except Exception:
            pass
        
        # Luego limpiar corpses en 3x3 alrededor del player
        ng_radar = context.get('ng_radar', {})
        if not isinstance(ng_radar, dict):
            return context
        coordinate = ng_radar.get('coordinate')
        if not is_valid_coordinate(coordinate) or coordinate is None:
            return context

        # Type narrowing: coordinate is guaranteed to be indexable here
        try:
            coord_tuple = (int(coordinate[0]), int(coordinate[1]), int(coordinate[2]))
        except (TypeError, IndexError):
            return context

        coordinates = [
            (coord_tuple[0] - 1, coord_tuple[1] - 1, coord_tuple[2]),
            (coord_tuple[0], coord_tuple[1] - 1, coord_tuple[2]),
            (coord_tuple[0] + 1, coord_tuple[1] - 1, coord_tuple[2]),
            (coord_tuple[0] - 1, coord_tuple[1], coord_tuple[2]),
            (coord_tuple[0], coord_tuple[1], coord_tuple[2]),
            (coord_tuple[0] + 1, coord_tuple[1], coord_tuple[2]),
            (coord_tuple[0] - 1, coord_tuple[1] + 1, coord_tuple[2]),
            (coord_tuple[0], coord_tuple[1] + 1, coord_tuple[2]),
            (coord_tuple[0] + 1, coord_tuple[1] + 1, coord_tuple[2]),
        ]

        corpses = context.get('loot', {}).get('corpsesToLoot')
        if not isinstance(corpses, list):
            return context

        new_corpses = []
        for corpse in corpses:
            if not isinstance(corpse, dict):
                continue
            corpse_coord = corpse.get('coordinate')
            if not isinstance(corpse_coord, (list, tuple)) or len(corpse_coord) < 3:
                continue
            try:
                corpse_coord_int = (int(corpse_coord[0]), int(corpse_coord[1]), int(corpse_coord[2]))
            except Exception:
                continue
            if any(coordinatesAreEqual(target, corpse_coord_int) for target in coordinates):
                continue
            new_corpses.append(corpse)

        context['loot']['corpsesToLoot'] = new_corpses

        return context
