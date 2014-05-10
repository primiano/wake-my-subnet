wake-my-subnet
==============

**Wake My Subnet** is a small Linux daemon which allows to remotely wake hosts on a network using the WOL magic packet.
It provides a web-based UI and is able to lookup hosts on the network segment automatically.

<img align="left" src="https://cloud.githubusercontent.com/assets/7137473/2936328/26c2e342-d856-11e3-9ae1-8794ef8ac90e.png" alt="logo">
The daemon should be executed on a machine (which is always on) which is connected to the same network segment of the other hosts that will be woken up.
The daemon periodically scans the network to discover the hosts (when they are up) and exposes a web interface to wake them up when they are not.
The WOL method used is the [UDP Magic Packet](http://en.wikipedia.org/wiki/Wake-on-LAN#Magic_packet) on port 7.


**Usage**

On the wake-station (the machine that will be always on and will be used to wake the others):

 * `sudo -u nobody ./wake-my-subnet -p 8080`
 * Open the browser at http://host-running-the-darmon:8080/
 * Profit :-)


On the other machines which will turned off regularly:

  * Enable WOL in the BIOS.
  * Add "ethtool -s eth0 wol g" to the rc.local.

**Sreenshot**
![screenshot](https://cloud.githubusercontent.com/assets/7137473/2936376/715a2e54-d858-11e3-8099-9602cfeedc33.jpg)
