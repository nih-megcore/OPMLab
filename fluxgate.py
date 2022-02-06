#! /usr/bin/env python

# position 1
bx11 = -234
bx12 = 97
by11 = -201
by12 = -287
bz11 = -225
bz12 = 177

# position 2
bx21 = -226
bx22 = 126
by21 = -203
by22 = -285
bz21 = -174
bz22 = 157

# position 3
bx31 = -234
bx32 = 95
by31 = -162
by32 = -236
bz31 = -177
bz32 = 154

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
