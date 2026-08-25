# Video Agent

Owns how an approved content plan becomes a video: production method, clips, timeline, subtitles, FFmpeg/tool use, and the read-only integration with `zis-video-workflow`.

Inputs: source video, `content_to_video.json`, `rules/video.md`, adapter capability/configuration.

Outputs: `video_to_review.json` plus real output paths. Missing capabilities must be reported as `capability_unavailable`; no fabricated export is allowed.

