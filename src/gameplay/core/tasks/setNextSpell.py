from ...typings import Context
from .common.base import BaseTask
from src.repositories.actionBar.core import hasCooldownByName
from src.utils.array import getNextArrayIndex
from time import time
from src.utils.core import getScreenshot, getScreenshotDebugInfo, setScreenshotOutputIdx

class SetNextSpellTask(BaseTask):
    def __init__(self: "SetNextSpellTask", spell: str) -> None:
        super().__init__()
        self.name = 'setNextSpell'
        self.spell = spell

    # TODO: add unit tests
    def do(self, context: Context) -> Context:
        # Refresh screenshot from the capture window (OBS projector) region.
        try:
            out_idx = context.get('ng_capture_output_idx')
            if out_idx is not None and getScreenshotDebugInfo().get('output_idx') != out_idx:
                setScreenshotOutputIdx(int(out_idx))
        except Exception:
            pass
        curScreen = getScreenshot(
            region=context.get('ng_capture_region'),
            absolute_region=context.get('ng_capture_absolute_region'),
        )
        context['ng_screenshot'] = curScreen
        if curScreen is None:
            return context
        hasCooldown = hasCooldownByName(curScreen, self.spell)
        if hasCooldown:
            comboSpell = context['ng_comboSpells']['items'][0]
            if comboSpell['enabled'] == False:
                return context
            nextIndex = getNextArrayIndex(
                comboSpell['spells'], comboSpell['currentSpellIndex'])
            # TODO: improve indexes without using context
            context['ng_comboSpells']['items'][0]['currentSpellIndex'] = nextIndex
            context['ng_comboSpells']['lastUsedSpell'] = self.spell
            context['ng_lastUsedSpellLoot'] = self.spell
            context['ng_comboSpells']['lastUsedSpellAt'] = time()
            context['healCount'] = 0

        return context
