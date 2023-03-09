from matplotlib import pyplot as plt
import numpy as np
import matplotlib
matplotlib.use('TkAgg')  # !IMPORTANT
#
#
# x = np.arange(1, 11)
# y = np.arange(1, 11)
# weights = np.arange(1, 11)
# weights[3] = 10
# plt.scatter(x, y, c=weights, cmap='Greys', marker='+')
# plt.colorbar()
# plt.show()
#
#
import matplotlib.pyplot as plt
import numpy as np

# # Fixing random state for reproducibility
# np.random.seed(19680801)
#
# plt.subplot(211)
# plt.imshow(np.random.random((100, 100)))
# plt.subplot(212)
# plt.imshow(np.random.random((100, 100)))
#
# plt.subplots_adjust(bottom=0.1, right=0.8, top=0.9)
# cax = plt.axes([0.85, 0.1, 0.075, 0.8])
# plt.colorbar(cax=cax)
#
# plt.show()

m = np.zeros((1,20))
for i in range(20):
    m[0,i] = (i*5)/100.0
print(m)
plt.imshow(m, cmap='viridis', aspect=2)
plt.yticks(np.arange(0))
plt.xticks(np.arange(0,25,5), [0,25,50,75,100])
plt.show()