# zis-video-workflow adapter contract

This repository never edits or copies the sibling project. Detection uses, in order, `ZIS_VIDEO_WORKFLOW_PATH` and the sibling directory `../zis-video-workflow`.

Detection alone is not execution. To make the capability executable, each machine must set both:

- `ZIS_VIDEO_WORKFLOW_PATH`: absolute or project-relative path to the local clone.
- `ZIS_VIDEO_WORKFLOW_COMMAND`: command prefix exposed by that project.

The adapter appends these arguments:

```text
--input <source-media> --task-dir <task-workspace> --handoff <content-handoff>
```

For a revision, the adapter also appends:

```text
--revision-request <revision-request-json>
```

The configured command must exit with code 0 and create or replace `outputs/video_manifest.json` inside the task workspace. The manifest should contain `output_file`, `timeline`, `subtitles_required`, and `subtitle_file`. Until the external project exposes this contract—or a thin wrapper implements it—the adapter truthfully reports `capability_unavailable`.

The smoke test only probes configuration and files. It does not run heavy media work.
