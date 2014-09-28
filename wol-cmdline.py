#!/usr/bin/env python
import re
import socket
import struct
import sys


def send_wol_packet(mac, bcast_addr='<broadcast>'):
    mac = re.sub(r'[^\w]', '', mac)
    assert(len(mac) == 12), 'Expecting 6-octects hex MAC addr'
    magic = 'FFFFFFFFFFFF' + (mac * 20)
    payload = ''
    for i in range(0, len(magic), 2):
        payload = ''.join(
            [payload, struct.pack('B', int(magic[i: i + 2], 16))])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(payload, (bcast_addr, 7))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage %s MAC:ADDR' % sys.argv[0]
        sys.exit(1)
    send_wol_packet(sys.argv[1])
