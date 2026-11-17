"""Subject mask without any model download: fit the plain wall's colour as a smooth
2D surface from known-wall pixels (top band + side strips), then call anything far
from that surface 'person'. Keeps the blob connected to the bottom centre."""
import cv2, numpy as np

W, H = 270, 480  # work size

def _design(xs, ys):
    x = xs / W - 0.5; y = ys / H - 0.5
    return np.stack([np.ones_like(x), x, y, x*x, y*y, x*y], 1)

class WallMask:
    def __init__(self, frames_bgr, wall_top=0.26, side=0.07, thr=11.0):
        labs = [cv2.cvtColor(cv2.resize(f, (W, H)), cv2.COLOR_BGR2LAB).astype(np.float32) for f in frames_bgr]
        lab = np.median(np.stack(labs), 0)
        ys, xs = np.mgrid[0:H, 0:W]
        known = (ys < H * wall_top) | (((xs < W * side) | (xs > W * (1 - side))) & (ys < H * 0.55))
        A = _design(xs[known].astype(np.float32), ys[known].astype(np.float32))
        self.model = np.zeros((H, W, 3), np.float32)
        Afull = _design(xs.ravel().astype(np.float32), ys.ravel().astype(np.float32))
        for c in range(3):
            coef, *_ = np.linalg.lstsq(A, lab[..., c][known], rcond=None)
            self.model[..., c] = (Afull @ coef).reshape(H, W)
        self.thr = thr

    def __call__(self, frame_bgr, out_size):
        s = cv2.resize(frame_bgr, (W, H))
        lab = cv2.cvtColor(s, cv2.COLOR_BGR2LAB).astype(np.float32)
        d = np.sqrt((((lab - self.model) ** 2) * np.array([0.35, 1.6, 1.6], np.float32)).sum(2))
        m = (d > self.thr).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        k, lab_, st, _ = cv2.connectedComponentsWithStats(m)
        if k > 1:
            # component that touches the bottom and is biggest
            best, ba = 0, 0
            for i in range(1, k):
                if st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT] >= H - 3 and st[i, cv2.CC_STAT_AREA] > ba:
                    best, ba = i, st[i, cv2.CC_STAT_AREA]
            if best:
                m = (lab_ == best).astype(np.uint8)
        ff = m.copy(); msk = np.zeros((H + 2, W + 2), np.uint8)
        cv2.floodFill(ff, msk, (0, 0), 1); m = m | (1 - ff)
        m = cv2.GaussianBlur(m.astype(np.float32), (5, 5), 0)
        return cv2.resize(m, out_size, interpolation=cv2.INTER_LINEAR)
