# Classifier improvement loop

1. Collect human labels for representative images.
2. Run the existing evaluation API.
3. Inspect confusion and low-margin diagnostics.
4. Change one scoring hypothesis at a time.
5. Re-run the same dataset and benchmark corpus.
6. Keep the change only when the measured trade-off is understood.

This avoids tuning the classifier from a handful of memorable images.
