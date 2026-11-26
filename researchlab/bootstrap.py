"""Synchronized stationary bootstrap, preserving cross-strategy dependence."""
import numpy as np


def stationary_indices(n, count, block, seed):
    rng = np.random.default_rng(seed)
    indices = np.empty((count, n), dtype=np.int32)
    indices[:, 0] = rng.integers(n, size=count)
    for t in range(1, n):
        restart = rng.random(count) < 1 / block
        indices[:, t] = np.where(restart, rng.integers(n, size=count), (indices[:, t - 1] + 1) % n)
    return indices


def inference(matrix, count=2000, block=20, seed=6413, reserved_papers=50):
    x = np.asarray(matrix, dtype=float)
    if x.ndim != 2 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError('Finite aligned T x strategies matrix required')
    idx = stationary_indices(len(x), count, block, seed)
    # Each resample uses identical time indices for EVERY asset/strategy column.
    means = np.empty((count, x.shape[1]))
    for start in range(0, count, 20):
        means[start:start + 20] = x[idx[start:start + 20]].mean(axis=1)
    observed = x.mean(axis=0)
    se = means.std(axis=0, ddof=1)
    safe_se = np.maximum(se, 1e-12)
    null_t = (means - observed) / safe_se
    observed_t = observed / safe_se
    max_t = null_t.max(axis=1)
    single_p = (1 + (null_t >= observed_t).sum(axis=0)) / (count + 1)
    fwer = (1 + (max_t[:, None] >= observed_t).sum(axis=0)) / (count + 1)
    adjusted = np.maximum(fwer, np.minimum(1, single_p * reserved_papers))
    intervals = np.quantile(means, [.025, .975], axis=0)
    return {'mean_daily': observed, 'low_daily': intervals[0], 'high_daily': intervals[1],
            'p_one_sided': single_p, 'p_max_t': fwer, 'p_conservative': adjusted,
            'standard_error': se}
