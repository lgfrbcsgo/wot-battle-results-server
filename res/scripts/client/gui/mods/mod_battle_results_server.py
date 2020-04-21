from debug_utils import LOG_CURRENT_EXCEPTION


def init(*_, **__):
    try:
        from ModBattleResultsServer import init
        init()
    except:
        LOG_CURRENT_EXCEPTION()


def fini(*_, **__):
    try:
        from ModBattleResultsServer import fini
        fini()
    except:
        LOG_CURRENT_EXCEPTION()
