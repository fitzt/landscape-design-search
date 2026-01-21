from .standard import StandardSearch
from .consultation import ConsultationSearch
from ..config import PROJECT_SLUG

class StrategyCoordinator:
    def __init__(self):
        self._standard = None
        self._consultation = None

    def get_strategy(self, project_slug: str = None):
        # Prioritize explicit argument, then global config
        target_slug = project_slug if project_slug else PROJECT_SLUG
        
        if target_slug == 'leahy':
            if not self._consultation:
                self._consultation = ConsultationSearch()
            return self._consultation
        else:
            if not self._standard:
                self._standard = StandardSearch()
            return self._standard

    def search(self, *args, **kwargs):
        # Extract project_slug from positional (index 4) or keyword
        slug = kwargs.get('project_slug') or (args[4] if len(args) > 4 else None)
        strategy = self.get_strategy(slug)
        return strategy.search(*args, **kwargs)

    def search_by_image(self, *args, **kwargs):
        slug = kwargs.get('project_slug') or (args[2] if len(args) > 2 else None)
        strategy = self.get_strategy(slug)
        return strategy.search_by_image(*args, **kwargs)

    def search_by_object(self, *args, **kwargs):
        slug = kwargs.get('project_slug') or (args[2] if len(args) > 2 else None)
        strategy = self.get_strategy(slug)
        return strategy.search_by_object(*args, **kwargs)

    def analyze_board(self, *args, **kwargs):
        slug = kwargs.get('project_slug') or (args[1] if len(args) > 1 else None)
        strategy = self.get_strategy(slug)
        return strategy.analyze_board(*args, **kwargs)
