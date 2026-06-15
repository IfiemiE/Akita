
"""
================================================================================
AKITA DIALECT DOCUMENTATION PLATFORM — PERMISSIONS MODULE
================================================================================
Date: 2026-05-20
Governance: Peer review (triple approval), role hierarchy, community tracking,
            elevation control, same-level deactivation protection
"""

from rest_framework import permissions
from apps.identity.users.models import UserRole


# =============================================================================
# BASE PERMISSIONS
# =============================================================================

class IsAnonymousReadOnly(permissions.BasePermission):
    """
    Allow read access to anyone (including anonymous), write only to authenticated.
    Used for: documentation/, pedagogy/ public endpoints.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class IsAuthenticated(permissions.BasePermission):
    """Require authentication for any access."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


# =============================================================================
# ROLE-BASED PERMISSIONS
# =============================================================================

class IsSuperuser(permissions.BasePermission):
    """Superuser only."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == UserRole.SUPERUSER
        )


class IsAdminOrAbove(permissions.BasePermission):
    """Admin or Superuser."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [UserRole.SUPERUSER, UserRole.ADMIN]
        )


class IsEditorOrAbove(permissions.BasePermission):
    """Editor, Admin, or Superuser."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [
                UserRole.SUPERUSER, UserRole.ADMIN, UserRole.EDITOR
            ]
        )


class IsContributor(permissions.BasePermission):
    """Any authenticated contributor or above."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [
                UserRole.SUPERUSER, UserRole.ADMIN,
                UserRole.EDITOR, UserRole.CONTRIBUTOR
            ]
        )


# =============================================================================
# ACTION-BASED PERMISSIONS
# =============================================================================

class IsRegistrar(permissions.BasePermission):
    """
    Can register new contributors after physical identification.
    Editors, Admins, and Superusers.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.can_register_users()
        )


class CanElevateToEditor(permissions.BasePermission):
    """
    Only Admin and Superuser can elevate a contributor to Editor.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.can_elevate_to_editor()
        )


# =============================================================================
# OBJECT-LEVEL PERMISSIONS
# =============================================================================

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level: owner can edit own content, others read-only.
    Used for: contributors editing their own uploads.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, 'created_by', None) == request.user


class CanManageTargetUser(permissions.BasePermission):
    """
    Object-level: can deactivate/censor target user.

    RULES:
    - Higher-level contributors can deactivate lower levels
    - Same-level deactivation is BLOCKED (returns False)
    - Superusers can deactivate other superusers (exception)
    - Admins cannot deactivate superusers
    - Contributors can only deactivate lower-level contributors
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.can_manage_user(obj)


class CannotSelfApprove(permissions.BasePermission):
    """
    Object-level: prevents reviewers from approving their own uploads.
    Enforced on all content review endpoints.
    """
    def has_object_permission(self, request, view, obj):
        # obj is the content item (LexicalEntry, MediaScript, etc.)
        # Check if the user is the creator of the content
        creator = getattr(obj, 'created_by', None)
        if creator is None:
            # Fallback for PendingSubmission
            creator = getattr(obj, 'submitted_by', None)
        if creator == request.user:
            return False
        return True


class HasNotReviewedYet(permissions.BasePermission):
    """
    Object-level: prevents duplicate reviews by the same user.
    Each reviewer can only approve once per submission.
    """
    def has_object_permission(self, request, view, obj):
        from apps.governance.workflow.models import ContentApproval

        # Get the submission ID — obj could be content or PendingSubmission
        submission = getattr(obj, 'pending_submission', None)
        if submission is None and hasattr(obj, 'submissions'):
            # obj is a PendingSubmission
            submission = obj

        if submission is None:
            # For direct content objects, check if there's a related submission
            return True  # Allow if no submission system is in place yet

        return not ContentApproval.objects.filter(
            submission=submission,
            reviewer=request.user
        ).exists()


class IsAssignedReviewer(permissions.BasePermission):
    """
    Object-level: editor must be assigned to this submission.
    Used for: restricting review to assigned moderators.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # Admins and superusers bypass assignment
        if request.user.role in [UserRole.SUPERUSER, UserRole.ADMIN]:
            return True
        assigned = getattr(obj, 'assigned_to', None)
        return assigned == request.user


# =============================================================================
# COMPOSITE PERMISSIONS (for specific endpoints)
# =============================================================================

class CanReviewContent(permissions.BasePermission):
    """
    Composite permission for content review endpoints.
    Requires: Editor+, not the owner, hasn't reviewed yet.
    """
    def has_permission(self, request, view):
        return IsEditorOrAbove().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        return (
            CannotSelfApprove().has_object_permission(request, view, obj) and
            HasNotReviewedYet().has_object_permission(request, view, obj)
        )


