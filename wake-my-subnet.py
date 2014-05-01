#!/usr/bin/env python
import datetime
import optparse
import os
import re
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib
import wsgiref.simple_server


BG_RESCAN_INTERVAL_SECS = 60 * 60 * 30  # Rescan network every 30 mins.

CONTENT = """
<!doctype html>
<html>
<head>
  <title>Wake My Subnet</title>
  <style type="text/css">
    html {font-family: sans-serif; 1.25em; }
    form {margin: 2em auto; text-align: center; border: 1px solid gray; }
    form > * { margin: 1em; }
  </style>
</head>
<body>
  <form method="POST">
    <h1>
      <a href="https://github.com/primiano/wake-my-subnet">Wake My Subnet</a>
    </h1>
    <label for="t">MAC or cached hostname:</label>
    <input type="text" name="t" list="hosts">
    <datalist id="hosts">
      <select>$1</select>
    </datalist>
    <input type="submit" value="WOL">
    </form>
</body>
Network scan status: $2
<pre>
How to setup your machine for WOL
 1. Enable wake on lan in the BIOS.
 2. Add "ethtool -s eth0 wol g" to your rc.local
</pre>
</html>
"""


class WMS(object):
  def __init__(self):
    parser = optparse.OptionParser()
    parser.add_option('-d', '--daemon', help='Daemonize', action='store_true')
    parser.add_option('-p', '--port', help='HTTP Port', default=8965,
                      type='int')
    parser.add_option('-i', '--interface', help='Interface IP addr',
                      default=socket.gethostbyname(socket.gethostname()))
    (options, _) = parser.parse_args()

    print 'Using interface', options.interface
    self._subnet = options.interface.split('.')[0:3]
    self._bacast_addr = '.'.join(self._subnet + ['255'])
    self._known_hosts = {}
    self._scan_status = 'Not started'

    print 'Serving on http://localhost:%d/' % options.port

    if options.daemon:
      print 'Forking into daemon land.'
      Daemonize()

    self._rescan_thread = threading.Thread(target=self._RescanThread)
    self._rescan_thread.daemon = True
    self._rescan_thread.start()

    httpd = wsgiref.simple_server.make_server(
        '', options.port, self._HttpHandler)
    httpd.serve_forever()


  def _HttpHandler(self, environ, start_response):
    # path = environ['PATH_INFO']
    method = environ['REQUEST_METHOD']
    start_response('200 OK', [('Content-Type', 'text/html'),
                              ('Cache-Control', 'no-cache'),
                              ('Expires', 'Fri, 19 Sep 1986 05:00:00 GMT')])
    if method == 'POST':
      req_body_size = int(environ.get('CONTENT_LENGTH', 0))
      req_body = environ['wsgi.input'].read(req_body_size)
      if req_body.startswith('t='):
        target = urllib.unquote(req_body[2:])
        mac = self._known_hosts.get(target, target)
        try:
          SendWOLPacket(mac, self._bacast_addr)
          return ['Sending WOL packet to %s' % mac]
        except:
          return ['Error while waking "%s": %s' % (mac, sys.exc_info())]
          raise

    else:
      hosts_datalist = ''
      for host, mac in self._known_hosts.iteritems():
        hosts_datalist += '<option value="%s">%s</option>' % (host, mac)
      html = str(CONTENT.replace('$1', hosts_datalist))
      html = str(html.replace('$2', str(self._scan_status)))
      return [html]


  def _RescanNetwork(self):
    print 'Scanning subnet'
    subnet_addrs = ['.'.join(self._subnet + [str(i)]) for i in xrange(1, 255)]
    pinged_addrs_count = 0
    for target_ip in subnet_addrs:
      host_or_ip, mac_addr = Lookup(target_ip)
      pinged_addrs_count += 1
      ping_stat = 'Ping: %d/%d' % (pinged_addrs_count, len(subnet_addrs))
      self._scan_status = ping_stat
      print ping_stat, '  \r',
      if mac_addr:
        self._known_hosts[host_or_ip] = mac_addr
    print '\rDiscovered %d hosts' % len(self._known_hosts)
    self._scan_status = datetime.datetime.now()


  def _RescanThread(self):
    while(True):
      self._RescanNetwork()
      time.sleep(BG_RESCAN_INTERVAL_SECS)


def Lookup(target_ip):
  p = subprocess.Popen(['arping', '-f', '-w1', target_ip],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  time.sleep(1)
  if p.poll() is None:
    p.kill()
    os.wait()
    return (target_ip, None)
  output, _ = p.communicate()
  match = re.search('reply.*\[([\w:]+)\]', output)
  if not match:
    return (target_ip, None)
  mac = match.group(1)
  try:
    socket.setdefaulttimeout(1)
    host_info = socket.gethostbyaddr(target_ip)
  except socket.herror:
    host_info = None
  host_or_ip = host_info[0] if host_info else target_ip
  return (host_or_ip, mac)


def SendWOLPacket(mac, bcast_addr='<broadcast>'):
  mac = re.sub('[^\w]', '', mac)
  assert(len(mac) == 12), 'Expecting 6-octects hex MAC addr'
  magic = 'FFFFFFFFFFFF' + (mac * 20)
  payload = ''
  for i in range(0, len(magic), 2):
    payload = ''.join(
        [payload, struct.pack('B', int(magic[i: i + 2], 16))])
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  sock.sendto(payload, (bcast_addr, 7))

def Daemonize():
  pid = os.fork()
  if pid > 0:
    sys.exit(0)  # exit first parent

  os.setsid()
  os.umask(0)

  pid = os.fork()
  if pid > 0:
    sys.exit(0)  # exit second parent

  sys.stdout.flush()
  sys.stderr.flush()
  null_in = file('/dev/null', 'r')
  null_out = file('/dev/null', 'a+')
  os.dup2(null_in.fileno(), sys.stdin.fileno())
  os.dup2(null_out.fileno(), sys.stdout.fileno())
  os.dup2(null_out.fileno(), sys.stderr.fileno())


if __name__ == '__main__':
  WMS()
