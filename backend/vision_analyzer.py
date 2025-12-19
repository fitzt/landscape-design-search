"""
Vision Analysis Engine
Analyzes vision boards to extract themes, patterns, and actionable insights.
Uses pre-computed tags and CLIP embeddings for instant analysis.
"""

import numpy as np
from sklearn.cluster import KMeans
from collections import Counter
from typing import List, Dict, Any
import psycopg2.extras

from backend.db import get_db_connection
from backend.taxonomy import TAXONOMY, get_tag_label, get_tag_category, TAG_TO_CATEGORY
from backend.search import SearchEngine

class VisionAnalyzer:
    def __init__(self):
        self.search_engine = SearchEngine()
    
    def analyze_vision_board(self, image_ids: List[int]) -> Dict[str, Any]:
        """
        Comprehensive analysis of a vision board.
        
        Args:
            image_ids: List of image IDs in the vision board
            
        Returns:
            Dict with themes, top_elements, materials, insights, etc.
        """
        if not image_ids:
            return {"error": "No images provided"}
        
        # Fetch image data
        conn = get_db_connection()
        placeholders = ','.join(['%s'] * len(image_ids))
        
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(f"""
                SELECT id, tags, caption, style_scores, file_path
                FROM images 
                WHERE id IN ({placeholders})
            """, tuple(image_ids))
            images = [dict(row) for row in cur.fetchall()]
        conn.close()
        
        if not images:
            return {"error": "No images found"}
        
        # Extract all tags and scores
        all_tags = []
        tag_scores = {}
        
        for img in images:
            if img['tags']:
                for tag in img['tags']:
                    all_tags.append(tag)
                    # Accumulate scores
                    if img['style_scores'] and tag in img['style_scores']:
                        score = img['style_scores'][tag]
                        tag_scores[tag] = tag_scores.get(tag, []) + [score]
        
        # Aggregate tags
        tag_counts = Counter(all_tags)
        total_images = len(images)
        
        # Calculate weighted scores
        top_elements = []
        for tag, count in tag_counts.most_common(15):
            avg_score = np.mean(tag_scores.get(tag, [0.5]))
            percentage = (count / total_images) * 100
            
            top_elements.append({
                "tag": tag,
                "label": get_tag_label(tag),
                "category": get_tag_category(tag),
                "count": count,
                "percentage": round(percentage, 1),
                "confidence": round(avg_score, 2)
            })
        
        # Cluster into themes
        themes = self._cluster_themes(images, image_ids)
        
        # Extract category-specific insights
        materials = self._extract_category_tags(top_elements, "materials")
        planting_signals = self._extract_category_tags(top_elements, "planting_style")
        layout_preference = self._extract_category_tags(top_elements, "layout")
        maintenance_vibe = self._extract_category_tags(top_elements, "maintenance_level")
        
        # Generate unconscious patterns
        unconscious_patterns = self._generate_insights(top_elements, themes, total_images)
        
        # Generate sales brief
        sales_brief = self._generate_sales_brief(
            themes, top_elements, materials, planting_signals, 
            layout_preference, maintenance_vibe, unconscious_patterns
        )
        
        return {
            "total_images": total_images,
            "themes": themes,
            "top_elements": top_elements[:10],  # Top 10 for UI
            "materials": materials,
            "planting_signals": planting_signals,
            "layout_preference": layout_preference[0] if layout_preference else None,
            "maintenance_vibe": maintenance_vibe[0] if maintenance_vibe else None,
            "unconscious_patterns": unconscious_patterns,
            "sales_brief": sales_brief,
            "tag_diversity": len(set(all_tags)),
            "avg_tags_per_image": round(len(all_tags) / total_images, 1)
        }
    
    def _cluster_themes(self, images: List[Dict], image_ids: List[int], n_clusters: int = None) -> List[Dict]:
        """
        Cluster images into 2-5 design themes using CLIP embeddings.
        """
        if len(images) < 3:
            # Too few images to cluster meaningfully
            return [{
                "name": "Primary Style",
                "confidence": 1.0,
                "image_ids": image_ids,
                "top_tags": self._get_top_tags_for_images(images)
            }]
        
        # Auto-determine number of clusters
        if n_clusters is None:
            if len(images) < 6:
                n_clusters = 2
            elif len(images) < 12:
                n_clusters = 3
            else:
                n_clusters = min(5, len(images) // 4)
        
        try:
            # Load images and get embeddings
            from PIL import Image
            import os
            
            valid_images = []
            valid_ids = []
            
            for img in images:
                if os.path.exists(img['file_path']):
                    try:
                        pil_img = Image.open(img['file_path'])
                        valid_images.append(pil_img)
                        valid_ids.append(img['id'])
                    except:
                        continue
            
            if len(valid_images) < 3:
                # Fallback to tag-based grouping
                return self._tag_based_themes(images, image_ids)
            
            # Encode images
            embeddings = self.search_engine.model.encode(valid_images)
            
            # Cluster
            kmeans = KMeans(n_clusters=min(n_clusters, len(valid_images)), random_state=42)
            labels = kmeans.fit_predict(embeddings)
            
            # Build theme groups
            themes = []
            for cluster_id in range(n_clusters):
                cluster_indices = np.where(labels == cluster_id)[0]
                cluster_image_ids = [valid_ids[i] for i in cluster_indices]
                cluster_images = [images[image_ids.index(img_id)] for img_id in cluster_image_ids]
                
                # Get top tags for this cluster
                top_tags = self._get_top_tags_for_images(cluster_images)
                
                # Generate theme name from top tags
                theme_name = self._generate_theme_name(top_tags)
                
                # Calculate confidence (silhouette-like score)
                confidence = len(cluster_image_ids) / len(valid_images)
                
                themes.append({
                    "name": theme_name,
                    "confidence": round(confidence, 2),
                    "image_ids": cluster_image_ids,
                    "top_tags": top_tags[:5],
                    "image_count": len(cluster_image_ids)
                })
            
            # Sort by confidence
            themes.sort(key=lambda x: x['confidence'], reverse=True)
            return themes
            
        except Exception as e:
            print(f"Clustering error: {e}")
            # Fallback to tag-based themes
            return self._tag_based_themes(images, image_ids)
    
    def _tag_based_themes(self, images: List[Dict], image_ids: List[int]) -> List[Dict]:
        """Fallback: Create themes based on tag similarity."""
        # Group by dominant style tag
        style_groups = {}
        
        for img in images:
            if not img['tags']:
                continue
            
            # Find dominant style tag
            style_tag = None
            for tag in img['tags']:
                if get_tag_category(tag) == 'style':
                    style_tag = tag
                    break
            
            if style_tag:
                if style_tag not in style_groups:
                    style_groups[style_tag] = []
                style_groups[style_tag].append(img['id'])
        
        # Convert to themes
        themes = []
        for style_tag, img_ids in sorted(style_groups.items(), key=lambda x: len(x[1]), reverse=True):
            cluster_images = [img for img in images if img['id'] in img_ids]
            top_tags = self._get_top_tags_for_images(cluster_images)
            
            themes.append({
                "name": get_tag_label(style_tag),
                "confidence": round(len(img_ids) / len(images), 2),
                "image_ids": img_ids,
                "top_tags": top_tags[:5],
                "image_count": len(img_ids)
            })
        
        return themes[:3]  # Max 3 themes
    
    def _get_top_tags_for_images(self, images: List[Dict], limit: int = 5) -> List[str]:
        """Get most common tags across a set of images."""
        all_tags = []
        for img in images:
            if img['tags']:
                all_tags.extend(img['tags'])
        
        tag_counts = Counter(all_tags)
        return [tag for tag, _ in tag_counts.most_common(limit)]
    
    def _generate_theme_name(self, top_tags: List[str]) -> str:
        """Generate a descriptive theme name from top tags."""
        if not top_tags:
            return "Mixed Style"
        
        # Prioritize style and material tags
        style_tags = [tag for tag in top_tags if get_tag_category(tag) in ['style', 'materials', 'layout']]
        
        if len(style_tags) >= 2:
            return f"{get_tag_label(style_tags[0])} with {get_tag_label(style_tags[1])}"
        elif style_tags:
            return get_tag_label(style_tags[0])
        else:
            return f"{get_tag_label(top_tags[0])} Focus"
    
    def _extract_category_tags(self, top_elements: List[Dict], category: str) -> List[str]:
        """Extract tags from a specific category."""
        return [
            elem['label'] 
            for elem in top_elements 
            if elem['category'] == category
        ][:5]
    
    def _generate_insights(self, top_elements: List[Dict], themes: List[Dict], total_images: int) -> List[str]:
        """Generate unconscious pattern insights."""
        insights = []
        
        # Check for lighting preference
        lighting_tags = [e for e in top_elements if e['category'] == 'lighting']
        if lighting_tags and lighting_tags[0]['percentage'] > 40:
            insights.append(f"Strong preference for {lighting_tags[0]['label'].lower()} ({lighting_tags[0]['percentage']:.0f}% of selections)")
        
        # Check for hardscape dominance
        hardscape_tags = [e for e in top_elements if e['category'] == 'hardscape']
        if len(hardscape_tags) >= 3:
            insights.append("Gravitates toward structured hardscape elements")
        
        # Check for planting style
        planting_tags = [e for e in top_elements if e['category'] == 'planting_style']
        if planting_tags:
            insights.append(f"Planting preference: {planting_tags[0]['label'].lower()}")
        
        # Check for layout consistency
        layout_tags = [e for e in top_elements if e['category'] == 'layout']
        if layout_tags and layout_tags[0]['percentage'] > 50:
            insights.append(f"Consistent preference for {layout_tags[0]['label'].lower()} layouts")
        
        # Theme diversity
        if len(themes) >= 3:
            insights.append("Exploring multiple design directions")
        elif len(themes) == 1:
            insights.append("Highly focused design vision")
        
        return insights
    
    def _generate_sales_brief(self, themes, top_elements, materials, planting_signals, 
                              layout_preference, maintenance_vibe, unconscious_patterns) -> str:
        """Generate a sales-ready text brief."""
        lines = []
        
        lines.append("CLIENT DESIGN PROFILE")
        lines.append("=" * 60)
        lines.append("")
        
        # Themes
        if themes:
            lines.append("PRIMARY THEMES:")
            for theme in themes[:3]:
                lines.append(f"• {theme['name']} ({theme['confidence']*100:.0f}% of selections)")
            lines.append("")
        
        # Top elements
        if top_elements:
            lines.append("TOP DESIGN ELEMENTS:")
            for elem in top_elements[:8]:
                lines.append(f"• {elem['label']} ({elem['count']} images, {elem['percentage']:.0f}%)")
            lines.append("")
        
        # Materials
        if materials:
            lines.append(f"MATERIAL PREFERENCES: {', '.join(materials)}")
            lines.append("")
        
        # Planting
        if planting_signals:
            lines.append(f"PLANTING STYLE: {', '.join(planting_signals)}")
            lines.append("")
        
        # Maintenance
        if maintenance_vibe:
            lines.append(f"MAINTENANCE EXPECTATION: {maintenance_vibe}")
            lines.append("")
        
        # Insights
        if unconscious_patterns:
            lines.append("KEY INSIGHTS:")
            for insight in unconscious_patterns:
                lines.append(f"- {insight}")
        
        return "\n".join(lines)

# Singleton instance
_analyzer = None

def get_analyzer() -> VisionAnalyzer:
    """Get or create the vision analyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = VisionAnalyzer()
    return _analyzer