class CanDeactivateUser(permissions.BasePermission):
    """
    Composite permission for user deactivation.
    Requires: authenticated + can_manage_user passes.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return CanManageTargetUser().has_object_permission(request, view, obj)


# =============================================================================
# THROTTLING PERMISSIONS (rate limiting by role)
# =============================================================================

class AnonymousRateThrottle:
    """Rate limit for anonymous users: 100 requests/hour."""
    rate = '100/hour'


class ContributorRateThrottle:
    """Rate limit for contributors: 1000 requests/hour."""
    rate = '1000/hour'


class EditorRateThrottle:
    """Rate limit for editors: 5000 requests/hour."""
    rate = '5000/hour'


class AdminRateThrottle:
    """Unlimited for admins and superusers."""
    rate = None  # No limit


# =============================================================================
# PERMISSION HELPERS (non-DRF, for use in views/signals)
# =============================================================================

def get_user_role_level(role):
    """
    Return numeric privilege level for role comparison.
    Higher number = more privilege.
    """
    levels = {
        UserRole.CONTRIBUTOR: 1,
        UserRole.EDITOR: 2,
        UserRole.ADMIN: 3,
        UserRole.SUPERUSER: 4,
    }
    return levels.get(role, 0)


def can_user_review_content(user, content_obj):
    """
    Standalone check: can this user review this content?
    Returns (bool, str) tuple: (allowed, reason)
    """
    if not user or not user.is_authenticated:
        return False, "Authentication required."

    if user.role not in [UserRole.SUPERUSER, UserRole.ADMIN, UserRole.EDITOR]:
        return False, "Only Editors and above can review."

    creator = getattr(content_obj, 'created_by', None)
    if creator is None:
        creator = getattr(content_obj, 'uploaded_by', None)
    if creator is None:
        creator = getattr(content_obj, 'submitted_by', None)

    if creator == user:
        return False, "Cannot approve your own upload."

    from apps.governance.workflow.models import ContentApproval, PendingSubmission

    # Find related submission
    try:
        submission = PendingSubmission.objects.get(
            content_type__model=content_obj._meta.model_name,
            object_id=content_obj.id
        )
        if ContentApproval.objects.filter(submission=submission, reviewer=user).exists():
            return False, "You have already reviewed this submission."
    except PendingSubmission.DoesNotExist:
        pass

    return True, "Eligible to review."


def check_same_level_deactivation(requester, target):
    """
    Check if same-level deactivation is attempted.
    Returns (bool, str): (blocked, reason)
    """
    if requester.role == UserRole.SUPERUSER and target.role == UserRole.SUPERUSER:
        return False, "Superuser can deactivate another superuser."

    if requester.contributor_level == target.contributor_level:
        return True, "Cannot deactivate a same-level contributor."

    if requester.contributor_level < target.contributor_level:
        return True, "Cannot deactivate a higher-level contributor."

    return False, "Deactivation allowed."


# =============================================================================
# PERMISSION SUMMARY
# =============================================================================
"""
PERMISSION MATRIX:
┌─────────────────────────────┬───────────┬──────────┬─────────┬───────────┬──────────┐
│ Permission                  │ Anonymous │ Contributor│ Editor │ Admin    │ Superuser│
├─────────────────────────────┼───────────┼──────────┼─────────┼───────────┼──────────┤
│ IsAnonymousReadOnly (GET)   │ ✓         │ ✓        │ ✓       │ ✓         │ ✓        │
│ IsAnonymousReadOnly (POST)  │ ✗         │ ✓        │ ✓       │ ✓         │ ✓        │
│ IsContributor               │ ✗         │ ✓        │ ✓       │ ✓         │ ✓        │
│ IsEditorOrAbove             │ ✗         │ ✗        │ ✓       │ ✓         │ ✓        │
│ IsAdminOrAbove              │ ✗         │ ✗        │ ✗       │ ✓         │ ✓        │
│ IsSuperuser                 │ ✗         │ ✗        │ ✗       │ ✗         │ ✓        │
│ IsRegistrar                 │ ✗         │ ✗        │ ✓       │ ✓         │ ✓        │
│ CanElevateToEditor          │ ✗         │ ✗        │ ✗       │ ✓         │ ✓        │
│ CanManageTargetUser*        │ ✗         │ level    │ level   │ ✓         │ ✓        │
│ CannotSelfApprove           │ N/A       │ N/A      │ blocks  │ blocks    │ blocks   │
│ HasNotReviewedYet           │ N/A       │ N/A      │ checks  │ checks    │ checks   │
│ IsAssignedReviewer          │ ✗         │ ✗        │ ✓**     │ ✓         │ ✓        │
└─────────────────────────────┴───────────┴──────────┴─────────┴───────────┴──────────┘

* CanManageTargetUser: Higher level can deactivate lower. Same-level blocked.
  Exception: Superuser can deactivate another superuser.
** IsAssignedReviewer: Editors bypass if Admin+. Editors must be assigned.
"""