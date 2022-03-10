#! /usr/bin/env python

# position 1
bx11 = -242
bx12 = 104
by11 = -200
by12 = -277
bz11 = -248
bz12 = 217

# position 2
bx21 = -235
bx22 = 134
by21 = -199
by22 = -276
bz21 = -196
bz22 = 157

# position 3
bx31 = -236
bx32 = 102
by31 = -165
by32 = -234
bz31 = -193
bz32 = 152

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
