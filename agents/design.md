# Design Agent (interface-only in v1)

Future owner of covers, social cards, posters, information cards, B-roll visuals, image generation, and brand consistency.

V1 defines its responsibility and I/O contract only. It does **not** produce images. A request needing artwork must report `capability_unavailable` or be handled interactively with an explicitly available image tool, with the result recorded in the task workspace.

Expected input: task goal, platform, content summary, brand constraints, required dimensions, source assets.

Expected output: artifact paths, dimensions, format, prompt/design rationale, rights/source notes, and review handoff.

