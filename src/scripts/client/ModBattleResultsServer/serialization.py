from copy import deepcopy

from ModBattleResultsServer.util import unset, get


def serialize_battle_results(results):
    # source: BattleReplay.__onBattleResultsReceived
    sanitized = sanitize_battle_results(results)
    return encode_obj(sanitized)


def sanitize_battle_results(results):
    results = deepcopy(results)

    vehicles = get(results, 'vehicles')
    if vehicles is not None:
        for player_vehicles in vehicles.itervalues():
            for vehicle in player_vehicles:
                unset(vehicle, 'damageEventList')

    personal = get(results, 'personal')
    if personal is not None:
        for player in personal.itervalues():
            unset(player, 'damageEventList')
            unset(player, 'xpReplay')
            unset(player, 'creditsReplay')
            unset(player, 'tmenXPReplay')
            unset(player, 'goldReplay')
            unset(player, 'crystalReplay')
            unset(player, 'freeXPReplay')
            unset(player, 'avatarDamageEventList')

            ext_meta = get(player, 'ext', 'epicMetaGame')
            if ext_meta is not None:
                unset(ext_meta, 'flXPReplay')

    common = get(results, 'common')
    if common is not None:
        unset(common, 'accountCompDescr')

    return results


def encode_obj(obj):
    if isinstance(obj, dict):
        return encode_dict(obj)
    if isinstance(obj, (list, set, frozenset, tuple)):
        return encode_iterable(obj)
    return obj


def encode_dict(obj):
    return {str(key): encode_obj(value) for key, value in obj.iteritems()}


def encode_iterable(obj):
    return [encode_obj(value) for value in obj]
