"""Synthetic likelihood validation only; never fits historical observations."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from .p74_model import simulate,filter_model


def main():
    truth=np.array([.01,-4.,-3.,.5,25.,-.2,.3,.2])
    n=2400;months=np.arange(n)%12+1;bill=.003+.001*np.sin(np.arange(n)/30)
    y,_,_=simulate(truth,bill,months,.0025,seed=74021)
    # Numerical coordinate scaling; parameters remain in documented decimal units.
    scales=np.array([.01,5,3,.5,30,.3,.5,.5])
    bounds=[(-5,5),(-8,8),(-6,-.01),(-1.9,1.9),(-10,10),(-5,5),(-1.9,6),(-1.9,6)]
    def objective(z):
        try:return -filter_model(z*scales,y,bill,months,.0025)['loglikelihood'].mean()
        except (ValueError,OverflowError):return 1e20
    records=[]
    for multiplier in [.9,1.1]:
        fit=minimize(objective,truth/scales*multiplier,method='L-BFGS-B',bounds=bounds,
                     options={'maxiter':400,'ftol':1e-11,'gtol':1e-6})
        records.append(dict(success=bool(fit.success),message=str(fit.message),objective=float(fit.fun),
                            parameters=(fit.x*scales).tolist(),iterations=int(fit.nit)))
    out=Path('research/replication_first/p74_audit/synthetic_validation_001.json')
    if out.exists():raise FileExistsError('Preserve previous validation')
    result=dict(seed=74021,n=n,truth=truth.tolist(),runs=records,
                scope='One synthetic path, two nearby starts. Diagnostic only; not robust parameter recovery or sandwich validation.',
                historical_data_used=False)
    out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
