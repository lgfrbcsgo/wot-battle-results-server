from debug_utils import LOG_CURRENT_EXCEPTION


def init():
    try:
        from mod_battle_results_server import g_battle_results_server

        g_battle_results_server.serve()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def fini():
    try:
        from mod_battle_results_server import g_battle_results_server

        g_battle_results_server.close()
    except Exception:
        LOG_CURRENT_EXCEPTION()
