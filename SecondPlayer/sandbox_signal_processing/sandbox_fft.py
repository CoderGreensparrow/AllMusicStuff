import numpy as np
from matplotlib import pyplot as plt

# https://www.youtube.com/watch?v=arYKpiVACvY

num_t = 48000
xt = np.sin(np.linspace(0, 4*np.pi, num_t)) + \
    np.sin(2 * np.linspace(0, 4*np.pi, num_t)) + \
    np.sin(np.linspace(0, 4*np.pi, num_t)) + \
    np.sin(4 * np.linspace(0, 4*np.pi, num_t))
plt.subplot(2, 2, 1)
plt.plot(xt)
plt.title("x(t)")

fxt = np.fft.fft(xt)
print(fxt.dtype)

# FIRST SUBPLOT
plt.subplot(2, 2, 3)
plt.plot(np.fft.fftshift(np.real(fxt)))  # real part of FFT
plt.title("Real part of FFT of x(t)")
plt.ylabel("Magnitude")
plt.xlabel("Freq index")
# SECOND SUBPLOT
plt.subplot(2, 2, 4)
plt.plot(np.fft.fftshift(np.imag(fxt)))  # real part of FFT
plt.title("Imag part of FFT of x(t)")
plt.ylabel("Magnitude")
plt.xlabel("Freq index")

ixt = np.fft.ifft(fxt)
plt.subplot(2, 2, 2)
plt.plot(np.real(ixt))
plt.plot(np.imag(ixt))
plt.title("IFFT of x(t)")
plt.show()

plt.show()