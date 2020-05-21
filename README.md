# WoT Battle Results Server
WoT mod which starts a WebSocket server on `ws://localhost:15455` for serving battle results.

The server has a peer dependency on [WoT Websocket Server](https://github.com/lgfrbcsgo/wot-websocket-server),
[WoT Async Server](https://github.com/lgfrbcsgo/wot-async-server), and
[WoT Async](https://github.com/lgfrbcsgo/wot-async).


## Demo Apps
[Live WN8](https://lgfrbcsgo.github.io/wot-live-wn8/) ([Source](https://github.com/lgfrbcsgo/wot-live-wn8))

[Live Win Rate](https://lgfrbcsgo.github.io/wot-live-win-rate/) ([Source](https://github.com/lgfrbcsgo/wot-live-win-rate))

## Origin Whitelisting
Origins need to be whitelisted to protect against malicious websites.
All `localhost` origins are white listed for local testing.
 
Please open an issue if you want to deploy your app and need your origin to be included in the whitelist.


## Protocol
The server uses a message protocol which is based on JSON. 
Every command and message is a JSON object which contains a `messageType` and `payload` property.
(`payload` must be an object.)

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
    > `after`: optional timestamp to only replay battle results after the given timestamp. Can be omitted.
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
    

### Messages
-   Sent when replaying a battle result or when a new battle result must be pushed to the client.  
    > `recordedAt`: timestamp when this battle result was recorded.
                                                                                                     
    > `result`: battle result in the same format as the JSON found at the start of a `.wotreplay` file.
    ```json5
    {
      "messageType": "BATTLE_RESULT",
      "payload": {
        "recordedAt": 1587657932.152,
        "result": {
          "arenaUniqueID": "104502528107595980",
          "personal": {
            // ...
          },
          "vehicles": {
            // ...
          },
          "avatars": {
            // ...
          },
          "players": {
            // ...
          },
          "common": {
            // ...
          }
        }
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
 
