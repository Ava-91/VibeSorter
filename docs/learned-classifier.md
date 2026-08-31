# Learned classifier

VibeSorter now includes an offline nearest-centroid classifier. It learns one feature centroid per labelled vibe from the existing JSONL evaluation format, using global and spatial visual features. The model is dependency-free and can be serialized to JSON.

The heuristic classifier remains the reference baseline. Use `LearnedClassifier.fit(load_labels(...))`, evaluate it with `evaluate_classifier(...)`, and compare its metrics before making it the default classifier.

This keeps the project local-first while making classifier quality data-driven rather than requiring a cloud model or a heavyweight ML dependency.
