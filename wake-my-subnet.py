#!/usr/bin/env python
import datetime
import multiprocessing
import optparse
import re
import socket
import struct
import subprocess
import sys
import time
import wsgiref.simple_server


CONTENT="""
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
Last network scan: $2
</html>
"""


class WMS(object):
  def __init__(self):
    parser = optparse.OptionParser()
    parser.add_option('-p', '--port', help='HTTP Port', default=8965, type='int')
    parser.add_option('-i', '--interface', help='Interface IP addr',
                      default=socket.gethostbyname(socket.gethostname()))
    (options, _) = parser.parse_args()

    print 'Using interface', options.interface
    self._subnet = options.interface.split('.')[0:3]
    self._bacast_addr = '.'.join(self._subnet + ['255'])
    self._known_hosts = {}
    self._last_scan = ''

    self._RescanNetwork()

    print 'Starting HTTP server at port %d' % options.port
    httpd = wsgiref.simple_server.make_server(
        '', options.port, self._HttpHandler)
    httpd.serve_forever()

  def _HttpHandler(self, environ, start_response):
    path = environ['PATH_INFO']
    method = environ['REQUEST_METHOD']
    start_response('200 OK', [('Content-Type', 'text/html'),
                              ('Cache-Control', 'no-cache'),
                              ('Expires', 'Fri, 19 Sep 1986 05:00:00 GMT')])
    if method == 'POST':
      req_body_size = int(environ.get('CONTENT_LENGTH', 0))
      req_body = environ['wsgi.input'].read(req_body_size)
      if req_body.startswith('t='):
        target = req_body[2:]
        mac = self._known_hosts.get(target, target)
        SendWOLPacket(mac, self._bacast_addr)
        return ['Sending WOL packet to %s' % mac]
    else:
      hosts_datalist = ''
      for host, mac in self._known_hosts.iteritems():
        hosts_datalist += '<option value="%s">%s</option>' % (host, mac)
      html = str(CONTENT.replace('$1', hosts_datalist))
      html = str(html.replace('$2', str(self._last_scan)))
      return [html]

  def _RescanNetwork(self):
    print 'Scanning subnet'
    subnet_addrs = ['.'.join(self._subnet + [str(i)]) for i in xrange(1, 255)]
    pool = multiprocessing.Pool(processes=20)
    pinged_addrs_count = 0
    for (host_or_ip, mac_addr) in pool.imap_unordered(LookupHost, subnet_addrs):
      pinged_addrs_count += 1
      print '  Ping: %d/%d   \r' % (pinged_addrs_count, len(subnet_addrs)),
      if mac_addr:
        self._known_hosts[host_or_ip] = mac_addr
    print '\rDiscovered %d hosts' % len(self._known_hosts)
    self._last_scan = datetime.datetime.now()

def LookupHost(target_ip):
  p = subprocess.Popen(['arping', '-f', '-w1', target_ip],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  output, _ = p.communicate()
  match = re.search('reply.*\[([\w:]+)\]', output)
  if not match:
    return (target_ip, None)
  mac = match.group(1)
  try:
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
      payload = ''.join([payload,
                         struct.pack('B', int(magic[i: i + 2], 16))])
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  sock.sendto(payload, (bcast_addr, 7))


if __name__ == '__main__':
  WMS()
