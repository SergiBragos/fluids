import funcions_aux as faux
import numpy as np
import matplotlib.pyplot as plt

h = 0.3
x = np.arange(-h, h, 0.01)
y = []
area = 0

for r in x:
  k = faux.kernel(r, h, 1)
  y.append(k)
  area += k

fig, ax = plt.subplots()
ax.plot(x, y, color = "blue")
ax.set(xlabel="Valors de r", ylabel="kernel(r) amb h = 1", title=f"Kernel (Àrea = {area:.2f})")
plt.show()