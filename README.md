# WoT Battle Results Server
WoT mod which starts a WebSocket server on `ws://localhost:61942` for serving battle results.

## Protocol
The sever uses a message protocol which is based on JSON. 
Every command and message is a JSON object which contains a `messageType` and `payload` property.

### Commands
-   Subscribes this client to the feed of battle results.
    ```json
    {
      "messageType": "SUBSCRIBE",
      "payload": {
      }
    }
    ```


-   Replays the battle results of the current gaming session to the client.
    Optionally, a timestamp can be specified by `after` to only replay battle results after the given timestamp. 
    ```json
    {
      "messageType": "REPLAY",
      "payload": {
        "after": 1587657932.152
      }
    }
    ```

-   Unsubscribes the client from the feed of battle results.
    ```json
    {
      "messageType": "UNSUBSCRIBE",
      "payload": {
      }
    }
    ```
    
-   Allows running multiple commands after each other without any interruptions.
    Individual commands are allowed to fail.  
    While the commands are being executed it is guaranteed that
    - no other commands are executed
    - no battle results are received
    ```json
    [
      {
        "messageType": "REPLAY",
        "payload": {
          "after": 1587657932.152
        }
      },
      {
        "messageType": "SUBSCRIBE",
        "payload": {
        }
      }
    ]
    ```
    

### Messages
-   Sent when replaying a battle result or when a new battle result must be pushed to the client.
    `recordedAt` is the timestamp when this battle result was recorded.
    `result` has the same format as the JSON fields found at the start of a .wotreplay file.
    ```json
    {
      "messageType": "BATTLE_RESULT",
      "payload": {
        "recordedAt": 1587657932.152,
        "result": {}
      }
    }
    ```
    
-   Sent when the execution of a command failed.
    ```json
    {
      "messageType": "ERROR",
      "payload": {
        "type": "UNKNOWN_COMMAND",
        "message": "Command UNRECOGNISED_COMMAND is unknown."
      }
    }
    ```
 