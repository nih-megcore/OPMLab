#! /usr/bin/env python

# position 1
bx11 = -244
bx12 = 94
by11 = -206
by12 = -277
bz11 = -243
bz12 = 209

# position 2
bx21 = -243
bx22 = 127
by21 = -204
by22 = -270
bz21 = -213
bz22 = 191

# position 3
bx31 = -239
bx32 = 94
by31 = -168
by32 = -224
bz31 = -213
bz32 = 187

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
