# WoT Battle Results Server
WoT mod which starts a WebSocket server on `ws://localhost:15455` for serving battle results.

The server has a peer dependency on [WoT Websocket Server](https://github.com/lgfrbcsgo/wot-websocket-server),
[WoT Async Server](https://github.com/lgfrbcsgo/wot-async-server), 
[WoT Async](https://github.com/lgfrbcsgo/wot-async), and [WoT Hooking](https://github.com/lgfrbcsgo/wot-hooking).


## Demo Apps
[Live WN8](https://lgfrbcsgo.github.io/wot-live-wn8/) ([Source](https://github.com/lgfrbcsgo/wot-live-wn8))

[Live Win Rate](https://lgfrbcsgo.github.io/wot-live-win-rate/) ([Source](https://github.com/lgfrbcsgo/wot-live-win-rate))

## Origin Whitelisting
Origins need to be whitelisted to protect against malicious websites.
All `localhost` origins are white listed for local testing.
 
Please open an issue if you want to deploy your app and need your origin to be included in the whitelist.


## Protocol
The server uses a protocol which is based on [JSON-RPC 2.0](https://www.jsonrpc.org/specification).

**Guarantees:**
- Responses will be sent in the order in which the requests were sent.
- Requests are processed atomically. This is also true for batch requests. 
  I.e. while your request is being processed, no other request from any client is handled.
  Also, no notifications will be sent.
- The individual responses of a batch response will have the same order as the individual requests of 
  the corresponding batch request.
- Notifications are not sent in batches.

### `subscribe`
Subscribes this client to the feed of battle results.

**Request**
```json
{
  "jsonrpc": "2.0",
  "method": "subscribe",
  "id": 42
}
```
**Response**
```json
{
  "jsonrpc": "2.0",
  "result": null,
  "id": 42
}
```

### `unsubscribe`
Unsubscribes this client from the feed of battle results.

**Request**
```json
{
  "jsonrpc": "2.0",
  "method": "unsubscribe",
  "id": 42
}
```
**Response**
```json
{
  "jsonrpc": "2.0",
  "result": null,
  "id": 42
}
```

### `get_battle_results`
Sends all recorded battle results of the current gaming session to the client.

**Params**
 - `after`: optional timestamp to only replay battle results after the given timestamp. Can be omitted.

**Request**
```json
{
  "jsonrpc": "2.0",
  "method": "get_battle_results",
  "params": {
    "after": 1587657932
  },
  "id": 42
}
```

**Response**
```json5
{
  "jsonrpc": "2.0",
  "result": {
    "start": 1587657932,
    "end": 1587659370,
    "battleResults": [ /* ... */ ]
  },
  "id": 42
}
```

### `subscription` notification
Sent **from the server** when a new battle result has been received. 
```json5
{
  "jsonrpc": "2.0",
  "method": "subscription",
  "params": {
    "timestamp": 1587657932,
    "battleResult": { /* ... */ }
  }
}
```    
