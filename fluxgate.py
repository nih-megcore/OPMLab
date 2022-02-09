#! /usr/bin/env python

# position 1
bx11 = -237
bx12 = 90
by11 = -208
by12 = -292
bz11 = -238
bz12 = 190

# position 2
bx21 = -235
bx22 = 121
by21 = -207
by22 = -287
bz21 = -174
bz22 = 155

# position 3
bx31 = -233
bx32 = 88
by31 = -160
by32 = -237
bz31 = -178
bz32 = 151

print((bx21 + bx31) / 2,
(by21 + by31) / 2,
(bz11 + bz21) / 2,
-(bx22 + bx32) / 2,
(by22 + by32) / 2,
-(bz12 + bz22) / 2)
