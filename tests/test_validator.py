from validator import (
    check_content, looks_like_error_page, has_spec_content,
    MIN_CONTENT_LENGTH, MIN_SPEC_KEYWORDS,
)


class TestLooksLikeErrorPage:
    def test_detects_403(self):
        assert looks_like_error_page("403 Forbidden") == "403 forbidden"

    def test_detects_access_denied(self):
        assert looks_like_error_page("Access Denied by WAF") == "access denied"

    def test_detects_javascript_gate(self):
        assert looks_like_error_page("Please enable JavaScript to continue") == "enable javascript"

    def test_detects_404(self):
        assert looks_like_error_page("404 Not Found") == "404 not found"

    def test_clean_page_returns_none(self):
        assert looks_like_error_page("ASUS ROG STRIX Z790-E Specifications") is None

    def test_case_insensitive(self):
        assert looks_like_error_page("ACCESS DENIED") == "access denied"


class TestHasSpecContent:
    def test_real_spec_text(self):
        text = (
            "Socket LGA1700, Intel Z790 chipset, DDR5 memory, "
            "PCIe 5.0 x16, 4x M.2 slots, USB 3.2 Gen2"
        )
        assert has_spec_content(text) is True

    def test_no_spec_keywords(self):
        assert has_spec_content("Buy now! Great deals on electronics.") is False

    def test_exactly_threshold(self):
        keywords = ["socket", "chipset", "ddr"]
        assert len(keywords) == MIN_SPEC_KEYWORDS
        text = " ".join(keywords)
        assert has_spec_content(text) is True

    def test_below_threshold(self):
        text = "socket chipset"
        assert has_spec_content(text) is False


class TestCheckContent:
    def test_error_page(self):
        result = check_content("Access Denied" + " x" * 500)
        assert result is not None
        assert "Error page" in result

    def test_too_short(self):
        result = check_content("socket chipset ddr pcie usb")
        assert result is not None
        assert "Too little content" in result

    def test_no_spec_keywords(self):
        text = "a" * MIN_CONTENT_LENGTH + " no specs here"
        result = check_content(text)
        assert result is not None
        assert "No spec content" in result

    def test_valid_page(self):
        text = (
            "ASUS ROG STRIX Z790-E Gaming WiFi\n"
            "Socket LGA1700, Intel Z790 chipset, DDR5 memory, "
            "PCIe 5.0 x16, 4x M.2 slots, USB 3.2 Gen2, "
            "SATA III, ATX form factor, Audio codec, LAN 2.5G, "
            "BIOS flashback\n"
        ) * 10
        assert check_content(text) is None

    def test_whitespace_stripped(self):
        result = check_content("   \n\n   ")
        assert result is not None
