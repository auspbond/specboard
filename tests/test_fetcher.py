from fetcher import url_variants, _is_manufacturer_url, _relevance_score, _query_terms, _strip_html


class TestUrlVariants:
    def test_no_plus_in_path(self):
        url = "https://example.com/board/specs"
        assert url_variants(url) == [url]

    def test_plus_in_path_generates_variant(self):
        url = "https://example.com/ROG+STRIX+Z790/specs"
        variants = url_variants(url)
        assert len(variants) == 2
        assert variants[0] == url
        assert "%20" in variants[1]
        assert "+" not in variants[1].split("?")[0].split("//")[1]

    def test_plus_in_query_not_affected(self):
        url = "https://example.com/specs?q=board+name"
        variants = url_variants(url)
        assert len(variants) == 1


class TestIsManufacturerUrl:
    def test_asus(self):
        assert _is_manufacturer_url("https://www.asus.com/motherboards/rog-strix/") is True

    def test_msi(self):
        assert _is_manufacturer_url("https://www.msi.com/Motherboard/MEG-Z790") is True

    def test_gigabyte(self):
        assert _is_manufacturer_url("https://www.gigabyte.com/Motherboard/X870") is True

    def test_asrock(self):
        assert _is_manufacturer_url("https://www.asrock.com/mb/") is True

    def test_review_site(self):
        assert _is_manufacturer_url("https://www.tomshardware.com/reviews/board") is False

    def test_newegg(self):
        assert _is_manufacturer_url("https://www.newegg.com/asus-board") is False


class TestQueryTerms:
    def test_basic_split(self):
        terms = _query_terms("ASUS ROG STRIX Z790-E")
        assert "asus" in terms
        assert "rog" in terms
        assert "strix" in terms
        assert "z790" in terms

    def test_short_terms_filtered(self):
        terms = _query_terms("ASUS X E Gaming")
        assert "asus" in terms
        assert "gaming" in terms
        assert "x" not in terms
        assert "e" not in terms

    def test_hyphen_split(self):
        terms = _query_terms("Z790-E")
        assert "z790" in terms


class TestRelevanceScore:
    def test_url_match_worth_2(self):
        score = _relevance_score(["z790"], "https://example.com/z790/specs", "Other Board")
        assert score == 2

    def test_title_match_worth_1(self):
        score = _relevance_score(["z790"], "https://example.com/board", "Z790 Board Review")
        assert score == 1

    def test_both_match(self):
        score = _relevance_score(["z790"], "https://example.com/z790", "Z790 Board")
        assert score == 3

    def test_no_match(self):
        score = _relevance_score(["z790"], "https://example.com/board", "Some Board")
        assert score == 0

    def test_multiple_terms(self):
        terms = ["asus", "z790", "strix"]
        score = _relevance_score(
            terms,
            "https://asus.com/z790-strix/",
            "ASUS ROG STRIX Z790"
        )
        assert score == 9  # 3 url matches * 2 + 3 title matches * 1


class TestStripHtml:
    def test_removes_scripts(self):
        html = "<html><body><script>var x=1;</script><p>Specs here</p></body></html>"
        assert "var x" not in _strip_html(html)
        assert "Specs here" in _strip_html(html)

    def test_removes_nav(self):
        html = "<nav>Menu items</nav><div>Real content</div>"
        result = _strip_html(html)
        assert "Menu items" not in result
        assert "Real content" in result

    def test_removes_style(self):
        html = "<style>.foo{color:red}</style><p>Content</p>"
        result = _strip_html(html)
        assert "color:red" not in result
        assert "Content" in result

    def test_plain_text_passthrough(self):
        html = "<p>Just text</p>"
        assert "Just text" in _strip_html(html)
