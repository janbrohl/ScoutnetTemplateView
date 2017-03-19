from collections import OrderedDict
import os
import requests


SN_RPC_URL = "https://www.scoutnet.de/jsonrpc/server.php"


class RPCError(Exception):
    pass


def rpc(url, method, *params):
    """
    JSON-RPC 1.0 über HTTP(S) POST
    """
    call_id = os.urandom(16).hex()
    json_data = {
        "method": method,
        "params": params,
        "id": call_id
    }
    got = requests.post(
        url,
        json=json_data
    ).json(object_pairs_hook=OrderedDict)
    e = got["error"]
    if e is not None:
        raise RPCError(e)
    return got["result"]


def get_data_by_global_id(global_id, query={}):
    return rpc(
        SN_RPC_URL,
        "get_data_by_global_id",
        global_id,
        query
    )
