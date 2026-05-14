# The Backend/API side:
### -- django/django REST framework

#### --> Apps: core, culture, language and users

## Core
Shared utilities and general resources

## users 
user accounts, roles, approvals, permissions and contributions

## culture
Cultural content (festivals, foods, dances, folktales, crafts, music, beliefs, practices)

## language
Orthography, Dictionary, Teaching/Learning materials, Grammar

## Proposed Project Tree:

akita/
├── .git/                          # Git repository root (at akita/ level)
├── .gitignore
├── README.md
├── LICENSE
│
├── api/                           # Django REST Framework backend (venv root)
│   ├── Pipfile
│   ├── Pipfile.lock
│   ├── .env
│   ├── .env.example
│   ├── manage.py
│   ├── pytest.ini
│   ├── setup.cfg
│   ├── pyproject.toml
│   │
│   ├── config/                    # Django project configuration
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   ├── production.py
│   │   │   └── test.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   ├── asgi.py
│   │   └── celery.py
│   │
│   ├── apps/                      # Domain-driven applications (5 domains, 11 apps)
│   │   ├── __init__.py
│   │   │
│   │   ├── identity/              # ─── Domain: Identity & Access ───
│   │   │   └── users/             # App: AkitaUser, SpeakerVerification
│   │   │       ├── __init__.py
│   │   │       ├── models.py
│   │   │       ├── admin.py
│   │   │       ├── apps.py            # name='apps.identity.users'
│   │   │       ├── serializers.py
│   │   │       ├── views.py
│   │   │       ├── viewsets.py
│   │   │       ├── urls.py            # /api/v1/users/, /api/v1/speakers/
│   │   │       ├── permissions.py
│   │   │       ├── filters.py
│   │   │       ├── signals.py
│   │   │       ├── tasks.py
│   │   │       ├── tests/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── test_models.py
│   │   │       │   ├── test_api.py
│   │   │       │   ├── test_permissions.py
│   │   │       │   └── fixtures/
│   │   │       │       └── users.json
│   │   │       └── migrations/
│   │   │           └── __init__.py
│   │   │
│   │   ├── infrastructure/        # ─── Domain: Platform Infrastructure ───
│   │   │   └── core/              # App: MediaTag, Category, SiteSetting, Page
│   │   │       ├── __init__.py
│   │   │       ├── models.py
│   │   │       ├── admin.py
│   │   │       ├── apps.py            # name='apps.infrastructure.core'
│   │   │       ├── serializers.py
│   │   │       ├── views.py
│   │   │       ├── viewsets.py
│   │   │       ├── urls.py            # /api/v1/tags/, /api/v1/categories/
│   │   │       ├── permissions.py
│   │   │       ├── filters.py
│   │   │       ├── signals.py
│   │   │       ├── tasks.py
│   │   │       ├── tests/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── test_models.py
│   │   │       │   └── test_api.py
│   │   │       └── migrations/
│   │   │           └── __init__.py
│   │   │
│   │   ├── documentation/         # ─── Domain: Language Documentation ───
│   │   │   ├── lexicon/           # App: Dictionary, grammar, etymology
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py          # 25+ models (see list below)
│   │   │   │   ├── admin.py
│   │   │   │   ├── apps.py            # name='apps.documentation.lexicon'
│   │   │   │   ├── serializers.py
│   │   │   │   ├── views.py
│   │   │   │   ├── viewsets.py
│   │   │   │   ├── urls.py            # /api/v1/lexicon/, /api/v1/entries/
│   │   │   │   ├── permissions.py
│   │   │   │   ├── filters.py
│   │   │   │   ├── search_indexes.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── tests/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── test_models.py
│   │   │   │   │   ├── test_api.py
│   │   │   │   │   ├── test_search.py
│   │   │   │   │   └── fixtures/
│   │   │   │   │       ├── dialects.json
│   │   │   │   │       ├── orthography_systems.json
│   │   │   │   │       └── semantic_domains.json
│   │   │   │   └── migrations/
│   │   │   │       └── __init__.py
│   │   │   │
│   │   │   ├── media_annotations/ # App: Subtitled media, learner sessions
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py          # MediaScript, ScriptSegment, etc.
│   │   │   │   ├── admin.py
│   │   │   │   ├── apps.py            # name='apps.documentation.media_annotations'
│   │   │   │   ├── serializers.py
│   │   │   │   ├── views.py
│   │   │   │   ├── viewsets.py
│   │   │   │   ├── urls.py            # /api/v1/media-scripts/, /api/v1/sessions/
│   │   │   │   ├── permissions.py
│   │   │   │   ├── filters.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── tasks.py           # Transcoding, subtitle generation
│   │   │   │   ├── tests/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── test_models.py
│   │   │   │   │   └── test_api.py
│   │   │   │   └── migrations/
│   │   │   │       └── __init__.py
│   │   │   │
│   │   │   └── culture/           # App: Cultural documentation, events
│   │   │       ├── __init__.py
│   │   │       ├── models.py          # CulturalDomain, CulturalItem, etc.
│   │   │       ├── admin.py
│   │   │       ├── apps.py            # name='apps.documentation.culture'
│   │   │       ├── serializers.py
│   │   │       ├── views.py
│   │   │       ├── viewsets.py
│   │   │       ├── urls.py            # /api/v1/culture/, /api/v1/events/
│   │   │       ├── permissions.py
│   │   │       ├── permissions.py
│   │   │       ├── filters.py
│   │   │       ├── signals.py
│   │   │       ├── tasks.py
│   │   │       ├── tests/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── test_models.py
│   │   │       │   └── test_api.py
│   │   │       └── migrations/
│   │   │           └── __init__.py
│   │   │
│   │   ├── pedagogy/              # ─── Domain: Language Learning ───
│   │   │   ├── immersion/         # App: Listen-first curriculum tracks
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py          # ImmersionTrack, ImmersionItem, TrackItemOrder
│   │   │   │   ├── admin.py
│   │   │   │   ├── apps.py            # name='apps.pedagogy.immersion'
│   │   │   │   ├── serializers.py
│   │   │   │   ├── views.py
│   │   │   │   ├── viewsets.py
│   │   │   │   ├── urls.py            # /api/v1/immersion-tracks/
│   │   │   │   ├── permissions.py
│   │   │   │   ├── filters.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── tests/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── test_models.py
│   │   │   │   │   └── test_api.py
│   │   │   │   └── migrations/
│   │   │   │       └── __init__.py
│   │   │   │
│   │   │   ├── constructions/     # App: Grammar patterns, fixed expressions
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py          # ConstructionTopic, SentencePattern, etc.
│   │   │   │   ├── admin.py
│   │   │   │   ├── apps.py            # name='apps.pedagogy.constructions'
│   │   │   │   ├── serializers.py
│   │   │   │   ├── views.py
│   │   │   │   ├── viewsets.py
│   │   │   │   ├── urls.py            # /api/v1/constructions/
│   │   │   │   ├── permissions.py
│   │   │   │   ├── filters.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── tests/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── test_models.py
│   │   │   │   │   └── test_api.py
│   │   │   │   └── migrations/
│   │   │   │       └── __init__.py
│   │   │   │
│   │   │   ├── curriculum/        # App: Lessons and progress tracking
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py          # Curriculum, Lesson, LessonProgress
│   │   │   │   ├── admin.py
│   │   │   │   ├── apps.py            # name='apps.pedagogy.curriculum'
│   │   │   │   ├── serializers.py
│   │   │   │   ├── views.py
│   │   │   │   ├── viewsets.py
│   │   │   │   ├── urls.py            # /api/v1/curricula/, /api/v1/progress/
│   │   │   │   ├── permissions.py
│   │   │   │   ├── filters.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── tests/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── test_models.py
│   │   │   │   │   └── test_api.py
│   │   │   │   └── migrations/
│   │   │   │       └── __init__.py
│   │   │   │
│   │   │   ├── spaced_repetition/ # App: Flashcard SRS system
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py          # FlashcardDeck, Flashcard, ReviewLog
│   │   │   │   ├── admin.py
│   │   │   │   ├── apps.py            # name='apps.pedagogy.spaced_repetition'
│   │   │   │   ├── serializers.py
│   │   │   │   ├── views.py
│   │   │   │   ├── viewsets.py
│   │   │   │   ├── urls.py            # /api/v1/decks/, /api/v1/reviews/
│   │   │   │   ├── permissions.py
│   │   │   │   ├── filters.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── tasks.py           # Daily review reminders
│   │   │   │   ├── tests/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── test_models.py
│   │   │   │   │   └── test_api.py
│   │   │   │   └── migrations/
│   │   │   │       └── __init__.py
│   │   │   │
│   │   │   └── challenges/        # App: Gamification, borrowing, voting
│   │   │       ├── __init__.py
│   │   │       ├── models.py          # Challenge, BorrowingCandidate, CommunityVote, etc.
│   │   │       ├── admin.py
│   │   │       ├── apps.py            # name='apps.pedagogy.challenges'
│   │   │       ├── serializers.py
│   │   │       ├── views.py
│   │   │       ├── viewsets.py
│   │   │       ├── urls.py            # /api/v1/challenges/, /api/v1/borrowing/
│   │   │       ├── permissions.py
│   │   │       ├── filters.py
│   │   │       ├── signals.py         # Vote recalculation, badges
│   │   │       ├── tasks.py           # Leaderboard recalc, deadline reminders
│   │   │       ├── tests/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── test_models.py
│   │   │       │   └── test_api.py
│   │   │       └── migrations/
│   │   │           └── __init__.py
│   │   │
│   │   └── governance/            # ─── Domain: Editorial Workflow ───
│   │       └── workflow/          # App: Submission moderation, file review
│   │           ├── __init__.py
│   │           ├── models.py          # PendingSubmission, PendingFile
│   │           ├── admin.py
│   │           ├── apps.py            # name='apps.governance.workflow'
│   │           ├── serializers.py
│   │           ├── views.py
│   │           ├── viewsets.py
│   │           ├── urls.py            # /api/v1/submissions/, /api/v1/pending-files/
│   │           ├── permissions.py     # IsModerator, IsContentEditor
│   │           ├── filters.py         # Status filter, assigned-to filter
│   │           ├── signals.py         # Auto-assignment, notifications
│   │           ├── tasks.py           # Escalation reminders, stale alerts
│   │           ├── tests/
│   │           │   ├── __init__.py
│   │           │   ├── test_models.py
│   │           │   └── test_api.py
│   │           └── migrations/
│   │               └── __init__.py
│   │
│   ├── common/                    # Shared utilities across all domains
│   │   ├── __init__.py
│   │   ├── pagination.py
│   │   ├── permissions.py
│   │   ├── throttling.py
│   │   ├── exceptions.py
│   │   ├── mixins.py
│   │   ├── validators.py
│   │   ├── utils.py
│   │   ├── storage.py
│   │   └── constants.py
│   │
│   ├── fixtures/                  # Domain-organized initial data
│   │   ├── identity/
│   │   │   └── users.json
│   │   ├── documentation/
│   │   │   ├── dialects.json
│   │   │   ├── orthography_systems.json
│   │   │   ├── semantic_domains.json
│   │   │   └── parts_of_speech.json
│   │   ├── pedagogy/
│   │   │   └── challenge_types.json
│   │   └── governance/
│   │       └── workflow_stages.json
│   │
│   ├── scripts/                   # Domain-organized management scripts
│   │   ├── __init__.py
│   │   ├── identity/
│   │   │   └── invite_speakers.py
│   │   ├── documentation/
│   │   │   ├── import_lexicon.py
│   │   │   ├── import_media.py
│   │   │   ├── sync_orthography.py
│   │   │   └── rebuild_search.py
│   │   ├── pedagogy/
│   │   │   ├── seed_immersion.py
│   │   │   └── recalc_leaderboards.py
│   │   └── governance/
│   │       ├── process_submissions.py
│   │       └── generate_reports.py
│   │
│   ├── templates/                 # Domain-organized Django templates
│   │   ├── admin/
│   │   │   └── base_site.html     # Custom admin title/logo
│   │   └── email/
│   │       ├── identity/
│   │       │   ├── verification_email.html
│   │       │   └── verification_email.txt
│   │       ├── pedagogy/
│   │       │   ├── weekly_digest.html
│   │       │   └── weekly_digest.txt
│   │       └── governance/
│   │           ├── submission_assigned.html
│   │           └── submission_approved.html
│   │
│   ├── static/
│   │   └── admin/
│   │       └── css/
│   │           └── custom_admin.css
│   │
│   ├── media/                       # Domain-organized upload directories
│   │   ├── identity/
│   │   │   └── profiles/
│   │   ├── documentation/
│   │   │   ├── lexicon/
│   │   │   ├── media_annotations/
│   │   │   └── culture/
│   │   ├── pedagogy/
│   │   │   ├── immersion/
│   │   │   ├── curriculum/
│   │   │   ├── spaced_repetition/
│   │   │   └── challenges/
│   │   └── governance/
│   │       └── workflow/
│   │
│   ├── locale/
│   │   ├── en/
│   │   │   └── LC_MESSAGES/
│   │   │       └── django.po
│   │   └── ij/
│   │       └── LC_MESSAGES/
│   │           └── django.po
│   │
│   ├── docs/
│   │   ├── openapi.yaml
│   │   ├── authentication.md
│   │   ├── domains/
│   │   │   ├── identity.md
│   │   │   ├── infrastructure.md
│   │   │   ├── documentation.md
│   │   │   ├── pedagogy.md
│   │   │   └── governance.md
│   │   └── webhooks.md
│   │
│   └── logs/                        # gitignored
│       ├── django/
│       ├── celery/
│       └── gunicorn/
│
└── client/                          # React frontend (ignored per request)
    └── ...