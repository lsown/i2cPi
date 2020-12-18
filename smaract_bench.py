import asyncio as aio 
import datetime
import math
import numpy as np
import uvloop
import time

import matplotlib
import matplotlib.pyplot as plt

from typing import List, Optional, Tuple

from gridcon_client import GridConClient, GridConError, GridConPacket

async def retry(f, retries):
    for i in range(retries + 1):
        try:
            return await f()
        except Exception as e:
            if i == retries:
                raise
            else:
                print("Retrying after error: %s" % e)

async def main():
    gridcon = GridConClient()
    gridcon_name = "pni-gridstage-3"
    await gridcon.open("10.0.0.240", 81, gridcon_name, key=b"mochiiisontheiss")

    await gridcon.calibrate_stage()
    await gridcon.zero_stage()

    x_latency = []
    y_latency = []
    latency_grid = []
    error_grid = []

    move_nm = 20000
    skew_nm = 300
    x_size = 30
    y_size = 30

    await gridcon.stage_position.set([-skew_nm, -move_nm])

    for y in range(y_size):
        latency_row = []
        error_row = []
        for x in range(x_size):
            if y % 2 == 0:
                ask_pos = [
                    move_nm * x + (y * skew_nm),
                    move_nm * y + (x * skew_nm),
                ]
            else:
                x_inverted = (x_size - 1 - x)
                ask_pos = [
                    move_nm * x_inverted + (y * skew_nm),
                    move_nm * y + (x_inverted * skew_nm),
                ]

            start_time = time.time()
            response = await gridcon.stage_position.set(ask_pos)
            #duration = time.time() - start_time
            duration = response[0]

            if x != 0:
                x_latency.append(duration)
            else:
                y_latency.append(duration)
            latency_row.append(duration)

            stage_pos = await gridcon.read_stage_position()

            error_row.append((
                ask_pos[0] - stage_pos[0],
                ask_pos[1] - stage_pos[1],
            ))

        if y % 2 == 1:
            latency_row.reverse()
            error_row.reverse()
        latency_grid.append(latency_row)
        error_grid.append(error_row)

    await gridcon.close()

    x_error_grid = [
        [abs(cell[0]) for cell in row]
        for row in error_grid
    ]
    y_error_grid = [
        [abs(cell[1]) for cell in row]
        for row in error_grid
    ]
    total_error_grid = [
        [math.sqrt(cell[0]*cell[0] + cell[1]*cell[1]) for cell in row]
        for row in error_grid
    ]

    print("X move duration: %.1f +/- %.1f ms" % (np.mean(x_latency) * 1000.0, np.std(x_latency) * 1000.0))
    print("Y move duration: %.1f +/- %.1f ms" % (np.mean(y_latency) * 1000.0, np.std(y_latency) * 1000.0))
    print("X distance error: %.1f +/- %.1f nm" % (np.mean(x_error_grid), np.std(x_error_grid)))
    print("Y distance error: %.1f +/- %.1f nm" % (np.mean(y_error_grid), np.std(y_error_grid)))

    # Client latency histogram
    n, bins, patches = plt.hist(x_latency, 50, facecolor='green', alpha=0.75)
    plt.xlabel('Seconds')
    plt.ylabel('Occurrences')
    plt.title("X latency histogram")
    plt.axis([min(x_latency), max(x_latency), 0, max(n)])
    plt.grid(True)
    plt.show()

    # Client latency histogram
    n, bins, patches = plt.hist(y_latency, 50, facecolor='green', alpha=0.75)
    plt.xlabel('Seconds')
    plt.ylabel('Occurrences')
    plt.title("Y latency histogram")
    plt.axis([min(y_latency), max(y_latency), 0, max(n)])
    plt.grid(True)
    plt.show()

    fig = plt.figure()
    plt.title("Move duration heatmap")
    plt.imshow(latency_grid)
    plt.colorbar()
    fig.canvas.draw()
    plt.show()

    fig = plt.figure()
    plt.title("Total error heatmap")
    plt.imshow(total_error_grid)
    plt.colorbar()
    fig.canvas.draw()
    plt.show()

    fig = plt.figure()
    plt.title("X error heatmap")
    plt.imshow(x_error_grid)
    plt.colorbar()
    fig.canvas.draw()
    plt.show()

    fig = plt.figure()
    plt.title("Y error heatmap")
    plt.imshow(y_error_grid)
    plt.colorbar()
    fig.canvas.draw()
    plt.show()

##################################

await main()