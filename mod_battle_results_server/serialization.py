from copy import deepcopy
from enum import Enum

from mod_battle_results_server.util import get, unset


def serialize_battle_results(results):
    # source: BattleReplay.__onBattleResultsReceived
    sanitized = sanitize_battle_results(results)
    return encode_obj(sanitized)


def sanitize_battle_results(results):
    results = deepcopy(results)

    vehicles = get(results, "vehicles")
    if vehicles is not None:
        for player_vehicles in vehicles.itervalues():
            for vehicle in player_vehicles:
                unset(vehicle, "damageEventList")

    personal = get(results, "personal")
    if personal is not None:
        for vehicle in personal.itervalues():
            unset(vehicle, "damageEventList")
            unset(vehicle, "xpReplay")
            unset(vehicle, "creditsReplay")
            unset(vehicle, "tmenXPReplay")
            unset(vehicle, "flXPReplay")
            unset(vehicle, "goldReplay")
            unset(vehicle, "crystalReplay")
            unset(vehicle, "eventCoinReplay")
            unset(vehicle, "bpcoinReplay")
            unset(vehicle, "freeXPReplay")
            unset(vehicle, "avatarDamageEventList")

            ext_meta = get(vehicle, "ext", "epicMetaGame")
            if ext_meta is not None:
                unset(ext_meta, "flXPReplay")

    common = get(results, "common")
    if common is not None:
        unset(common, "accountCompDescr")

    return results


def encode_obj(obj):
    if isinstance(obj, dict):
        return encode_dict(obj)
    if isinstance(obj, (list, set, frozenset, tuple)):
        return encode_iterable(obj)
    if isinstance(obj, long):
        return encode_long(obj)
    if isinstance(obj, Enum):
        return encode_enum(obj)
    return obj


def encode_dict(obj):
    return {str(key): encode_obj(value) for key, value in obj.iteritems()}


def encode_iterable(obj):
    return [encode_obj(value) for value in obj]


def encode_long(obj):
    return str(obj)


def encode_enum(obj):
    return obj.value
