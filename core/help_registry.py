"""
Central registry of help topic slugs used in templates.

When you add {% help_trigger "some-slug" %} to any template, add an entry
here so admins know what to fill in.
"""

REGISTERED_TOPICS = {
    'parts-overview': 'Job detail — Parts heading',
    'area-description': 'Area description'
}
