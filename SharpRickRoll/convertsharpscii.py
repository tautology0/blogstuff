from PIL import Image, ImageOps, ImageChops, ImageFilter
import imagehash
import sys
import math
import struct
from pathlib import Path
import argparse
from collections import Counter

# skimage stores images as numpy array
import numpy as np
import skimage

def rmsdiff(im1, im2):
	"Calculate the root-mean-square difference between two images"
	diff = ImageChops.difference(im1, im2)
	h = diff.histogram()
	sq = (value*((idx%256)**2) for idx, value in enumerate(h))
	sum_of_squares = sum(sq)
	rms = math.sqrt(sum_of_squares/float(im1.size[0] * im1.size[1]))
	return rms

def convertbw(image, threshold):
	fn = lambda x : 255 if x > threshold else 0
	return image.convert('L').point(fn, mode='1')

def setupcharset(charset):
	# Create an array of sharpscii
	sharpscii=[]
	with open("font.rom", "rb") as infile:

		charrange = [0x00]
		match args.charset:
			case "pixels":
				charrange += range(0xf1, 0xfe)
			case "full":
				charrange += range(0x01, 0xff)
			case "common":
				charrange += range(0x30, 0x40)
				charrange += [0x1e, 0x1f]
				charrange += [0x42, 0x43]
				charrange += range(0x4b, 0x4e)
				charrange += [0x56]
				charrange += range(0x5b, 0x5f)
				charrange += range(0x6c, 0x7f)
				charrange += range(0x9c, 0xa3)
				charrange += range(0xa6, 0xa9)
				charrange += range(0xb0, 0xbb)
				charrange += [0xbd]
				charrange += range(0xd0, 0xda)
				charrange += [0xdd, 0xde, 0xe0, 0xe1, 0xe2, 0xe5, 0xeb, 0xef]
				#charrange += range(0xef, 0xff)

		for x in charrange:
			infile.seek(x*8)
			data=infile.read(8)
			character=Image.frombytes("1",(8,8),data)
			sharpscii.append({"character": character, "code": x})
		
	return sharpscii

# Returns the index of the two most commonly used colours as a list
def getcolours(image):
	colours = [0,0]
	counts=Counter(image.getdata())
	colours[0] = counts.most_common()[0][0]
	if len(counts) > 1:
		colours[1] = counts.most_common()[1][0]
	return colours

parser = argparse.ArgumentParser(
							prog='ConvertSharpSCII',
							description='Tries to convert images to SharpSCII')
parser.add_argument('infile')
parser.add_argument('basename')
parser.add_argument('--threshold', nargs='?', default=75, type=int)
parser.add_argument('--charset', choices=['pixels','full','common'], default="common")
parser.add_argument('--filter', choices=['none', 'blur', 'smooth', 'smoothmore', 'sharpen'], default='none')
parser.add_argument('--savebw', action='store_true', default=False)
parser.add_argument('--invert', action='store_true', default=False)
parser.add_argument('--colour', action='store_true', default=False)
parser.add_argument('--output', action='append', choices=['mzf','image','raw'], default=['image'])
args = parser.parse_args()

basename=Path(args.basename).stem
xsize=320
ysize=200
# load the image
im=Image.open(args.infile)
# Convert to an RGB for the thumbnail
thumb = im.convert("RGB")
thumb.thumbnail((xsize, ysize))

# Make a black and white version for the character comparison
bwthumb = convertbw(thumb, args.threshold)

# Try filtering it, only filter bwthumb or things can get weird
if args.filter != 'none':
	filters={
				 'blur': ImageFilter.BLUR,
				 'smooth': ImageFilter.SMOOTH,
				 'smoothmore': ImageFilter.SMOOTH_MORE,
				 'sharpen': ImageFilter.SHARPEN
				}
	bwthumb.filter(filter=filters[args.filter])

if args.savebw:
	bwthumb.save(f"{basename}-bw.png")
	
if args.invert:
	ImageOps.invert(bwthumb)
	ImageOps.invert(thumb)

sharpscii = setupcharset(args.charset)

# Create an array of the image blocks
blocks=[]
for yoffset in range(0, ysize, 8):
	for xoffset in range(0, xsize, 8):
		blocks.append(bwthumb.crop((xoffset, yoffset, xoffset+8, yoffset+8)))

out=Image.new("RGB",(xsize,ysize))
x = y = 0
palette =   [0,0,0]     + [0,0,255]     + [255,0,0] \
			 + [255,0,255] + [0,255,0]     + [0,255,255] \
			 + [255,255,0] + [255,255,255]

quantised = Image.new("P", (8,8))
quantised.putpalette(palette)

# Array of bytes for screen
outmem=bytearray(4096)

for yoffset in range(0, ysize, 8):
	for xoffset in range(0, xsize, 8):
		bwblock=bwthumb.crop((xoffset, yoffset, xoffset+8, yoffset+8))
		block=thumb.crop((xoffset, yoffset, xoffset+8, yoffset+8))
		
		# work out the most common colours
		# first quantise the image to the Sharp palette
		block=block.quantize(8, palette=quantised, dither=Image.Dither.NONE)
		
		# Get the top most colours
		colours=getcolours(block)
			
		# match black and white
		# closest contains the RMS similarity of the closed sharpscii character
		closest = -1
		# matched is a dictionary of the character image and the display code
		matched = sharpscii[0]
		for char in sharpscii:
			manning = rmsdiff(char["character"], bwblock)
			if manning > closest:
				matched = char.copy()
				closest = manning

		# We've checked all characters, output it
		outputchar = ImageOps.invert(matched["character"])
		# get the "colours" for the bitmap to match the colours tuple to it
		charcolours = getcolours(outputchar)
		colourbyte = 0x07
		if args.colour:
			outputchar=outputchar.convert("P")
			outputchar.putpalette(palette)
			pixdata = outputchar.load()
			# Add colour back
			for y in range(8):
				for x in range(8):
					# match most used colour in the colour block to that in the B&W block
					if pixdata[x, y] == charcolours[0]:
						pixdata[x, y] = colours[0]
					else:
						pixdata[x, y] = colours[1]
			
			colourbyte=(colours[1]<<4) + colours[0]
				
		out.paste(outputchar, (xoffset,yoffset))
		memoffset=int((yoffset / 8)*40 + (xoffset / 8))
		outmem[memoffset] = matched["code"]
		outmem[memoffset+2048] = colourbyte
	
if 'image' in args.output:
	out.save(basename + ".png")

# If we're saving as an mzf, add a simple header
if 'mzf' in args.output:
	header = bytearray(b'')
	header.extend(b'\0')
	header.extend(b'IMAGE           ')
	header.extend(b'\x0d')
	header.extend(struct.pack('H', 4096))
	header.extend(struct.pack('H', 0xD000))
	header.extend(struct.pack('H', 0xD000))
	header.extend(b' ' * 104)
	with open(basename + ".mzf", "wb") as outf:
		outf.write(header)
		outf.write(outmem)

if 'raw' in args.output:
	with open(basename + ".bin","wb") as outf:
		if args.colour:
			outf.write(outmem)
		else:
			outf.write(outmem[:1000])