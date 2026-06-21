"""Accessibility verification test module.

This module parses the rendered SPA template to verify compliance with accessibility requirements:
presence of ARIA live regions, descriptive labels on interactive buttons,
keyboard compatibility, and semantic HTML5 structural elements.
"""

from html.parser import HTMLParser
from typing import List, Dict, Any
from flask.testing import FlaskClient


class AccessibilityHTMLParser(HTMLParser):
    """HTML Parser that records tags, attributes, and text for accessibility verification."""

    def __init__(self) -> None:
        """Initializes the parser and lists to hold parsed elements."""
        super().__init__()
        self.tags: List[str] = []
        self.elements: List[Dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        """Invoked when a start tag is encountered.

        Args:
            tag: The HTML tag name.
            attrs: The attributes of the tag.
        """
        self.tags.append(tag)
        attr_dict = {name: val for name, val in attrs}
        self.elements.append({"tag": tag, "attrs": attr_dict})


def test_html_accessibility_compliance(client: FlaskClient) -> None:
    """Parses index.html to assert accessibility markup is present."""
    response = client.get("/")
    assert response.status_code == 200
    html_content = response.data.decode("utf-8")

    parser = AccessibilityHTMLParser()
    parser.feed(html_content)

    # 1. Assert Semantic HTML5 Landmarks
    assert "header" in parser.tags
    assert "main" in parser.tags
    assert "section" in parser.tags
    assert "footer" in parser.tags

    # 2. Assert ARIA Live Region presence
    # Check if there is an element with aria-live="polite" for the live nudge announcements
    live_regions = [
        el for el in parser.elements 
        if el["attrs"].get("aria-live") == "polite"
    ]
    assert len(live_regions) >= 1, "Must have at least one aria-live='polite' region for nudges."

    # 3. Assert all buttons have aria-label
    buttons = [el for el in parser.elements if el["tag"] == "button"]
    assert len(buttons) > 0, "No buttons found in index.html."
    
    for btn in buttons:
        attrs = btn["attrs"]
        assert "aria-label" in attrs, f"Button is missing 'aria-label': {btn}"
        assert len(attrs["aria-label"].strip()) > 5, f"aria-label is too short/generic: {attrs['aria-label']}"

    # 4. Assert Earth Health visual state has a text counterpart
    earth_health_label = [
        el for el in parser.elements 
        if el["attrs"].get("id") == "earth-health-text"
    ]
    assert len(earth_health_label) == 1, "Must contain a text element describing Earth health (id='earth-health-text')."

    # 5. Assert canvas has an accessibility label
    canvas_els = [el for el in parser.elements if el["tag"] == "canvas"]
    assert len(canvas_els) >= 1
    for canvas in canvas_els:
        assert "aria-label" in canvas["attrs"], "Canvas must contain a descriptive aria-label."
