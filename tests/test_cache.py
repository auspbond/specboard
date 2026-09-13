import json

from cache import _hash, _page_path, _extraction_path, get_page, set_page, disable


class TestHash:
    def test_deterministic(self):
        assert _hash("a", "b") == _hash("a", "b")

    def test_different_inputs_different_hash(self):
        assert _hash("a", "b") != _hash("a", "c")

    def test_order_matters(self):
        assert _hash("a", "b") != _hash("b", "a")

    def test_returns_16_chars(self):
        assert len(_hash("test")) == 16


class TestPagePath:
    def test_rendered_flag_changes_path(self):
        p1 = _page_path("https://example.com", rendered=False)
        p2 = _page_path("https://example.com", rendered=True)
        assert p1 != p2

    def test_different_urls_different_paths(self):
        p1 = _page_path("https://a.com", rendered=False)
        p2 = _page_path("https://b.com", rendered=False)
        assert p1 != p2

    def test_path_under_cache_dir(self):
        p = _page_path("https://example.com", rendered=False)
        assert "cache" in str(p)
        assert "pages" in str(p)
        assert str(p).endswith(".txt")


class TestExtractionPath:
    def test_prompt_change_invalidates(self):
        p1 = _extraction_path("prompt v1", "schema", "text")
        p2 = _extraction_path("prompt v2", "schema", "text")
        assert p1 != p2

    def test_schema_change_invalidates(self):
        p1 = _extraction_path("prompt", "schema v1", "text")
        p2 = _extraction_path("prompt", "schema v2", "text")
        assert p1 != p2

    def test_same_inputs_same_path(self):
        p1 = _extraction_path("prompt", "schema", "text")
        p2 = _extraction_path("prompt", "schema", "text")
        assert p1 == p2

    def test_path_is_json(self):
        p = _extraction_path("prompt", "schema", "text")
        assert str(p).endswith(".json")


class TestPageCacheRoundtrip:
    def test_set_and_get(self, tmp_path, monkeypatch):
        import cache
        monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")
        monkeypatch.setattr(cache, "_enabled", True)

        set_page("https://example.com", rendered=False, text="spec content")
        result = get_page("https://example.com", rendered=False)
        assert result == "spec content"

    def test_miss_returns_none(self, tmp_path, monkeypatch):
        import cache
        monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")
        monkeypatch.setattr(cache, "_enabled", True)

        assert get_page("https://missing.com", rendered=False) is None

    def test_disabled_cache_returns_none(self, tmp_path, monkeypatch):
        import cache
        monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")
        monkeypatch.setattr(cache, "_enabled", True)

        set_page("https://example.com", rendered=False, text="content")
        monkeypatch.setattr(cache, "_enabled", False)
        assert get_page("https://example.com", rendered=False) is None

    def test_empty_text_not_cached(self, tmp_path, monkeypatch):
        import cache
        monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")
        monkeypatch.setattr(cache, "_enabled", True)

        set_page("https://example.com", rendered=False, text="")
        assert get_page("https://example.com", rendered=False) is None
