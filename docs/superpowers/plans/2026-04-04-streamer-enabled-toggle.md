# Streamer Enabled Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-streamer `enabled` toggle to `config.yaml` so disabled streamers are excluded from the entire pipeline, and add new streamer "二抛".

**Architecture:** Single change in `load_yaml_config()` — skip streamers where `enabled is False` (strict identity check). All downstream consumers already read from `config.STREAMERS` populated by this function, so no other modules need changes.

**Tech Stack:** Python, PyYAML, pytest

**Spec:** `docs/superpowers/specs/2026-04-03-streamer-enabled-toggle-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/douyu2bilibili/uploader.py` | Modify (lines 482-537) | Add `enabled` check in streamer loop, add empty-list warning after loop |
| `config.yaml` | Modify | Add 二抛 streamer block |
| `tests/unit/test_yaml_streamer_config.py` | Modify | Add tests for `enabled` filtering |

---

### Task 1: Add `enabled` filtering tests

**Files:**
- Modify: `tests/unit/test_yaml_streamer_config.py`

- [ ] **Step 1: Write test — `enabled: false` skips streamer**

Add to `tests/unit/test_yaml_streamer_config.py`:

```python
def test_enabled_false_skips_streamer(tmp_path: Path, monkeypatch):
    from douyu2bilibili import uploader

    yaml_content = """\
streamers:
  洞主:
    room_id: "138243"
    enabled: true
    upload:
      title: "test{time}"
      tid: 171
      tag: "t"
      desc: "d"
      source: "s"
  银剑君:
    room_id: "251783"
    enabled: false
    upload:
      title: "test{time}"
      tid: 171
      tag: "t"
      desc: "d"
      source: "s"
"""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")
    monkeypatch.setattr(config_module, "YAML_CONFIG_PATH", str(yaml_file))

    result = uploader.load_yaml_config()

    assert result is True
    assert len(config_module.STREAMERS) == 1
    assert config_module.STREAMERS[0]["name"] == "洞主"
    assert "银剑君" not in uploader.streamer_configs
```

- [ ] **Step 2: Write test — omitted `enabled` defaults to included**

```python
def test_enabled_omitted_defaults_to_included(tmp_path: Path, monkeypatch):
    from douyu2bilibili import uploader

    yaml_content = """\
streamers:
  洞主:
    room_id: "138243"
    upload:
      title: "test{time}"
      tid: 171
      tag: "t"
      desc: "d"
      source: "s"
"""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")
    monkeypatch.setattr(config_module, "YAML_CONFIG_PATH", str(yaml_file))

    result = uploader.load_yaml_config()

    assert result is True
    assert len(config_module.STREAMERS) == 1
    assert config_module.STREAMERS[0]["name"] == "洞主"
```

- [ ] **Step 3: Write test — all disabled returns True with empty list and logs warning**

```python
def test_all_streamers_disabled_returns_true_with_warning(tmp_path: Path, monkeypatch, caplog):
    import logging
    from douyu2bilibili import uploader

    yaml_content = """\
streamers:
  洞主:
    room_id: "138243"
    enabled: false
    upload:
      title: "test{time}"
      tid: 171
      tag: "t"
      desc: "d"
      source: "s"
"""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")
    monkeypatch.setattr(config_module, "YAML_CONFIG_PATH", str(yaml_file))

    with caplog.at_level(logging.WARNING):
        result = uploader.load_yaml_config()

    assert result is True
    assert len(config_module.STREAMERS) == 0
    assert any("没有启用的主播" in r.message for r in caplog.records)
```

- [ ] **Step 4: Write test — non-boolean values are NOT filtered**

```python
@pytest.mark.parametrize(
    "enabled_value",
    [0, "null", '"false"', '""'],
    ids=["int_zero", "yaml_null", "string_false", "empty_string"],
)
def test_non_boolean_false_enabled_not_filtered(tmp_path: Path, monkeypatch, enabled_value):
    from douyu2bilibili import uploader

    yaml_content = f"""\
streamers:
  洞主:
    room_id: "138243"
    enabled: {enabled_value}
    upload:
      title: "test{{time}}"
      tid: 171
      tag: "t"
      desc: "d"
      source: "s"
"""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")
    monkeypatch.setattr(config_module, "YAML_CONFIG_PATH", str(yaml_file))

    result = uploader.load_yaml_config()

    assert result is True
    assert len(config_module.STREAMERS) == 1
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_yaml_streamer_config.py -v -k "enabled"`
Expected: FAIL — `enabled: false` streamer is still included

- [ ] **Step 6: Commit test file**

```bash
git add tests/unit/test_yaml_streamer_config.py
git commit -m "test: add enabled toggle tests for load_yaml_config"
```

---

### Task 2: Implement `enabled` filtering in `load_yaml_config()`

**Files:**
- Modify: `src/douyu2bilibili/uploader.py:482-537`

- [ ] **Step 1: Add `enabled` check in streamer loop**

In `load_yaml_config()`, right after the `if not isinstance(streamer_data, dict)` check (line 486), add:

```python
                # Skip disabled streamers (only strict `False` triggers skip)
                if streamer_data.get('enabled') is False:
                    logger.info(f"主播 '{streamer_name}' 已禁用 (enabled: false)，跳过")
                    continue
```

- [ ] **Step 2: Add warning when no streamers are enabled**

Between the `if not valid: ... return False` block (lines 521-523) and `streamer_configs.clear()` (line 525), insert:

```python
            if not streamers_list:
                logger.warning("配置文件中没有启用的主播")
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_yaml_streamer_config.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add src/douyu2bilibili/uploader.py
git commit -m "feat: add per-streamer enabled toggle in load_yaml_config"
```

---

### Task 3: Add 二抛 to config.yaml

**Files:**
- Modify: `config.yaml`

- [ ] **Step 1: Add 二抛 streamer block**

Append after the 银剑君 block (before the `upload:` global section):

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

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest tests/unit/test_yaml_streamer_config.py -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add config.yaml
git commit -m "feat: add streamer 二抛 (room 4452132) to config"
```
