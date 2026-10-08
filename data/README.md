# Synthetic Demand Dataset

`raw/synthetic_demand.csv` is controlled synthetic data, not real-world logistics data. Regenerate it from the repository root with:

```bash
python -m experiments.data_generation
```

The generator writes exactly 730 consecutive daily observations beginning `2024-01-01`; `data_type` labels every row `synthetic`. The default seed is `20261008` and the generator uses NumPy's `default_rng`.

For day index $t = 0, \ldots, 729$, demand is:

```text
max(0, 100 + 0.04*t
       + 18*sin(2*pi*t/7)
       + 25*sin(2*pi*t/365.25)
       + Normal(0, 5))
```

There are 670 chronological training observations and 60 chronological holdout observations. No shuffling is performed. The annual period approximates a solar year; the additive Gaussian noise has sigma 5. Values are clipped at zero to avoid impossible negative demand.

This small, designed series is useful for checking deterministic pipelines and feature behavior. It does not represent a measured customer, fleet, location, or real demand distribution. Performance on it is not evidence of real-world accuracy or a paper result.