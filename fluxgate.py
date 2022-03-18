#! /usr/bin/env python

# position 1
bx11 = -234
bx12 = 91
by11 = -194
by12 = -261
bz11 = -242
bz12 = 191

# position 2
bx21 = -245
bx22 = 125
by21 = -193
by22 = -258
bz21 = -189
bz22 = 140

# position 3
bx31 = -232
bx32 = 87
by31 = -162
by32 = -222
bz31 = -189
bz32 = 136

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
