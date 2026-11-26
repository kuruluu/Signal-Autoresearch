"""Numerical QML sandwich using summed Hessian and per-observation scores."""
import numpy as np


def sandwich(loglikelihood, parameters, step=1e-4):
    p=np.asarray(parameters,float);k=len(p);base=np.asarray(loglikelihood(p),float)
    n=len(base);scores=np.empty((n,k));hessian=np.empty((k,k));eye=np.eye(k)*step
    for i in range(k):
        plus=np.asarray(loglikelihood(p+eye[i]));minus=np.asarray(loglikelihood(p-eye[i]))
        scores[:,i]=(plus-minus)/(2*step)
        hessian[i,i]=(plus.sum()-2*base.sum()+minus.sum())/step**2
        for j in range(i):
            cross=(np.sum(loglikelihood(p+eye[i]+eye[j]))-np.sum(loglikelihood(p+eye[i]-eye[j]))
                   -np.sum(loglikelihood(p-eye[i]+eye[j]))+np.sum(loglikelihood(p-eye[i]-eye[j])))/(4*step**2)
            hessian[i,j]=hessian[j,i]=cross
    information=-hessian
    if not np.isfinite(information).all() or np.linalg.eigvalsh(information).min()<=0:
        raise ValueError('Observed information is not positive definite')
    inverse=np.linalg.inv(information);cov=inverse@(scores.T@scores)@inverse
    return dict(covariance=cov,scores=scores,information=information,
                gradient=scores.sum(0),condition_number=float(np.linalg.cond(information)))
