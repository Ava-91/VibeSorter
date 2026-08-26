# Test suite

The tests use temporary files and generated Pillow images so they do not depend on a personal image library. Run the suite with:

```bash
python -m pytest
```

The suite is split by behavior: feature contracts, classifier invariants, pipeline behavior, evaluation, and existing command/module tests.
