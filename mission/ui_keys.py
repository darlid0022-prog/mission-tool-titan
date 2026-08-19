"""Single source of truth for shared `st.session_state` key names.

A neutral module (no Streamlit import, no visual component, no business
logic) so both a page (`pages/mission_setup.py`) and a presentation adapter
(`mission/ui_presentation.py`) can import the same key without importing
each other - avoiding the circular import a page-to-adapter or
adapter-to-page dependency would create.

Every value here is a session_state key string only. Changing a value would
change the serialized session_state key and must not be done without a
migration - see mission/ui_state_migration.py for the existing precedent.
"""

from __future__ import annotations

LAST_VALID_MISSION_BUNDLE_STATE_KEY = "mission_last_valid_bundle_v030"
