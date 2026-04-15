"""Tests for retryctl.labels."""
import pytest

from retryctl.labels import LabelError, LabelSet, parse_labels


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ls(*pairs: str) -> LabelSet:
    return parse_labels(pairs)


# ---------------------------------------------------------------------------
# LabelSet.add
# ---------------------------------------------------------------------------

class TestLabelSetAdd:
    def test_adds_valid_label(self):
        ls = LabelSet()
        ls.add('env', 'production')
        assert ls.get('env') == 'production'

    def test_overwrites_existing_key(self):
        ls = LabelSet()
        ls.add('env', 'staging')
        ls.add('env', 'production')
        assert ls.get('env') == 'production'

    def test_invalid_key_raises(self):
        ls = LabelSet()
        with pytest.raises(LabelError, match='Invalid label key'):
            ls.add('bad key!', 'value')

    def test_key_starting_with_digit_raises(self):
        ls = LabelSet()
        with pytest.raises(LabelError):
            ls.add('1bad', 'value')

    def test_value_too_long_raises(self):
        ls = LabelSet()
        with pytest.raises(LabelError, match='exceeds maximum length'):
            ls.add('key', 'x' * 257)

    def test_value_at_max_length_is_ok(self):
        ls = LabelSet()
        ls.add('key', 'x' * 256)  # should not raise

    def test_dots_and_dashes_in_key_are_valid(self):
        ls = LabelSet()
        ls.add('app.name-v2', 'svc')
        assert ls.get('app.name-v2') == 'svc'


# ---------------------------------------------------------------------------
# LabelSet.remove / __contains__ / __len__
# ---------------------------------------------------------------------------

class TestLabelSetRemove:
    def test_removes_existing_key(self):
        ls = _ls('a=1')
        ls.remove('a')
        assert 'a' not in ls

    def test_remove_missing_key_is_noop(self):
        ls = LabelSet()
        ls.remove('ghost')  # must not raise

    def test_len_reflects_count(self):
        ls = _ls('a=1', 'b=2')
        assert len(ls) == 2
        ls.remove('a')
        assert len(ls) == 1


# ---------------------------------------------------------------------------
# LabelSet.as_dict
# ---------------------------------------------------------------------------

class TestLabelSetAsDict:
    def test_returns_copy(self):
        ls = _ls('x=10')
        d = ls.as_dict()
        d['x'] = 'mutated'
        assert ls.get('x') == '10'

    def test_contains_all_labels(self):
        ls = _ls('a=1', 'b=2', 'c=3')
        assert ls.as_dict() == {'a': '1', 'b': '2', 'c': '3'}


# ---------------------------------------------------------------------------
# parse_labels
# ---------------------------------------------------------------------------

class TestParseLabels:
    def test_parses_single_pair(self):
        ls = parse_labels(['env=prod'])
        assert ls.get('env') == 'prod'

    def test_value_may_contain_equals(self):
        ls = parse_labels(['token=abc=def'])
        assert ls.get('token') == 'abc=def'

    def test_missing_equals_raises(self):
        with pytest.raises(LabelError, match='key=value'):
            parse_labels(['noequals'])

    def test_empty_iterable_returns_empty_labelset(self):
        ls = parse_labels([])
        assert len(ls) == 0

    def test_invalid_key_propagates(self):
        with pytest.raises(LabelError):
            parse_labels(['bad key=val'])
