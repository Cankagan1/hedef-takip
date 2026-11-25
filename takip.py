import numpy as np
import matplotlib.pyplot as plt

np.random.seed(42)
n = 100          # ölçüm sayısı
t = np.arange(n) # zaman adımları

# Gerçek yol: sabit hızlı hedef
true_x = 5 + 2.0 * t
true_y = 10 + 1.0 * t

# Radar ölçümü = gerçek konum + gürültü
noise = 8.0
meas_x = true_x + np.random.normal(0, noise, n)
meas_y = true_y + np.random.normal(0, noise, n)

plt.plot(true_x, true_y, label="Gerçek yol")
plt.scatter(meas_x, meas_y, s=10, c="red", label="Ölçümler")
plt.legend()
plt.axis("equal")
plt.show()