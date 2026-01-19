# TODO: add typings
# TODO: add unit tests
def matchHpHealing(healing, statusBar):
    if statusBar is None or statusBar.get('hpPercentage') is None:
        return False
    if healing['hpPercentageLessThanOrEqual'] is not None:
        if statusBar['hpPercentage'] > healing['hpPercentageLessThanOrEqual']:
            return False
    if healing['manaPercentageGreaterThanOrEqual'] is not None:
        if statusBar['hpPercentage'] < healing['manaPercentageGreaterThanOrEqual']:
            return False
    return True


# TODO: add typings
# TODO: add unit tests
def matchManaHealing(healing, statusBar):
    if statusBar is None or statusBar.get('manaPercentage') is None:
        return False
    if healing['manaPercentageLessThanOrEqual'] is None:
        return False
    if statusBar['manaPercentage'] > healing['manaPercentageLessThanOrEqual']:
        return False
    return True