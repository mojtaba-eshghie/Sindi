## Reproducing the invariant subsumption experiment: 

We have two commands (for Sindi and Sindi light):
```sh
python sindi_batch_compare.py \
  --input datasets/require_statement_updates.json \
  --output datasets/require_updates_strict.csv \
  --print-summary  
```

```sh
python sindi_batch_compare.py \
  --input datasets/require_statement_updates.json \
  --output datasets/require_updates_strict.csv \
  --print-summary --light
```