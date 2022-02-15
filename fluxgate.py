#! /usr/bin/env python

# position 1
bx11 = -244
bx12 = 90
by11 = -199
by12 = -289
bz11 = -240
bz12 = 205

# position 2
bx21 = -244
bx22 = 124
by21 = -198
by22 = -284
bz21 = -184
bz22 = 148

# position 3
bx31 = -241
bx32 = 92
by31 = -169
by32 = -250
bz31 = -182
bz32 = 145

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
