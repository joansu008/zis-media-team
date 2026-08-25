# Independent review rules

Content review checks completeness, relevance, opening, logic, title/content match, unsupported claims, omissions, and task fit.

Video review checks source range validity, timeline order, accidental duplication, completeness, subtitles when requested, generated file existence/non-zero size, and workflow compliance.

Return structured JSON. FAIL must set `need_re_review: true`, identify `owner_agent`, and state a testable required action. PASS must set `need_re_review: false`. The Manager permits at most two automatic revisions per stage, then escalates to `needs_human_review`.

