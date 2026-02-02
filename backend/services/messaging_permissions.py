"""Role-based permission checks for messaging system."""

from enum import Enum


class UserRole(str, Enum):
    """User roles in the system."""

    ADMIN = "admin"
    EXECUTIVE_DIRECTOR = "executive_director"
    PROGRAM_COORDINATOR = "program_coordinator"
    CAPTION_HEAD = "caption_head"
    TECH = "tech"
    MUSIC_WRITER = "music_writer"
    PERFORMER = "performer"


class MessagingPermissions:
    """Permission checks for messaging operations."""

    @staticmethod
    def can_create_thread(user_role: str) -> bool:
        """Check if user can create a messaging thread.

        ✅ Executive Directors
        ✅ Program Coordinators
        ❌ Caption Heads and Techs (must route through ED/PC)
        ❌ Other agents
        """
        role = UserRole(user_role) if isinstance(user_role, str) else user_role
        return role in [UserRole.EXECUTIVE_DIRECTOR, UserRole.PROGRAM_COORDINATOR]

    @staticmethod
    def can_mark_thread_complete(
        user_role: str, thread_originator_role: str, is_originator: bool
    ) -> bool:
        """Check if user can mark a thread complete.

        ✅ Admin can mark complete
        ✅ Original sender (ED/PC) can mark complete if they are the actor
        ❌ Other agents cannot mark threads complete

        Args:
            user_role: The role of the user attempting the action
            thread_originator_role: The role of the thread's originator
            is_originator: Whether the user is the thread originator
        """
        user = UserRole(user_role) if isinstance(user_role, str) else user_role
        originator = (
            UserRole(thread_originator_role)
            if isinstance(thread_originator_role, str)
            else thread_originator_role
        )

        # Admin has primary authority
        if user == UserRole.ADMIN:
            return True

        # Originator (ED/PC) can mark their own thread complete
        if is_originator and originator in [UserRole.EXECUTIVE_DIRECTOR, UserRole.PROGRAM_COORDINATOR]:
            return True

        return False

    @staticmethod
    def can_bulk_archive_threads(user_role: str) -> bool:
        """Check if user can bulk-archive threads.

        ✅ Admin role only
        ❌ Agents cannot archive
        """
        role = UserRole(user_role) if isinstance(user_role, str) else user_role
        return role == UserRole.ADMIN

    @staticmethod
    def can_search_archive(user_role: str) -> bool:
        """Check if user can search archived threads.

        ✅ Admin users — full access
        ✅ Executive Directors — read-only access
        ❌ Other agents cannot search archive
        """
        role = UserRole(user_role) if isinstance(user_role, str) else user_role
        return role in [UserRole.ADMIN, UserRole.EXECUTIVE_DIRECTOR]

    @staticmethod
    def can_add_message_to_thread(user_role: str, thread_status: str) -> bool:
        """Check if user can add a message to a thread.

        Any user/agent with proper role can add messages to active (pending) threads.
        Completed threads remain readable but are not actively messaged.
        """
        # For now, allow any authenticated user to add messages
        # In production, could restrict by thread visibility
        return True
