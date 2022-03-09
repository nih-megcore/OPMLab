import numpy as np
import matplotlib.pyplot as plt

x = y = np.linspace(0, 4, 40, endpoint = True)
X, Y = np.meshgrid(x, y)
Z1 = np.exp(-X**2 - Y**2)
Z2 = np.exp(-(X - 3)**2 - (Y - 3)**2)
Z = (Z1 - Z2) * 2

#fig1, ax2 = plt.subplots(constrained_layout=True)
fig1, ax2 = plt.subplots()

#CS = ax2.contourf(X, Y, Z, 10, cmap=plt.cm.jet)
CS = ax2.contourf(X, Y, Z, 10, cmap=plt.cm.coolwarm)

# Note that in the following, we explicitly pass in a subset of the contour
# levels used for the filled contours.  Alternatively, we could pass in
# additional levels to provide extra resolution, or leave out the *levels*
# keyword argument to use all of the original levels.

CS2 = ax2.contour(CS, levels=CS.levels[::2], colors='r')

ax2.set_title('Title')
ax2.set_xlabel('')
ax2.set_ylabel('')

plt.tick_params('x', top=True)
plt.tick_params('x', labelbottom=False)
plt.tick_params('y', right=True)
plt.tick_params('y', labelleft=False)

ax2.xaxis.set(ticks = [0, 1, 2, 3, 4])
ax2.yaxis.set(ticks = [0, 1, 2, 3, 4])
ax2.grid(c='k', ls='-', alpha=0.3)

ax2.set_aspect(15/13)
fig1.set_size_inches(5 * 15/13, 5 * 15/13)

# Make a colorbar for the ContourSet returned by the contourf call.
cbar = fig1.colorbar(CS)
cbar.ax.set_ylabel('pT')

ax = cbar.ax
pos = ax.get_position()
pos.p0 += (0, .03)          # adjust margins
pos.p1 += (0, -.03)
pos = ax.set_position(pos)

# Add the contour line levels to the colorbar
cbar.add_lines(CS2)

plt.show()
