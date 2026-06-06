"""Database class assembled from storage mixins."""

from __future__ import annotations

from .database_schema_mixin import DatabaseSchemaMixin
from .database_tasks_mixin import DatabaseTasksMixin
from .database_projects_mixin import DatabaseProjectsMixin
from .database_project_properties_mixin import DatabaseProjectPropertiesMixin
from .database_maps_mixin import DatabaseMapsMixin
from .database_notes_ideas_mixin import DatabaseNotesIdeasMixin
from .database_objects_characters_mixin import DatabaseObjectsCharactersMixin
from .database_dossier_mixin import DatabaseDossierMixin
from .database_collections_mixin import DatabaseCollectionsMixin
from .database_purchases_mixin import DatabasePurchasesMixin
from .database_settings_cloud_mixin import DatabaseSettingsCloudMixin
from .database_concept_boards_mixin import DatabaseConceptBoardsMixin
from .database_context_links_mixin import DatabaseContextLinksMixin
from .database_entity_links_mixin import DatabaseEntityLinksMixin
from .database_core_mixin import DatabaseCoreMixin

class Database(
    DatabaseSchemaMixin,
    DatabaseTasksMixin,
    DatabaseProjectsMixin,
    DatabaseProjectPropertiesMixin,
    DatabaseMapsMixin,
    DatabaseNotesIdeasMixin,
    DatabaseObjectsCharactersMixin,
    DatabaseDossierMixin,
    DatabaseCollectionsMixin,
    DatabasePurchasesMixin,
    DatabaseSettingsCloudMixin,
    DatabaseConceptBoardsMixin,
    DatabaseContextLinksMixin,
    DatabaseEntityLinksMixin,
    DatabaseCoreMixin,
):
    """???????????????? ?? ?????????????????? ?????????? ???????????? ????????????????????."""

    pass

__all__ = ["Database"]
