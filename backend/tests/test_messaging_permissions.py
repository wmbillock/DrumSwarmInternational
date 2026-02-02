"""Tests for messaging permission checks."""

from backend.services.messaging_permissions import MessagingPermissions


def test_mark_thread_complete_admin_allowed():
    assert MessagingPermissions.can_mark_thread_complete(
        user_role="admin",
        thread_originator_role="executive_director",
        is_originator=False,
    )


def test_mark_thread_complete_originator_allowed():
    assert MessagingPermissions.can_mark_thread_complete(
        user_role="executive_director",
        thread_originator_role="executive_director",
        is_originator=True,
    )


def test_mark_thread_complete_non_originator_denied():
    assert not MessagingPermissions.can_mark_thread_complete(
        user_role="caption_head",
        thread_originator_role="executive_director",
        is_originator=False,
    )
