#! /usr/bin/env python

# position 1
bx11 = -232
bx12 = 108
by11 = -203
by12 = -285
bz11 = -248
bz12 = 205

# position 2
bx21 = -223
bx22 = 135
by21 = -202
by22 = -279
bz21 = -186
bz22 = 138

# position 3
bx31 = -225
bx32 = 104
by31 = -171
by32 = -244
bz31 = -184
bz32 = 134

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
