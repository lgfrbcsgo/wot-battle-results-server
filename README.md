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


-   Replays the battle results of the current gaming session to the client.
    `sessionId` can be used to ensure that current session matches the expected one.
    `offset` can be used to specify an offset when not all results have to be replayed.
    An `offset` of `0` or omitting the `offset` will replay all battle results.
    ```json
    {
      "msgType": "REPLAY_BATTLE_RESULTS",
      "sessionId": "88bd6588-b124-4890-83c8-5862ff171795",
      "offset": 2
    }
    ```

-   Replays the battle results of the current gaming session to the client and then subscribes it to the feed.
    `sessionId` can be used to ensure that current session matches the expected one.
    `offset` can be used to specify an offset when not all results have to be replayed.
    An `offset` of `0` or omitting the `offset` will replay all battle results.
    ```json
    {
      "msgType": "REPLAY_AND_SUBSCRIBE_TO_BATTLE_RESULTS",
      "sessionId": "88bd6588-b124-4890-83c8-5862ff171795",
      "offset": 2
    }
    ```

-   Unsubscribes the client from the feed of battle results.
    ```json
    {
      "msgType": "UNSUBSCRIBE_FROM_BATTLE_RESULTS"
    }
    ```
    
-   Starts a new gaming session. Results recorded before this command won't be replayed anymore.
    ```json
    {
      "msgType": "START_NEW_SESSION"
    }
    ```
    

### Messages
-   Sent when replaying a battle result or when a new battle result must be pushed to the client.
    `sessionId` is a unique id of the gaming session which was active when this result was recorded.
    `index` is the index of this `battleResult` within the gaming session which was active when this result was recorded. 
    `battleResult` has the same format as the JSON fields found at the start of a .wotreplay file.
    ```json
    {
      "msgType": "BATTLE_RESULT",
      "sessionId": "88bd6588-b124-4890-83c8-5862ff171795",
      "index": 1,
      "battleResult": {}
    }
    ```
    
-   Sent when the client first connects or when the session changed.
    `sessionId` is the unique id of the current gaming session. The `sessionId` is the same for all connections.
    ```json
    {
      "msgType": "SESSION_ID",
      "sessionId": "88bd6588-b124-4890-83c8-5862ff171795"
    }
    ```
    
-   Sent when a command from the client could not be recognised.
    `commandType` is the original message type.
    ```json
    {
      "msgType": "UNKNOWN_COMMAND",
      "commandType": "UNRECOGNISED_COMMAND"
    }
    ```
    
-   Sent when a command from the client could not be parsed.
    `command` is the original message.
    ```json
    {
      "msgType": "INVALID_COMMAND",
      "command": "{\"msgType\": \"COMMAND\", "
    }
    ```