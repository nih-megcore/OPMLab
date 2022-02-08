#! /usr/bin/env python

# position 1
bx11 = -235
bx12 = 88
by11 = -201
by12 = -282
bz11 = -233
bz12 = 187

# position 2
bx21 = -236
bx22 = 121
by21 = -201
by22 = -278
bz21 = -181
bz22 = 155

# position 3
bx31 = -234
bx32 = 84
by31 = -160
by32 = -233
bz31 = -181
bz32 = 150

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
