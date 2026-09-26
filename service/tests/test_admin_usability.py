from pathlib import Path


ADMIN_HTML = Path(__file__).resolve().parents[1] / "src" / "ncpc_service" / "admin.html"


def _html() -> str:
    return ADMIN_HTML.read_text(encoding="utf-8")


def test_plain_language_navigation_and_pages_are_present() -> None:
    html = _html()
    for label in (
        "Overview",
        "Products",
        "Needs Review",
        "Suggested Changes",
        "Possible Duplicates",
        "Publish Catalogue",
        "Catalogue Progress",
        "Connections",
    ):
        assert label in html


def test_help_language_system_is_implemented() -> None:
    html = _html()
    assert 'class="help-icon"' in html
    assert 'class="attention-icon"' in html
    assert 'class="page-help"' in html
    assert "HELP_CONTENT" in html
    assert "function openHelp" in html
    assert 'id="help-dialog"' in html


def test_technical_details_are_progressively_disclosed() -> None:
    html = _html()
    assert "Technical details" in html
    assert 'class="technical-details"' in html
    assert 'class="local-setup"' in html
    assert "Product option ID" in html


def test_accessibility_focus_styles_are_explicit() -> None:
    html = _html()
    assert ":focus-visible" in html
    assert 'aria-label="What is a barcode?"' in html
    assert 'aria-labelledby="help-dialog-title"' in html


def test_old_engineering_first_navigation_labels_are_not_primary_nav() -> None:
    html = _html()
    nav_start = html.index('<nav id="nav"')
    nav_end = html.index("</nav>", nav_start)
    nav = html[nav_start:nav_end]
    assert "Products &amp; Resolver" not in nav
    assert ">Reviews<" not in nav
    assert ">Submissions<" not in nav
    assert ">Duplicates<" not in nav
    assert ">Publication<" not in nav
    assert "Catalogue Coverage" not in nav
    assert "Integrations" not in nav


def test_shop_operational_facts_are_explicitly_excluded_from_publish_copy() -> None:
    html = _html()
    assert "Shop prices, stock, availability, sales and other business information are never part of this catalogue update." in html


def test_local_access_is_exchanged_for_a_session_before_admin_requests() -> None:
    html = _html()
    assert "const authenticated=()=>localAdminSession;" in html
    assert "headers:{'Content-Type':'application/json'}" in html
    assert "Authorization:'Bearer '+value('token'),'Content-Type'" not in html
    assert "localAdminSession=true;$('token').value='';updateAuthState()" in html


def test_product_search_uses_the_catalogue_api_result_limit() -> None:
    html = _html()
    search_start = html.rindex("searchProducts=async function")
    search_end = html.index("updateAuthState();refreshDashboard();", search_start)
    assert "new URLSearchParams({limit:'50'})" in html[search_start:search_end]
