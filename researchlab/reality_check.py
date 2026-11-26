"""White centered maximum-mean statistic, conditional on fixed rule returns."""
import numpy as np


def statistics(values,indices):
    values=np.asarray(values,float);indices=np.asarray(indices,int)
    if values.ndim!=2 or indices.ndim!=2 or indices.shape[1]!=len(values):raise ValueError('Invalid panel/resamples')
    if not np.isfinite(values).all():raise ValueError('Nonfinite performance')
    mean=values.mean(0);observed=np.sqrt(len(values))*mean.max()
    draws=np.sqrt(len(values))*(values[indices].mean(1)-mean).max(1)
    return float(observed),draws


def stationary_indices(n,paths,restart_probability,rng):
    if n<1 or paths<1 or not 0<restart_probability<=1:raise ValueError('Invalid bootstrap settings')
    idx=np.empty((paths,n),int);idx[:,0]=rng.integers(n,size=paths)
    for j in range(1,n):idx[:,j]=np.where(rng.random(paths)<restart_probability,rng.integers(n,size=paths),(idx[:,j-1]+1)%n)
    return idx
