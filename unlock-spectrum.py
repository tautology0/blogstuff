import binascii
import sys
from Crypto.Cipher import DES

key="H3U89XT1"

def mungeit(code):
	out=[]
	temp=[]
	numbers=code.split(" ")
	for i in numbers:
		num=0
		binstr=binascii.unhexlify(i)
		for j in range(0,4):
			num+=ord(binstr[j])<<(j*8)
		temp.append(num)
	
	out.append(format(temp[0],'08x') + format(temp[1],'08x'))
	out.append(format(temp[2],'08x') + format(temp[3],'08x'))
	return out
	
def decryptit(code,key):
	cipher=DES.new(key, DES.MODE_ECB)
	t=cipher.encrypt(binascii.unhexlify(code[0]))
	tx=''.join(chr(ord(a)^ord(b)) for a,b in zip(t, binascii.unhexlify(code[1])))
	t2=cipher.encrypt(tx)
	unlock1=0
	unlock2=0
	for x in range(0,4):
		unlock1+=(ord(t2[x])<<(x*8))
		unlock2+=(ord(t2[x+4])<<(x*8))

	return unlock1 ^ unlock2

code=""
for x in range(1,5):
	code+=sys.argv[x]
	if x != 4:
		code+=" "
texts=mungeit(code)
unlockcode=decryptit(texts, key)
print "Unlock code: " + str(unlockcode)