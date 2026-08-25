# Video rules

- Never edit a sibling project or copy it wholesale into this repository.
- Invoke external production only through the adapter contract.
- Validate source existence, time ranges, output existence/non-zero size, timeline order, repetitions, and subtitle presence when required.
- Keep local media and exports out of Git.
- Missing FFmpeg or adapter configuration is `capability_unavailable`, not success.

