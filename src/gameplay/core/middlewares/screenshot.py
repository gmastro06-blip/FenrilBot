from src.utils.core import getScreenshot
from src.gameplay.typings import Context


# TODO: add unit tests
def setScreenshotMiddleware(context: Context) -> Context:
    region = None
    window = context.get('window')
    if window is not None:
        try:
            left = int(window.left)
            top = int(window.top)
            right = left + int(window.width)
            bottom = top + int(window.height)
            region = (left, top, right, bottom)
        except Exception:
            region = None
    context['ng_screenshot'] = getScreenshot(region=region)
    if context.get('ng_debug') is not None and context['ng_screenshot'] is None:
        context['ng_debug']['last_tick_reason'] = 'no screenshot'
    return context
