import numpy as np
import matplotlib.pyplot as plt

def generate(velocities, flows, waiting_times):
    densities = np.arange(0.0, 1.1, 0.1)
    plt.plot(densities, flows)
    plt.plot(densities, flows_emergincy)
    plt.show()
    plt.plot(densities[1:], velocities)
    plt.show()
    plt.plot(densities, waiting_times)
    plt.show()


flows = [0,
0.86988297,
1.4144415,
1.39745689,
1.4044276,
1.40230703,
1.40732075,
1.40634588,
1.39710697,
1.39397906,
1.39676291]

velocities = [
12.1071856,
6.92760565,
7.93747758,
6.85631719,
7.34739613,
6.44406244,
6.58902317,
7.85017607,
7.90686819,
7.59635098
]

waiting_times = [
0,
39.60444444,
205.8571429,
239.84,
239.1478261,
240.5578947,
252.7875,
243.9666667,
251.2888889,
244.875,
254.125,
]
generate(velocities, flows, waiting_times)
