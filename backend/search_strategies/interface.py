from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class SearchInterface(ABC):
    @abstractmethod
    def search(self, 
               query: str, 
               top_k: int = 50, 
               favorites_only: bool = False, 
               folder: Optional[str] = None, 
               project_slug: Optional[str] = None) -> List[Dict[Any, Any]]:
        """
        Standard text-to-image or text-to-container search.
        """
        pass

    @abstractmethod
    def search_by_image(self, 
                        image_id: int, 
                        top_k: int = 50) -> List[Dict[Any, Any]]:
        """
        Find similar images based on an anchor image.
        """
        pass

    @abstractmethod
    def search_by_object(self, 
                         object_id: str, 
                         top_k: int = 50) -> List[Dict[Any, Any]]:
        """
        Find images containing similar objects.
        """
        pass

    @abstractmethod
    def analyze_board(self, 
                      image_ids: List[int]) -> Dict[str, Any]:
        """
        Composite analysis of a collection of images.
        """
        pass
