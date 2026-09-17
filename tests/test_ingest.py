"""PR URL parsing."""
import pytest

from patchcourt.ingest import parse_pr_url


def test_full_url():
    assert parse_pr_url("https://github.com/octoorg/octorepo/pull/42") == ("octoorg", "octorepo", 42)


def test_trailing_slash():
    assert parse_pr_url("https://github.com/o/r/pull/7/") == ("o", "r", 7)


def test_url_inside_text():
    assert parse_pr_url("see https://github.com/a/b/pull/9 thanks") == ("a", "b", 9)


def test_invalid_url():
    with pytest.raises(ValueError):
        parse_pr_url("https://example.com/not-a-pr")