# numpy implementation of https://github.com/omarestrella/simplify.py
# It uses a combination of Douglas-Peucker and Radial Distance algorithms

import numpy as np
import numpy as np
from math import factorial

def savitzky_golay(y, window_size, order, deriv=0, rate=1):
    r"""Smooth (and optionally differentiate) data with a Savitzky-Golay filter.
    The Savitzky-Golay filter removes high frequency noise from data.
    It has the advantage of preserving the original shape and
    features of the signal better than other types of filtering
    approaches, such as moving averages techniques.
    Parameters
    ----------
    y : array_like, shape (N,)
        the values of the time history of the signal.
    window_size : int
        the length of the window. Must be an odd integer number.
    order : int
        the order of the polynomial used in the filtering.
        Must be less then `window_size` - 1.
    deriv: int
        the order of the derivative to compute (default = 0 means only smoothing)
    Returns
    -------
    ys : ndarray, shape (N)
        the smoothed signal (or it's n-th derivative).
    Notes
    -----
    The Savitzky-Golay is a type of low-pass filter, particularly
    suited for smoothing noisy data. The main idea behind this
    approach is to make for each point a least-square fit with a
    polynomial of high order over a odd-sized window centered at
    the point.
    Examples
    --------
    t = np.linspace(-4, 4, 500)
    y = np.exp( -t**2 ) + np.random.normal(0, 0.05, t.shape)
    ysg = savitzky_golay(y, window_size=31, order=4)
    import matplotlib.pyplot as plt
    plt.plot(t, y, label='Noisy signal')
    plt.plot(t, np.exp(-t**2), 'k', lw=1.5, label='Original signal')
    plt.plot(t, ysg, 'r', label='Filtered signal')
    plt.legend()
    plt.show()
    References
    ----------
    .. [1] A. Savitzky, M. J. E. Golay, Smoothing and Differentiation of
       Data by Simplified Least Squares Procedures. Analytical
       Chemistry, 1964, 36 (8), pp 1627-1639.
    .. [2] Numerical Recipes 3rd Edition: The Art of Scientific Computing
       W.H. Press, S.A. Teukolsky, W.T. Vetterling, B.P. Flannery
       Cambridge University Press ISBN-13: 9780521880688
    """

    try:
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError, msg:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order+1)
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
    m = np.linalg.pinv(b).A[deriv] * rate**deriv * factorial(deriv)
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - np.abs( y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + np.abs(y[-half_window-1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve( m[::-1], y, mode='valid')

class DouglasPeuckerSimplifier(object):

    def __init__(self,xs,ys,tolerance):
        self.xs = xs
        self.ys = ys
        self.tolerance = tolerance

        self.length = xs.size
        self.markers = np.zeros(self.length,dtype='bool')
        self.markers[[0,-1]] = 1

        #pre-allocate the temporary arrays used in getSquareSegmentDistances
        self.ts = np.empty(self.length)
        self.final_xs = np.empty(self.length)
        self.final_ys = np.empty(self.length)

        
    def getSquareSegmentDistances(self, first, last):
        """
        Square distance between point and a segment
        """
        inner = slice(first,last)
        x = self.xs[first]
        y = self.ys[first]

        dx = self.xs[last] - x
        dy = self.ys[last] - y

        if dx != 0 or dy != 0:
            inner_ts = self.ts[inner]

            final_xs = self.final_xs[inner]
            final_ys = self.final_ys[inner]
            final_xs[:] = x
            final_ys[:] = y

            inner_ts = (((self.xs[inner] - x) * dx 
                + (self.ys[inner] -y) * dy) / (dx*dx + dy*dy))

            large_ts = inner_ts>1
            small_ts = inner_ts>0 & ~large_ts

            final_xs[small_ts] += dx*inner_ts[small_ts]
            final_ys[small_ts] += dy*inner_ts[small_ts]

            final_xs[large_ts] = self.xs[last]
            final_ys[large_ts] = self.ys[last]


        dx = self.xs[inner] - final_xs
        dy = self.ys[inner] - final_ys

        return dx * dx + dy * dy

    def simplifyDouglasPeucker(self):

        first = 0
        last = self.length - 1

        first_stack = np.empty(self.length,dtype='uint32')
        first_i = -1
        last_stack = np.empty(self.length,dtype='uint32')
        last_i = -1

        while last is not None:
            max_sqdist = 0
            sqdists = self.getSquareSegmentDistances(first,last)
            max_idx = np.argmax(sqdists)
            max_sqdist = sqdists[max_idx]
            max_idx += first

            if max_sqdist > self.tolerance:
                self.markers[max_idx] = 1

                first_stack[first_i+1:first_i+3] = first,max_idx
                last_stack[last_i+1:last_i+3] = max_idx,last
                first_i +=2
                last_i += 2

            if first_i < 0:
                first = None
            else:
                first = first_stack[first_i]
                first_i -=1 

            if last_i < 0:
                last = None
            else:
                last = last_stack[last_i]
                last_i -=1 

        return self.xs[self.markers],self.ys[self.markers],np.where(self.markers)[0]


def simplify(xs,ys, tolerance=0.1, highestQuality=True):
    sqtolerance = tolerance * tolerance
    #smooth it out first
    xs = savitzky_golay(xs,25,5)
    return DouglasPeuckerSimplifier(xs,ys,sqtolerance).simplifyDouglasPeucker()
