import cv2
import dxcam
import numpy as np


def stats(bgra):
    g = cv2.cvtColor(bgra, cv2.COLOR_BGRA2GRAY)
    return float(np.mean(g)), float(np.std(g))


def main() -> None:
    cam = dxcam.create(device_idx=0, output_idx=0, output_color="BGRA")

    full = cam.grab()
    print("full:", None if full is None else (full.shape, *stats(full)))

    regs = [
        (0, 0, 1920, 1009),
        (0, 1, 1920, 1010),
        (0, 2, 1920, 1011),
        (0, 8, 1920, 1017),
        (0, 16, 1920, 1025),
        (0, 23, 1920, 1032),
        (0, 24, 1920, 1033),
        (0, 32, 1920, 1041),
    ]

    for reg in regs:
        shot = cam.grab(region=reg)
        if shot is None:
            print("region", reg, "-> None")
        else:
            mean, std = stats(shot)
            print("region", reg, "->", shot.shape, "mean", mean, "std", std)


if __name__ == "__main__":
    main()
