---
name: run-pipeline
description: Run the global embed → compute → discover pipeline across all artists
---

Run the global batch processing pipeline in sequence:

```bash
python scripts/embed.py && python scripts/compute.py && python scripts/discover.py
```

Report the output of each step. If any step fails, stop and report the error — do not proceed to the next step.
