export const SEED_CONFIG = [
    { id: 2351, label: "The Modernist" },
    { id: 2277, label: "The Entertainer" },
    { id: 2265, label: "The Naturalist" },
    { id: 2228, label: "The Hearth" },
    { id: 2298, label: "The Architectural" },
    { id: 2313, label: "The Sanctuary" },
    { id: 2340, label: "The Minimalist" },
    { id: 2349, label: "The Traditionalist" }
];

export const ARCHETYPE_CONFIG = {
    'The Modernist': { style_query: 'Modern', suggested_chips: ['Concrete Pavers', 'Linear', 'Minimalist', 'Steel'] },
    'The Entertainer': { style_query: 'Kitchen', suggested_chips: ['Pizza Oven', 'Fire Pit', 'Bar Seating', 'Outdoor Grill'] },
    'The Naturalist': { style_query: 'Natural', suggested_chips: ['Native Plants', 'Meadow', 'Wildlife', 'Stone Path'] },
    'The Hearth': { style_query: 'Fire', suggested_chips: ['Fireplace', 'Wood Storage', 'Gathering', 'Flagstone'] },
    'The Architectural': { style_query: 'Structure', suggested_chips: ['Retaining Wall', 'Steps', 'Terrace', 'Lighting'] },
    'The Sanctuary': { style_query: 'Private', suggested_chips: ['Privacy Hedge', 'Screening', 'Water Feature', 'Enclosed'] },
    'The Minimalist': { style_query: 'Simple', suggested_chips: ['Gravel', 'Lawn', 'Clean Lines', 'Single Material'] },
    'The Traditionalist': { style_query: 'Classic', suggested_chips: ['Brick', 'Boxwood', 'Symmetry', 'Formal Garden'] }
};
