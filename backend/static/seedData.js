export const SEED_CONFIG = [
    { id: 1535, label: "The Modernist" },
    { id: 1959, label: "The Entertainer" },
    { id: 1957, label: "The Naturalist" },
    { id: 1714, label: "The Hearth" },
    { id: 1436, label: "The Architectural" },
    { id: 1916, label: "The Sanctuary" },
    { id: 1743, label: "The Minimalist" },
    { id: 1633, label: "The Traditionalist" }
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
