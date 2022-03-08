#! /usr/bin/env python

# position 1
bx11 = -236
bx12 = 89
by11 = -203
by12 = -296
bz11 = -234
bz12 = 203

# position 2
bx21 = -229
bx22 = 118
by21 = -201
by22 = -288
bz21 = -180
bz22 = 144

# position 3
bx31 = -233
bx32 = 87
by31 = -162
by32 = -245
bz31 = -176
bz32 = 138

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
