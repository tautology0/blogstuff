#!/usr/bin/env python3

import os
import sys
import struct

infile=sys.argv[1]
outfile=sys.argv[2]

stats=os.stat(infile)

# build header
header=bytearray(b'')
header.extend(b'\0')
header.extend(b'MYSTERY         ')
header.extend(b'\x0d')
header.extend(struct.pack('H', stats.st_size))
header.extend(struct.pack('H', 0x2000))
header.extend(struct.pack('H', 0x2000))
header.extend(b' ' * 104)

with open(infile,"rb") as fh:
   data=fh.read()

with open(outfile,"wb") as fh:
   fh.write(header)
   fh.write(data)
   
