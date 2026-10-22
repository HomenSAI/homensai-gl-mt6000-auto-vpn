import struct
import unittest
from unittest.mock import patch
import mt3000_namespace_probe as P

class Tests(unittest.TestCase):
    def test_trace_needs_single_public_ipv4_and_http_marker(self):
        self.assertEqual(P.trace_address(b'ip=9.9.9.9\nhttp=http/1.1\n'),'9.9.9.9')
        for body in (b'ip=192.168.11.250\nhttp=h',b'ip=9.9.9.9',b'ip=9.9.9.9\nip=1.1.1.1\nhttp=h',b'ip=::1\nhttp=h',b'\xff'):
            with self.assertRaises((ValueError,UnicodeError)):P.trace_address(body)
    def test_dns_requires_actual_a_and_exact_echo(self):
        q=b'\x07example\x03com\0'+struct.pack('!HH',1,1);token=b'xy'
        raw=struct.pack('!2sHHHHH',token,0x8180,1,1,0,0)+q+b'\xc0\x0c'+struct.pack('!HHIH',1,1,60,4)+b'\x09'*4
        self.assertTrue(P.valid_dns(raw,token,q))
        for bad in (raw[:-1],raw[:12],b'zz'+raw[2:],raw[:2]+b'\x83'+raw[3:]):self.assertFalse(P.valid_dns(bad,token,q))
    def test_request_cannot_be_root_namespace_or_foreign_interface(self):
        args=dict(nonce='0123456789ab',namespace_inode=12,root_namespace_inode=12,interface='hvn0123456789',source='192.168.11.250',gateway='192.168.11.1',peer_mac='fe:fe:ff:67:89:ab')
        with patch.object(P.subprocess,'check_output') as commands:
            with self.assertRaises(ValueError):P.topology(args)
            commands.assert_not_called()
    def test_empty_request_is_unconfirmed_never_certificate(self):
        value=P.measure({})
        self.assertFalse(value['performed']);self.assertFalse(value['external_lan_verified']);self.assertFalse(value['native_certificate'])

if __name__=='__main__':unittest.main()
