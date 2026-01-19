from src.gameplay.healing.observers import healingByPotions as healing_module


def _base_context():
    return {
        "ng_statusBar": {
            "hpPercentage": None,
            "manaPercentage": None,
            "mana": None,
        },
        "healing": {
            "potions": {
                "firstHealthPotion": {
                    "enabled": True,
                    "hotkey": "F1",
                    "slot": 1,
                    "hpPercentageLessThanOrEqual": 30,
                    "manaPercentageGreaterThanOrEqual": 0,
                },
                "firstManaPotion": {
                    "enabled": False,
                    "hotkey": "F2",
                    "slot": 2,
                    "manaPercentageLessThanOrEqual": 80,
                },
            }
        },
    }


def test_healing_by_potions_hp_none_no_crash():
    healing_module.tasksOrchestrator.reset()
    context = _base_context()
    healing_module.healingByPotions(context)
    assert healing_module.tasksOrchestrator.rootTask is None


def test_healing_by_potions_hp_string_triggers():
    healing_module.tasksOrchestrator.reset()
    context = _base_context()
    context["ng_statusBar"]["hpPercentage"] = "25"
    healing_module.healingByPotions(context)
    assert healing_module.tasksOrchestrator.rootTask is not None


def test_healing_by_potions_invalid_string_no_crash():
    healing_module.tasksOrchestrator.reset()
    context = _base_context()
    context["ng_statusBar"]["hpPercentage"] = "abc"
    healing_module.healingByPotions(context)
    assert healing_module.tasksOrchestrator.rootTask is None
