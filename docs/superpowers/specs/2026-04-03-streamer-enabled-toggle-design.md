# Streamer Enabled Toggle

## Summary

Add per-streamer `enabled` field to `config.yaml`. Disabled streamers are completely excluded from recording, status monitoring, video processing, and upload — as if they don't exist in the config.

## Motivation

The user manages multiple streamers but doesn't always want to record all of them simultaneously. A simple config-level toggle avoids the need to delete and re-add streamer config blocks.

## Design

### Config Format

Add optional `enabled` field under each streamer in `config.yaml`. Defaults to `true` when omitted.

```yaml
streamers:
  洞主:
    room_id: "138243"
    enabled: true          # optional, defaults to true
    upload:
      ...

  银剑君:
    room_id: "251783"
    enabled: false         # disabled: skip entirely
    upload:
      ...

  二抛:
    room_id: "4452132"
    upload:                # enabled omitted → defaults to true
      ...
```

### Implementation

**Single change point:** `uploader.py` → `load_yaml_config()`

In the streamer iteration loop, after extracting `streamer_data`, check `enabled`:
- If `enabled is False` (strict identity check), log at INFO level and `continue` (skip this streamer)
- Any other value (including omitted/`true`/`null`) → proceed as normal
- After the loop, if `streamers_list` is empty (all disabled or none configured), log a WARNING

No other modules need changes. All downstream consumers (`app.py` startup, `recording_service.py`, `scheduler.py`) read from `config.STREAMERS`, which is populated by `load_yaml_config()`. Skipping a streamer there removes it from the entire pipeline.

### New Streamer: 二抛

Add to `config.yaml`:

```yaml
  二抛:
    room_id: "4452132"
    upload:
      source: "https://www.douyu.com/4452132"
      title: "二抛直播录像{time}{danmaku_tag}"
      desc: |
            二抛的精彩直播录像！
            主播直播间地址：https://www.douyu.com/4452132
            欢迎关注！
      tid: 171
      tag: "二抛,直播录像,游戏实况"
      cover: ''
      dynamic: ''
```

## Affected Files

| File | Change |
|------|--------|
| `src/douyu2bilibili/uploader.py` | `load_yaml_config()`: add `enabled` check in streamer loop |
| `config.yaml` | Add `二抛` streamer config |

## Testing

- Unit test: `load_yaml_config()` skips streamers with `enabled: false`, includes `enabled: true` and omitted
- Unit test: all streamers disabled → function returns `True` with empty `STREAMERS`, logs warning
- Unit test: non-boolean `enabled` values (`0`, `null`, `"false"`) are NOT filtered (only `false` is)
