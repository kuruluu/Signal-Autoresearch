"""P74 published Model 5-L recursion, not a generic EGARCH substitute.

All inputs and parameters use decimal-return units. b0 is a log-variance
intercept. The scan's Table V 'b0 (x100)' label is ambiguous; do not rescale
that published value into a fixed calibration without resolving the units.
"""
import numpy as np


def filter_model(parameters, excess, bill, months, initial_variance):
    """Conditional means/variances and Gaussian per-observation log likelihood.

    parameters: a0,a1,b0,b1,b2,g1,lambda_oct,lambda_jan.
    Model 5-L restricts g2=0, per text below Table V. Innovations are signed.
    Initial fundamental variance is supplied, not inferred from future data.
    For t=0 use that initial variance directly; subsequent recursion uses
    previous deseasonalized shock and current month's bill-return input.
    Whether bill[t] was actually known in advance is a separate data audit.
    """
    a0,a1,b0,b1,b2,g1,october,january=np.asarray(parameters,float)
    y=np.asarray(excess,float);rf=np.asarray(bill,float);month=np.asarray(months,int)
    if y.ndim!=1 or len(y)==0 or rf.shape!=y.shape or month.shape!=y.shape:
        raise ValueError('Misaligned inputs')
    if not np.isfinite(y).all() or not np.isfinite(rf).all() or not np.isfinite(parameters).all():
        raise ValueError('Nonfinite inputs')
    if not np.isfinite(initial_variance) or initial_variance<=0 or ((month<1)|(month>12)).any():
        raise ValueError('Invalid initialization or months')
    scale=1+october*(month==10)+january*(month==1)
    if (scale<=0).any():raise ValueError('Nonpositive seasonal scale')
    n=len(y);h=np.empty(n);v=np.empty(n);mu=np.empty(n);eta=np.empty(n);ll=np.empty(n)
    logh=float(np.log(initial_variance))
    for t in range(n):
        if t:
            logh=b0+b1*np.log(h[t-1])+b2*rf[t]+g1*eta[t-1]/np.sqrt(h[t-1])
        # Reject invalid parameter paths instead of clipping away model failures.
        if not np.isfinite(logh) or not -700<logh<700:raise ValueError('Invalid log-variance path')
        h[t]=np.exp(logh);v[t]=scale[t]**2*h[t]
        mu[t]=a0+a1*v[t];epsilon=y[t]-mu[t];eta[t]=epsilon/scale[t]
        with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
            ll[t]=-.5*(np.log(2*np.pi)+np.log(v[t])+epsilon**2/v[t])
        if not np.isfinite(ll[t]):raise ValueError('Invalid likelihood')
    return dict(fundamental_variance=h,variance=v,mean=mu,innovation=eta,loglikelihood=ll)


def simulate(parameters,bill,months,initial_variance,seed=74001):
    """Generate known-parameter data for numerical validation only."""
    a0,a1,b0,b1,b2,g1,october,january=np.asarray(parameters,float)
    rf=np.asarray(bill,float);month=np.asarray(months,int)
    rng=np.random.default_rng(seed);z=rng.standard_normal(len(rf));y=np.empty(len(rf));h=np.empty(len(rf))
    scale=1+october*(month==10)+january*(month==1)
    if (scale<=0).any() or initial_variance<=0:raise ValueError('Invalid synthetic inputs')
    for t in range(len(rf)):
        h[t]=initial_variance if t==0 else np.exp(b0+b1*np.log(h[t-1])+b2*rf[t]+g1*z[t-1])
        v=scale[t]**2*h[t]
        y[t]=a0+a1*v+scale[t]*np.sqrt(h[t])*z[t]
    return y,h,z
