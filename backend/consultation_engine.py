import json
import os

class ConsultationEngine:
    def __init__(self, knowledge_path=None):
        if knowledge_path is None:
            # Try to find it relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            knowledge_path = os.path.join(base_dir, "data", "leahy_knowledge.json")
            
        with open(knowledge_path, 'r') as f:
            self.data = json.load(f)
        
        self.profile = self.data['company_profile']
        self.facts = self.data['fact_cards']

    def generate_trust_header(self, query_terms, user_city=None):
        target_city = user_city if user_city else "the North Shore"
        header = f"Since {self.profile['founded']}, {self.profile['name']} has served {target_city} "
        header += "with commercial and residential expertise. "

        query_str = ' '.join(query_terms).lower()
        
        if "commercial" in query_str:
            header += "From Thomas Butler Park to corporate campuses, our team handles large-scale management."
        elif any(x in query_str for x in ["patio", "hardscape", "stone", "granite", "paver"]):
            header += f"While we have worked in {target_city} for decades, the examples below highlight our masonry standards across Essex County."
        else:
            header += f"Below are examples of our work and technical approach, available for your project in {target_city}."
        return header

    def get_knowledge_card(self, query_terms, user_city="the North Shore"):
        best_match = None
        query_str = ' '.join(query_terms).lower()
        
        for card in self.facts:
            if any(trigger in query_str for trigger in card['triggers']):
                best_match = card
                break
        
        if not best_match: return None

        final_text = best_match['geo_template'].format(city=user_city)
        return {
            "type": "knowledge_card",
            "title": best_match['title'],
            "fact": best_match['scientific_fact'],
            "local_context": final_text,
            "visual_tags": best_match['visual_tags'] 
        }
