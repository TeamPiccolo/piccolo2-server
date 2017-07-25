# numpy implementation of https://github.com/omarestrella/simplify.py
# It uses a combination of Douglas-Peucker and Radial Distance algorithms

import numpy as np

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

        return self.xs[self.markers],self.ys[self.markers]


def simplify(xs,ys, tolerance=0.1, highestQuality=True):
    sqtolerance = tolerance * tolerance

    return DouglasPeuckerSimplifier(xs,ys,sqtolerance).simplifyDouglasPeucker()
