# WoT Battle Results Server
WoT mod which starts a WebSocket server on `ws://localhost:61942` for serving battle results.

## Protocol
The sever uses a message protocol which is based on JSON. 
Every command and message is a JSON object which contains at least a `msgType` property.

### Commands
-   Subscribes this client to the feed of battle results.
    ```json
    {
      "msgType": "SUBSCRIBE_TO_BATTLE_RESULTS"
    }
    ```


-   Replays the battle results of the current session to the client.
    `offset` can be used specify an offset when not all results have to be replayed.
    An `offset` of `0` or omitting the `offset` will replay all battle results.
    ```json
    {
      "msgType": "REPLAY_BATTLE_RESULTS",
      "offset": 2
    }
    ```

-   Replays the battle results of the current session to the client and then subscribes it to the feed.
    `offset` can be used specify an offset when not all results have to be replayed.
    An `offset` of `0` or omitting the `offset` will replay all battle results.
    ```json
    {
      "msgType": "REPLAY_AND_SUBSCRIBE_TO_BATTLE_RESULTS",
      "offset": 2
    }
    ```

-   Unsubscribes the client from the feed of battle results.
    ```json
    {
      "msgType": "UNSUBSCRIBE_FROM_BATTLE_RESULTS"
    }
    ```

### Messages
-   Sent when replaying a battle result or when a new battle result must be pushed to the client.
    `battleResult` has the same format as the JSON fields found at the start of a .wotreplay file.
    ```json
    {
      "msgType": "BATTLE_RESULT",
      "battleResult": {}
    }
    ```
    
-   Sent when a command from the client could not be recognised.
    `commandType` is the original message type.
    `payload` will contain all additional fields of the original message.
    ```json
    {
      "msgType": "UNKNOWN_COMMAND",
      "commandType": "UNRECOGNISED_COMMAND",
      "payload": {}
    }
    ```