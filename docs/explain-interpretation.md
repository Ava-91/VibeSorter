# Interpreting explanations

A high winner score does not mean certainty. Check the winner margin and `ambiguous` flag. When a second vibe is close enough to the winner, `selected_vibes` exposes it instead of hiding the overlap.

Feature signals are the raw visual measurements available to the deterministic classifier. They are useful for debugging and comparing classifier behavior, not as claims about the semantic content of an image.

For example, a high `dark_ratio` and high `contrast` support a Dark / Moody score, while a negative center brightness delta means the center is darker than the surrounding regions.
