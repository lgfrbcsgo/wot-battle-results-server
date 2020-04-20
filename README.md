# WoT Battle Results Server
WoT mod which starts a WebSocket server on `localhost:61942` which publishes the current battle results.
When a client connects, the server will replay all previous battle results of the current session in order.
The battle results have the same format as those found at the beginning of a WoT replay file.
A message will ever only contain a single battle result.