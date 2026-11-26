"""Causal P74 forecast mapping with explicitly delayed bill information."""
import numpy as np
from .p74_model import filter_model


def forecast(parameters, completed_excess, completed_bill, completed_months,
             target_month, initial_variance=.0025):
    """Use previous completed month's bill return as the next bill proxy.

    The historical likelihood must use this same lagged-bill definition when
    estimating parameters for this branch. It is a declared timing adaptation.
    One additional month of bill history is required to align lagged inputs.
    """
    y=np.asarray(completed_excess,float);bill=np.asarray(completed_bill,float)
    if len(bill)!=len(y)+1 or len(y)==0:raise ValueError('Need one extra completed bill observation')
    f=filter_model(parameters,y,bill[:-1],completed_months,initial_variance)
    a0,a1,b0,b1,b2,g1,october,january=np.asarray(parameters,float)
    logh=b0+b1*np.log(f['fundamental_variance'][-1])+b2*bill[-1]+g1*f['innovation'][-1]/np.sqrt(f['fundamental_variance'][-1])
    if not np.isfinite(logh) or not -700<logh<700:raise ValueError('Invalid forecast variance')
    scale=1+october*(target_month==10)+january*(target_month==1)
    if scale<=0 or target_month not in range(1,13):raise ValueError('Invalid month/scale')
    variance=scale**2*np.exp(logh)
    return float(a0+a1*variance),float(variance)
