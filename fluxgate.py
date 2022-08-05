#! /usr/bin/env python

# position 1
bx11 = -219
bx12 = 104
by11 = -234
by12 = -275
bz11 = -248
bz12 = 213

# position 2
bx21 = -202
bx22 = 124
by21 = -234
by22 = -270
bz21 = -184
bz22 = 142

# position 3
bx31 = -217
bx32 = 102
by31 = -200
by32 = -230
bz31 = -181
bz32 = 136

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
