# Note: if you use python3, python >= 3.7 is required.

import socket
import struct
import pickle
import cv2
import numpy as np
import pickle_compat


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

def recvall_image(sock):
    length = recvall(sock, 16) 
    string_data = recvall(sock, int(length))
    data = np.fromstring(string_data, dtype='uint8')
    return cv2.imdecode(data, 1)

def sendall_image(sock, image):
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
    result, imgencode = cv2.imencode('.jpg', image, encode_param)
    data = np.array(imgencode)
    string_data = data.tostring()
    sock.send(str(len(string_data)).ljust(16))
    sock.send(string_data)
