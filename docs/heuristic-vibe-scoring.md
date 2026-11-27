# Heuristic vibe scoring

VibeSorter ranks each canonical vibe using a small, deterministic set of measurable image signals. It does not infer a person's emotions, and it does not use a neural network.

## Comparable scores

Each rule set has a documented maximum possible weighted score. Individual weighted contributions are divided by that maximum before being summed. This prevents a label from receiving an automatic advantage merely because its rule set contains more weighted terms.

The result is a bounded heuristic ranking score from 0 to 1. **It is not a probability, calibrated confidence, or a claim that the image objectively has a particular mood.** It only describes how strongly the currently implemented visual rules match the image's measured features.

## Evidence inspection

The explanation API exposes the weighted contribution of each signal for every candidate vibe. These values make the rule behavior inspectable and testable. A contribution is evidence used by a rule, not proof of a semantic concept.

## Limitations

Low contrast, warm colors, low saturation, and brightness are visual properties. They are not reliable standalone evidence that an image is dreamy, cozy, romantic, or soft. The labels remain heuristic style suggestions and should be treated cautiously. Further improvements should add better measurable features and uncertainty handling rather than claiming human-like understanding.

## Offline and dependency policy

The default classifier uses the existing Pillow-based feature pipeline. It requires no model weights, cloud service, network connection, or heavyweight machine-learning runtime.
