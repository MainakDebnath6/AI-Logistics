import sys; sys.path.insert(0,'/home/claude/repro')
import numpy as np, pandas as pd
from experiments.common import ExperimentConfig, make_dataset, calculate_metrics
from experiments.forecasting import _naive_previous_week,_holt_winters_forecast,_seasonal_regression_forecast
from dataclasses import replace
full=frozenset({"weekly","annual","lags","rolling"})
rows=[]
for seed in range(1000,1040):
    cfg=replace(ExperimentConfig(),seed=seed); y=make_dataset(cfg); tr,te=y[:670],y[670:]
    for name,f in [("naive",lambda h:_naive_previous_week(tr,h)),("hw",lambda h:_holt_winters_forecast(tr,h)),("lr",lambda h:_seasonal_regression_forecast(tr,h,full))]:
        p=f(60); m=calculate_metrics(te,p); m7=calculate_metrics(te[:7],p[:7])
        rows.append(dict(seed=seed,model=name,mape60=m['mape_percent'],mae60=m['mae'],mape7=m7['mape_percent']))
d=pd.DataFrame(rows); d.to_csv('/home/claude/audit/seed_sweep_repo_impl.csv',index=False)
print(d.groupby('model')[['mape60','mae60','mape7']].agg(['mean','min','max']).round(2).to_string())
w=d.pivot(index='seed',columns='model',values='mape60')
print("seeds with HW<naive:", (w.hw<w.naive).sum(),"/40; LR best:",((w.lr<w.hw)&(w.lr<w.naive)).sum())
