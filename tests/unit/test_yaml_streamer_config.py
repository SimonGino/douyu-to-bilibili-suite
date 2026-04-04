"""Tests for config.yaml loading and STREAMERS derivation."""
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from douyu2bilibili import config as config_module
from douyu2bilibili import uploader


@pytest.fixture
def write_yaml_config(tmp_path: Path, monkeypatch):
    """Write YAML content to a temp file and patch the config path."""
    def _write(content: str) -> Path:
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(content, encoding="utf-8")
        monkeypatch.setattr(config_module, "YAML_CONFIG_PATH", str(yaml_file))
        return yaml_file
    return _write


def test_load_yaml_config_populates_streamers(write_yaml_config):
    yaml_content = """\
streamers:
  洞主:
    room_id: "138243"
    upload:
      title: "洞主直播录像{time}弹幕版"
      tid: 171
      tag: "洞主,直播录像"
      desc: "测试简介"
      source: "https://www.douyu.com/138243"
      cover: ""
      dynamic: ""
  银剑君:
    room_id: "999999"
    upload:
      title: "银剑君直播录像{time}"
      tid: 171
      tag: "银剑君,直播录像"
      desc: "银剑君简介"
      source: "https://www.douyu.com/999999"

upload:
  max_concurrent: 2
"""
    write_yaml_config(yaml_content)

    result = uploader.load_yaml_config()

    assert result is True
    assert len(config_module.STREAMERS) == 2
    assert config_module.STREAMERS[0]["name"] == "洞主"
    assert config_module.STREAMERS[0]["room_id"] == "138243"
    assert config_module.STREAMERS[1]["name"] == "银剑君"
    assert config_module.STREAMERS[1]["room_id"] == "999999"

    assert "洞主" in uploader.streamer_configs
    assert uploader.streamer_configs["洞主"]["title"] == "洞主直播录像{time}弹幕版"
    assert "银剑君" in uploader.streamer_configs
    assert uploader.streamer_configs["银剑君"]["cover"] == ""  # default

    assert uploader.upload_global_config.get("max_concurrent") == 2


def test_load_yaml_config_fails_on_missing_room_id(write_yaml_config):
    yaml_content = """\
streamers:
  洞主:
    upload:
      title: "test{time}"
      tid: 171
      tag: "t"
      desc: "d"
      source: "s"
"""
    write_yaml_config(yaml_content)

    result = uploader.load_yaml_config()
    assert result is False


def test_load_yaml_config_fails_on_missing_upload_fields(write_yaml_config):
    yaml_content = """\
streamers:
  洞主:
    room_id: "138243"
    upload:
      title: "test{time}"
      # missing tid, tag, desc, source
"""
    write_yaml_config(yaml_content)

    result = uploader.load_yaml_config()
    assert result is False


def test_load_yaml_config_fails_on_missing_streamers(write_yaml_config):
    yaml_content = """\
upload:
  max_concurrent: 1
"""
    write_yaml_config(yaml_content)

    result = uploader.load_yaml_config()
    assert result is False


def test_single_streamer_backward_compatible(write_yaml_config):
    yaml_content = """\
streamers:
  洞主:
    room_id: "138243"
    upload:
      title: "洞主直播录像{time}弹幕版"
      tid: 171
      tag: "洞主,凯哥,直播录像,游戏实况"
      desc: "简介"
      source: "https://www.douyu.com/138243"
      cover: ""
      dynamic: ""
"""
    write_yaml_config(yaml_content)

    result = uploader.load_yaml_config()

    assert result is True
    assert len(config_module.STREAMERS) == 1
    assert config_module.STREAMERS[0] == {"name": "洞主", "room_id": "138243"}


def test_danmaku_tag_placeholder_in_title(write_yaml_config):
    yaml_content = """\
streamers:
  洞主:
    room_id: "138243"
    upload:
      title: "洞主直播录像{time}{danmaku_tag}"
      tid: 171
      tag: "洞主,直播录像"
      desc: "测试简介"
      source: "https://www.douyu.com/138243"

upload:
  max_concurrent: 1
"""
    write_yaml_config(yaml_content)

    result = uploader.load_yaml_config()

    assert result is True
    assert "{danmaku_tag}" in uploader.streamer_configs["洞主"]["title"]


def test_enabled_false_skips_streamer(write_yaml_config):
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
    write_yaml_config(yaml_content)

    result = uploader.load_yaml_config()

    assert result is True
    assert len(config_module.STREAMERS) == 1
    assert config_module.STREAMERS[0]["name"] == "洞主"
    assert "银剑君" not in uploader.streamer_configs


def test_enabled_omitted_defaults_to_included(write_yaml_config):
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
    write_yaml_config(yaml_content)

    result = uploader.load_yaml_config()

    assert result is True
    assert len(config_module.STREAMERS) == 1
    assert config_module.STREAMERS[0]["name"] == "洞主"


def test_all_streamers_disabled_returns_true_with_warning(write_yaml_config):
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
    yaml_file = write_yaml_config(yaml_content)

    with patch.object(uploader.logger, "warning") as mock_warn:
        result = uploader.load_yaml_config()

    assert result is True
    assert len(config_module.STREAMERS) == 0
    mock_warn.assert_any_call(f"配置文件 {str(yaml_file)} 中没有启用的主播")


@pytest.mark.parametrize(
    "enabled_value",
    [0, "null", '"false"', '""'],
    ids=["int_zero", "yaml_null", "string_false", "empty_string"],
)
def test_non_boolean_false_enabled_not_filtered(write_yaml_config, enabled_value):
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
    write_yaml_config(yaml_content)

    result = uploader.load_yaml_config()

    assert result is True
    assert len(config_module.STREAMERS) == 1
