#! /usr/bin/env python

# position 1
bx11 = -241
bx12 = 91
by11 = -199
by12 = -277
bz11 = -245
bz12 = 201

# position 2
bx21 = -245
bx22 = 122
by21 = -197
by22 = -275
bz21 = -188
bz22 = 145

# position 3
bx31 = -240
bx32 = 88
by31 = -161
by32 = -234
bz31 = -189
bz32 = 142

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
