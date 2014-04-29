wake-my-subnet
==============

A small python tool to Wake On Lan computers on a network segment.
Upon start it pings all the subnet to discover hosts names and MAC addresses.
Then it brings up a standalone web server, which a simple interface which allows
to send a WOL magic packet (UDP port 7) to either:
 - One of the hosts discovered
 - An arbitrary MAC address entered by the user.

**Usage**
 * `./wake-my-subnet -p 8080`
 * Open the browser at http://localhost:8080
 * Enjoy :-)
