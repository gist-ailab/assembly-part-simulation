# Note: if you use python3, python >= 3.7 is required.

import socket
import struct
import pickle
import numpy as np
import pickle_compat

from .timeout import timeout


def recvall(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf: return None
        buf += newbuf
        count -= len(newbuf)
    return buf

def recvall_pickle(sock):
    pickle_compat.patch()
    packed_length = recvall(sock, 8) 
    length = struct.unpack("L", packed_length)[0]
    string_data = recvall(sock, int(length))
    try:
        # send python3 -> receive python 2
        data = pickle.loads(string_data)
    except TypeError:
        # send python2 -> receive python 3
        data = pickle.loads(string_data, encoding="bytes")
    pickle_compat.unpatch()
    return data

def sendall_pickle(sock, data):
    data = pickle.dumps(data, protocol=2)
    sock.send(struct.pack("L", len(data)))
    sock.send(data)
