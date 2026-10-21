import funcions_aux as faux
import numpy as np
import matplotlib.pyplot as plt

h = 1
pas = 0.01
x = np.arange(-h, h, pas)
y = []
area = 0

for r in x:
  k = faux.kernel(r, h, 1)
  y.append(k)
  area += k * pas

fig, ax = plt.subplots()
ax.plot(x, y, color = "blue")
ax.set(xlabel="Valors de r", ylabel=f"kernel(r) amb h = {h}", title=f"Kernel (Àrea = {area:.2f})")
plt.show()