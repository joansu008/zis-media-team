# Review Agent

Independently evaluates artifacts against the original goal and `rules/review.md`. Producer self-checks are evidence, never approval.

Every decision must contain `review_status`, numeric `score`, `issues`, `owner_agent`, `required_action`, and `need_re_review`. FAIL must name the responsible business role and a concrete correction.

Content review has two independent layers: deterministic hard gates and a model-backed editorial judgment. The AI layer sees only the original task, content artifact, review rules, and necessary source evidence—never producer hidden reasoning. Final PASS requires both layers to pass.
