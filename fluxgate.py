#! /usr/bin/env python

# position 1
bx11 = -254
bx12 = 94
by11 = -204
by12 = -268
bz11 = -257
bz12 = 222

# position 2
bx21 = -244
bx22 = 115
by21 = -203
by22 = -269
bz21 = -195
bz22 = 165

# position 3
bx31 = -251
bx32 = 93
by31 = -168
by32 = -227
bz31 = -200
bz32 = 159

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
