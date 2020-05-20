from debug_utils import LOG_CURRENT_EXCEPTION


def init(*_, **__):
    try:
        from mod_battle_results_server import init

        init()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def fini(*_, **__):
    try:
        from mod_battle_results_server import fini

        fini()
    except Exception:
        LOG_CURRENT_EXCEPTION()
