#!/usr/bin/python

import sys

content = """
<root>
    <id>lgfrbcsgo.battle-results-server</id>
    <version>{version}</version>
    <name>Battle Results Server</name>
    <description>WoT mod which starts a WebSocket server on `ws://localhost:15455` for serving battle results.</description>
</root>
"""

print(content.format(version=sys.argv[1]))
