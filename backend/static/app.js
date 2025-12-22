const API_BASE = '/api';
const VERSION = '14.0';
console.log(`Lynch Landscape Intelligence Engine ${VERSION} initialized.`);

// GLOBAL ERROR TRAP for Debugging
window.onerror = function (msg, url, line, col, error) {
    alert(`Error: ${msg}\nLine: ${line}`);
    return false;
};

// State
let currentResults = [];
let currentLightboxIndex = -1;
let folders = [];
let collections = [];
let visionBoard = JSON.parse(localStorage.getItem('visionBoard')) || [];
let imageCache = {}; // Global metadata cache

const SEED_CONFIG = [
    { id: 322, label: "The Modernist" },
    { id: 307, label: "The Entertainer" },
    { id: 764, label: "The Naturalist" },
    { id: 309, label: "The Hearth" },
    { id: 310, label: "The Architectural" },
    { id: 600, label: "The Sanctuary" },
    { id: 450, label: "The Minimalist" },
    { id: 120, label: "The Traditionalist" }
];
const ARCHETYPE_CONFIG = {
    'The Modernist': { style_query: 'Modern', suggested_chips: ['Concrete Pavers', 'Linear', 'Minimalist', 'Steel'] },
    'The Entertainer': { style_query: 'Kitchen', suggested_chips: ['Pizza Oven', 'Fire Pit', 'Bar Seating', 'Outdoor Grill'] },
    'The Naturalist': { style_query: 'Natural', suggested_chips: ['Native Plants', 'Meadow', 'Wildlife', 'Stone Path'] },
    'The Hearth': { style_query: 'Fire', suggested_chips: ['Fireplace', 'Wood Storage', 'Gathering', 'Flagstone'] },
    'The Architectural': { style_query: 'Structure', suggested_chips: ['Retaining Wall', 'Steps', 'Terrace', 'Lighting'] },
    'The Sanctuary': { style_query: 'Private', suggested_chips: ['Privacy Hedge', 'Screening', 'Water Feature', 'Enclosed'] },
    'The Minimalist': { style_query: 'Simple', suggested_chips: ['Gravel', 'Lawn', 'Clean Lines', 'Single Material'] },
    'The Traditionalist': { style_query: 'Classic', suggested_chips: ['Brick', 'Boxwood', 'Symmetry', 'Formal Garden'] }
};
const SEED_IDS = SEED_CONFIG.map(s => s.id);
const ARCHETYPES = Object.fromEntries(SEED_CONFIG.map(s => [s.id, s.label]));

// New state for Single Path
let activeArchetype = null;
let activeChips = new Set();
let hasViewedProject = false;

// Luxe Icons (SVGs)
const ICONS = {
    SEARCH: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>`,
    PLUS: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/></svg>`,
    CHECK_CIRCLE: `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4" stroke="white" stroke-width="2" fill="none"/></svg>`
};

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const resultsGrid = document.getElementById('resultsGrid');
const folderFilter = document.getElementById('folderFilter');
// Removed: toggleFavorites, collectionFilter, createCollectionBtn
const visionFab = document.getElementById('vision-fab');
const visionCountStr = document.getElementById('vision-count');
const visionModal = document.getElementById('vision-modal');
const visionReviewList = document.getElementById('vision-review-list');
// Lightbox Elements
const lightbox = document.getElementById('lightbox');
const lightboxImage = document.getElementById('lightboxImage');
const lightboxClose = document.getElementById('lightboxClose');
const lightboxNext = document.getElementById('lightboxNext');
const lightboxPrev = document.getElementById('lightboxPrev');
const lightboxFav = document.getElementById('lightboxFav');
const lightboxNotes = document.getElementById('lightboxNotes');
const lightboxAddToCollection = document.getElementById('lightboxAddToCollection');

// Init
async function init() {
    console.log("Initializing Portfolio search...");

    // Check if we should show instructions (Versioned for v13)
    const lastShown = localStorage.getItem('instructionsShown_v13');
    if (!lastShown) {
        document.getElementById('instructions-overlay').classList.remove('hidden');
    } else {
        document.getElementById('instructions-overlay').classList.add('hidden');
    }

    // Load initial seeds if nothing's happening
    if (visionBoard.length === 0) {
        loadSeedPortfolio();
    } else {
        performSearch(""); // Default view
    }

    try {
        await loadFolders();
        await loadCollections();
        updateVisionUI();

    } catch (e) {
        console.error("Init Error:", e);
        alert("Init Error: " + e.message);
    }
}

window.closeInstructions = function () {
    const overlay = document.getElementById('instructions-overlay');
    overlay.style.opacity = '0';
    setTimeout(() => {
        overlay.classList.add('hidden');
        localStorage.setItem('instructionsShown_v13', 'true');
    }, 400);
}

async function loadSeedPortfolio() {
    console.log("Loading luxury path seeds...");
    try {
        const res = await fetch(`${API_BASE}/images/details`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: SEED_IDS })
        });
        const data = await res.json();
        if (data.images) {
            data.images.forEach(img => imageCache[img.id] = img);
            updateGridWithFlip(data.images);
        }
    } catch (e) {
        console.error("Seed load failed", e);
    }
}
// (Keeping standard listeners)
searchBtn.addEventListener('click', () => {
    console.log("Search Button Clicked");
    performSearch();
});
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        console.log("Enter Key Pressed");
        performSearch();
    }
});
// Handle "X" Clear button in search input
searchInput.addEventListener('search', (e) => {
    if (searchInput.value === '') {
        performSearch(); // Reset to Onboarding
    }
});
// Removed: toggleFavorites and collectionFilter event listeners
folderFilter.addEventListener('change', performSearch);

lightboxClose.addEventListener('click', closeLightbox);
lightboxNext.addEventListener('click', nextImage);
lightboxPrev.addEventListener('click', prevImage);
document.addEventListener('keydown', (e) => {
    if (lightbox.classList.contains('hidden')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowRight') nextImage();
    if (e.key === 'ArrowLeft') prevImage();
});

lightboxFav.addEventListener('click', async () => {
    try {
        const img = currentResults[currentLightboxIndex];
        const newStatus = !img.favorite;

        // Optimistic UI update
        img.favorite = newStatus;
        updateLightboxUI();

        console.log("Toggling Favorite:", img.id, newStatus);

        await fetch(`${API_BASE}/favorite`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: img.id, favorite: newStatus })
        });
    } catch (e) {
        console.error("Favorite Error:", e);
        alert("Failed to save favorite.");
    }
});

lightboxNotes.addEventListener('click', () => {
    console.log("Notes Clicked");
    const img = currentResults[currentLightboxIndex];
    if (img) openNotesModal(img);
    else console.error("No image found for notes");
});

lightboxAddToCollection.addEventListener('change', async (e) => {
    const cid = e.target.value;
    if (!cid) return;
    const img = currentResults[currentLightboxIndex];
    await fetch(`${API_BASE}/collection/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection_id: cid, image_id: img.id })
    });
    e.target.value = "";
    alert("Added to collection!");
});

// ... Loaders and Search ... (Standard)
async function loadFolders() {
    const res = await fetch(`${API_BASE}/folders`);
    const data = await res.json();
    folders = data.folders;
    folderFilter.innerHTML = '<option value="">All Folders</option>';
    folders.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f;
        opt.textContent = f.split('/').pop() || f;
        folderFilter.appendChild(opt);
    });
}

async function loadCollections() {
    try {
        const res = await fetch(`${API_BASE}/collections`);
        collections = await res.json();

        // Header filter (removed from UI, but keep variable check for safety)
        const colFilter = document.getElementById('collectionFilter');
        if (colFilter) {
            colFilter.innerHTML = '<option value="">All Collections</option>';
            collections.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.name;
                colFilter.appendChild(opt);
            });
        }

        // Lightbox adder (still exists)
        if (lightboxAddToCollection) {
            lightboxAddToCollection.innerHTML = '<option value="">+ Add to Collection</option>';
            collections.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.name;
                lightboxAddToCollection.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Load Collections Error:", e);
    }
}

// New state for FLIP
let isReflowing = false;

// New state for Project Mode
let isProjectMode = false;
let currentProjectSlug = null;

// --- UTILS ---
function extractProjectSlug(filename) {
    if (!filename) return null;
    // Strict Regex: Identify project name by splitting on the last underscore/hyphen preceding a number
    // Example: mcgonigle_01.jpg -> mcgonigle
    // Example: old-connecticut-path-003.jpg -> old-connecticut-path
    const match = filename.match(/^(.*)[-_]\d+/);
    if (match && match[1]) {
        return match[1];
    }
    return null; // Safety: do not return full filename if pattern fails
}

async function performSearch(query = searchInput.value.trim(), folder = folderFilter.value) {
    console.log("performSearch called");

    // UNIFIED QUERY: Text + Archetype + Chips
    let combinedQuery = query;
    if (activeArchetype) {
        const config = ARCHETYPE_CONFIG[activeArchetype];
        if (config) combinedQuery = `${combinedQuery} ${config.style_query}`.trim();
    }
    if (activeChips.size > 0) {
        combinedQuery = `${combinedQuery} ${Array.from(activeChips).join(' ')}`.trim();
    }

    resultsGrid.innerHTML = '<div class="loading">Architecting results...</div>';

    // "Empty Search" Check -> Load Seeds
    if (!combinedQuery && !folder && !isProjectMode) {
        loadSeedPortfolio();
        return;
    }

    // Allow empty query
    const res = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query: combinedQuery || "",
            top_k: isProjectMode ? 100 : 24,
            folder: folder || null,
            slug: isProjectMode ? currentProjectSlug : null
        })
    });
    const data = await res.json();

    // Cache Metadata (Ensure we get rich columns if available)
    if (data.results) {
        data.results.forEach(img => {
            imageCache[img.id] = img;
        });
    }

    updateGridWithFlip(data.results);
    updateVisionMeter();
}

window.enterProjectMode = async function (slug) {
    if (!slug) return;
    console.log("Entering Project Mode:", slug);
    isProjectMode = true;
    currentProjectSlug = slug;
    hasViewedProject = true;
    updateVisionMeter();

    // Safety: Clear previous state
    currentResults = [];
    resultsGrid.innerHTML = '<div class="loading">Architecting project...</div>';

    // 1. Fetch Project Metadata
    try {
        const res = await fetch(`${API_BASE}/projects/${slug}`);
        if (res.ok) {
            const project = await res.json();
            renderProjectHero(project);
        } else {
            console.warn("Project metadata not found for slug:", slug);
            renderProjectHero({ display_title: slug, location: 'Portfolio', description: '', awards: [] });
        }
    } catch (err) {
        console.error("Error fetching project metadata:", err);
    }

    // 2. Re-search with slug filter
    await performSearch('', '');

    // 3. Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
    if (lightbox) lightbox.classList.add('hidden');
}

window.exitProjectMode = function () {
    console.log("Exiting Project Mode");
    isProjectMode = false;
    currentProjectSlug = null;

    const hero = document.getElementById('project-hero');
    if (hero) hero.classList.add('hidden');

    performSearch();
}

function renderProjectHero(project) {
    const hero = document.getElementById('project-hero');
    if (!hero) return;

    hero.classList.remove('hidden');

    // Awards rendering
    let awardsHtml = '';
    if (project.awards && project.awards.length > 0) {
        awardsHtml = project.awards.map(a => `<span class="award-badge">${a}</span>`).join('');
    }

    hero.innerHTML = `
        <div class="hero-content">
            <button class="back-link" onclick="window.exitProjectMode()">← BACK TO SEARCH</button>
            <div class="hero-top">
                <h2 class="hero-title">${project.display_title} <span class="hero-location">— ${project.location}</span></h2>
                <div class="hero-awards">${awardsHtml}</div>
            </div>
            <p class="hero-description">${project.description}</p>
        </div>
    `;
}

// Living Grid Logic
async function triggerSimilaritySearch(id) {
    // Visual Feedback immediately?
    console.log("Finding similar to", id);

    // Optional: Highlighting the anchor?

    try {
        const res = await fetch(`${API_BASE}/search/similar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, top_k: 50 })
        });
        const data = await res.json();

        // Cache Metadata
        if (data.results) {
            data.results.forEach(img => {
                imageCache[img.id] = img;
            });
        }

        // The anchor image should ideally be part of the result,
        // often returned as the first result if distance is 0.
        // If not, we might want to manually prepend it?
        // For now, trust the results.

        // Update Search Input to indicate mode?
        searchInput.value = `By Image #${id}`;

        updateGridWithFlip(data.results);

    } catch (e) {
        console.error("Similarity search failed", e);
    }

    // If triggered from lightbox, verify if we should close it?
    // Usually yes, to see the grid.
    if (!lightbox.classList.contains('hidden')) {
        closeLightbox();
    }
}
// Expose to window for HTML onclick
window.triggerSimilaritySearch = triggerSimilaritySearch;

// Refactored Render with FLIP
function updateGridWithFlip(newResults) {
    // 1. FIRST: Capture positions of existing items
    const firstPositions = new Map();
    resultsGrid.querySelectorAll('.card').forEach(card => {
        const id = card.dataset.id;
        if (id) firstPositions.set(id, card.getBoundingClientRect());
    });

    // 2. STATE: Update Data
    currentResults = newResults;
    if (currentResults.length === 0) {
        resultsGrid.innerHTML = '<div class="empty-state">No results found.</div>';
        return;
    }

    // 3. RENDER (LAST)
    resultsGrid.innerHTML = '';
    currentResults.forEach((img, index) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.dataset.id = img.id; // Critical for FLIP

        // Hover Intelligence: Show sidebar preview if board is empty
        card.onmouseenter = () => {
            if (visionBoard.length === 0) {
                calculateLiveAnalysis([img]);
            }
        };
        card.onmouseleave = () => {
            if (visionBoard.length === 0) {
                calculateLiveAnalysis([]);
            }
        };

        // Image Click -> Lightbox
        // But we need a separate button for "Find Similar"

        const thumbUrl = `/thumbnails/${img.thumbnail_path}`;
        const inVision = visionBoard.includes(img.id);
        const visionIcon = inVision ? '✨' : '';

        // Card HTML
        // NOTE: onclick="event.stopPropagation()" is crucial for buttons inside the card

        const isSelected = visionBoard.includes(img.id);
        const iconClass = isSelected ? 'active' : '';
        const actionIcon = isSelected ? ICONS.CHECK_CIRCLE : ICONS.PLUS;

        card.innerHTML = `
            <img src="${thumbUrl}" loading="lazy" alt="${img.filename}">
            <div class="card-overlay">
                <div class="card-actions">
                    <button class="icon-btn" onclick="event.stopPropagation(); window.triggerSimilaritySearch(${img.id})" title="Find Similar">
                        ${ICONS.SEARCH}
                    </button>
                    <button class="icon-btn ${iconClass}" onclick="event.stopPropagation(); window.toggleVisionFromCard(${img.id})" title="Add to Vision">
                        ${actionIcon}
                    </button>
                </div>
            </div>
            ${ARCHETYPES[img.id] ? `<div class="archetype-badge">${ARCHETYPES[img.id]}</div>` : ''}
        `;
        // Main click -> Open Lightbox OR trigger Archetype flow
        card.onclick = () => {
            if (ARCHETYPES[img.id]) {
                handleArchetypeClick(ARCHETYPES[img.id]);
            } else {
                openLightbox(index);
            }
        };

        resultsGrid.appendChild(card);
    });

    // 4. INVERT & PLAY
    requestAnimationFrame(() => {
        resultsGrid.querySelectorAll('.card').forEach(card => {
            const id = card.dataset.id;
            const first = firstPositions.get(id);

            if (first) {
                const last = card.getBoundingClientRect();
                const deltaX = first.left - last.left;
                const deltaY = first.top - last.top;

                // Invert
                card.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
                card.style.transition = 'none';

                // Play
                requestAnimationFrame(() => {
                    card.style.transition = 'transform 0.6s cubic-bezier(0.2, 0, 0.2, 1)'; // Smooth easing
                    card.style.transform = '';
                });
            } else {
                // New Item: Fade In / Slide Up
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';

                requestAnimationFrame(() => {
                    card.style.transition = 'opacity 0.6s ease, transform 0.6s cubic-bezier(0.2, 0, 0.2, 1)';
                    card.style.opacity = '1';
                    card.style.transform = '';
                });
            }
        });
    });
}
// Alias renderGrid to updateGridWithFlip for init compatibility if needed
// function renderGrid() { updateGridWithFlip(currentResults); } 
// But init calls renderGrid() implicitly via performSearch or just setting html?
// performSearch calls renderGrid().
// I will remove the old renderGrid function definition.


function openLightbox(index) {
    currentLightboxIndex = index;
    updateLightboxUI();
    lightbox.classList.remove('hidden');
}

function closeLightbox() {
    lightbox.classList.add('hidden');
    // renderGrid() call removed because we don't need to re-render the whole grid just to close lightbox
    // unless state changed. If state changed (e.g. favorite), we might want to update THAT card.
    // For now, let's just allow it. Or re-render if needed. 
    // Actually, re-rendering might be expensive. Let's start with NO re-render.
}

function updateLightboxUI() {
    if (currentLightboxIndex < 0 || currentLightboxIndex >= currentResults.length) return;
    const img = currentResults[currentLightboxIndex];
    lightboxImage.src = `${API_BASE}/image/${img.id}/raw`;

    // Favorites
    lightboxFav.classList.toggle('active', !!img.favorite);
    lightboxFav.onclick = (e) => {
        e.stopPropagation();
        toggleFavorite(img.id);
    };

    // Project Mode Trigger
    const projectBtn = document.getElementById('lightboxProject');
    if (projectBtn) {
        if (img.project_slug) {
            projectBtn.style.display = 'block';
            projectBtn.onclick = () => window.enterProjectMode(img.project_slug);
        } else {
            projectBtn.style.display = 'none';
        }
    }

    // Notes
    if (lightboxNotes) {
        lightboxNotes.onclick = () => openNotesModal(img);
    }

    // Vision Button
    let visionBtn = document.getElementById('lightboxVision');
    if (!visionBtn) {
        visionBtn = document.createElement('button');
        visionBtn.id = 'lightboxVision';
        visionBtn.className = 'control-btn';
        // Insert it after favorite or similar
        const target = document.getElementById('lightboxSimilar') || lightboxFav;
        target.parentNode.insertBefore(visionBtn, target.nextSibling);
        visionBtn.onclick = toggleVision;
    }
    const inVision = visionBoard.includes(img.id);
    const btnIcon = inVision ? ICONS.CHECK_CIRCLE : ICONS.PLUS;
    visionBtn.innerHTML = `${btnIcon} <span>Vision</span>`;
    visionBtn.classList.toggle('active', inVision);

    // Similar Button
    let similarBtn = document.getElementById('lightboxSimilar');
    if (!similarBtn) {
        similarBtn = document.createElement('button');
        similarBtn.id = 'lightboxSimilar';
        similarBtn.className = 'control-btn';
        similarBtn.textContent = "🔍 Find Similar";
        lightboxFav.parentNode.insertBefore(similarBtn, lightboxFav.nextSibling);
        similarBtn.onclick = () => {
            triggerSimilaritySearch(currentResults[currentLightboxIndex].id);
        };
    }
}

function toggleVision() {
    const img = currentResults[currentLightboxIndex];
    toggleVisionFromCard(img.id);
}

// New: Direct Toggle
window.toggleVisionFromCard = async function (id) {
    console.log("toggleVisionFromCard called with ID:", id);
    const idx = visionBoard.indexOf(id);
    if (idx === -1) {
        visionBoard.push(id);
        // Ensure we have metadata
        if (!imageCache[id]) {
            try {
                const res = await fetch(`${API_BASE}/images/details`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids: [id] })
                });
                const data = await res.json();
                if (data.images && data.images[0]) {
                    imageCache[id] = data.images[0];
                }
            } catch (e) {
                console.error("Failed to fetch metadata for live analysis", e);
            }
        }
    } else {
        visionBoard.splice(idx, 1);
    }
    localStorage.setItem('visionBoard', JSON.stringify(visionBoard));
    updateVisionMeter();

    updateVisionUI(); // Updates Dock & Analysis
    updateLightboxUI(); // Updates Modal if open

    // Update Card UI
    const card = resultsGrid.querySelector(`.card[data-id="${id}"]`);
    if (card) {
        const btn = card.querySelectorAll('.icon-btn')[1];
        const isSel = visionBoard.includes(id);
        btn.innerHTML = isSel ? ICONS.CHECK_CIRCLE : ICONS.PLUS;
        btn.classList.toggle('active', isSel);
    }
}

function updateVisionUI() {
    const cnt = visionBoard.length;
    const dock = document.getElementById('vision-dock');
    const dockCount = document.getElementById('dock-count');
    const dockItems = document.getElementById('dock-items');
    const analysisSidebar = document.getElementById('analysis-sidebar');

    if (cnt > 0) {
        dock.classList.remove('hidden');
        analysisSidebar.classList.remove('hidden');
        dockCount.textContent = cnt;

        // Render dock items
        dockItems.innerHTML = '';
        visionBoard.forEach(id => {
            const img = imageCache[id];
            if (!img) return;

            const div = document.createElement('div');
            div.className = 'dock-item';
            div.innerHTML = `<img src="/thumbnails/${img.thumbnail_path}" alt="Thumb">`;
            div.onclick = () => {
                const idx = currentResults.findIndex(r => r.id === id);
                if (idx !== -1) openLightbox(idx);
            };
            dockItems.appendChild(div);
        });

        // Trigger Live Analysis
        calculateLiveAnalysis();
    } else {
        dock.classList.add('hidden');
        analysisSidebar.classList.add('hidden');
    }
}

// Missing helper functions
function nextImage() {
    if (currentLightboxIndex < currentResults.length - 1) {
        currentLightboxIndex++;
        updateLightboxUI();
    }
}

function prevImage() {
    if (currentLightboxIndex > 0) {
        currentLightboxIndex--;
        updateLightboxUI();
    }
}

async function createCollectionPrompt() {
    const name = prompt("Collection Name:");
    if (!name) return;
    const res = await fetch(`${API_BASE}/collection/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });
    if (res.ok) await loadCollections();
    else alert("Failed to create collection.");
}

// Vision modal cache and notes
let visionDetailsCache = {}; // This is now largely superseded by imageCache for vision board items
let visionNotes = JSON.parse(localStorage.getItem('visionNotes')) || {};

// Modal logic updated
window.openVisionModal = async function () {
    visionModal.classList.remove('hidden');

    // Fetch any missing metadata for modal review
    await ensureVisionMetadata();

    renderReviewList();
}

async function ensureVisionMetadata() {
    const missing = visionBoard.filter(id => !imageCache[id]);
    if (missing.length > 0) {
        try {
            const res = await fetch(`${API_BASE}/images/details`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: missing })
            });
            const data = await res.json();
            if (data.images) {
                data.images.forEach(img => {
                    imageCache[img.id] = img;
                });
            }
        } catch (e) {
            console.error("Metadata fetch error", e);
        }
    }
}

// --- REACTIVE ANALYSIS ENGINE ---

function calculateLiveAnalysis(overrideImages = null) {
    const selected = overrideImages || visionBoard.map(id => imageCache[id]).filter(Boolean);

    if (selected.length === 0) {
        // Reset UI if empty
        document.getElementById('dominant-style').textContent = '---';
        document.getElementById('materials-section').classList.add('hidden');
        document.getElementById('privacy-val').textContent = '---';
        document.getElementById('terrain-val').textContent = '---';
        document.getElementById('balance-val').textContent = '---';
        document.getElementById('spatial-intent-list').textContent = '---';
        const list = document.getElementById('vision-review-list');
        if (list) list.innerHTML = '';
        return;
    }

    // --- 1. DATA AGGREGATION ---

    // A. Style & Archetype (Dominant)
    const styleCounts = {};
    selected.forEach(img => {
        if (img.design_style) {
            styleCounts[img.design_style] = (styleCounts[img.design_style] || 0) + 1;
        }
    });
    const dominantStyle = Object.entries(styleCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'Unclassified';

    // B. Primary Materials (Consolidated List)
    const materialCounts = {};
    selected.forEach(img => {
        const mats = img.material_palette && img.material_palette.length > 0
            ? img.material_palette
            : img.hardscape_materials || []; // Fallback

        mats.forEach(m => {
            const clean = m.trim().toUpperCase();
            materialCounts[clean] = (materialCounts[clean] || 0) + 1;
        });
    });
    const topMaterials = Object.entries(materialCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([m]) => m);

    // C. Site Dynamics (Privacy, Terrain, Balance)
    const privacyCounts = {};
    const terrainCounts = {};
    const balanceCounts = {};

    selected.forEach(img => {
        if (img.privacy_level) privacyCounts[img.privacy_level] = (privacyCounts[img.privacy_level] || 0) + 1;
        if (img.terrain_type) terrainCounts[img.terrain_type] = (terrainCounts[img.terrain_type] || 0) + 1;
        if (img.hardscape_ratio) balanceCounts[img.hardscape_ratio] = (balanceCounts[img.hardscape_ratio] || 0) + 1;
    });

    const getTop = (counts) => Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0].toUpperCase() || '---';

    const dominantPrivacy = getTop(privacyCounts);
    const dominantTerrain = getTop(terrainCounts);
    const dominantBalance = getTop(balanceCounts);

    // D. Spatial Purpose (Top 2)
    const spatialCounts = {};
    selected.forEach(img => {
        if (img.spatial_purpose) {
            spatialCounts[img.spatial_purpose] = (spatialCounts[img.spatial_purpose] || 0) + 1;
        }
    });
    const topSpatial = Object.entries(spatialCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 2)
        .map(([purpose]) => purpose.toUpperCase());


    // --- 2. UI RENDERING ('Spec Sheet' Aesthetic) ---

    // Style
    document.getElementById('dominant-style').textContent = dominantStyle.toUpperCase();

    // Primary Materials
    const materialsList = document.getElementById('materials-list');
    const materialsSec = document.getElementById('materials-section');
    if (topMaterials.length > 0) {
        materialsList.textContent = topMaterials.join(' • ');
        materialsSec.classList.remove('hidden');
    } else {
        materialsSec.classList.add('hidden');
    }

    // Site Dynamics
    document.getElementById('privacy-val').textContent = dominantPrivacy;
    document.getElementById('terrain-val').textContent = dominantTerrain;
    document.getElementById('balance-val').textContent = dominantBalance;

    // Spatial Intent
    const spatialList = document.getElementById('spatial-intent-list');
    spatialList.innerHTML = topSpatial.length > 0 ? topSpatial.join(' <span class="pipe">|</span> ') : '---';

    // Sidebar Image Review
    renderSidebarReview(selected);

    // Update global for brief copying
    window.currentVisionAnalysis = {
        total_images: selected.length,
        top_styles: [{ label: dominantStyle, avg: 1.0 }], // Simplified for now
        top_elements: topSpatial.map(p => ({ label: p, count: 1 }))
    };
}

function renderSidebarReview(selected) {
    const list = document.getElementById('vision-review-list');
    if (!list) return; // In case we removed it from sidebar
    list.innerHTML = '';
    selected.forEach(img => {
        const div = document.createElement('div');
        div.className = 'review-item-mini';
        div.innerHTML = `
            <img src="/thumbnails/${img.thumbnail_path}">
            <div class="review-details">
                <span class="review-caption">${img.caption || 'Project Detail'}</span>
                <span class="review-style">${img.design_style || ''}</span>
            </div>
            <button class="remove-btn-mini" onclick="window.toggleVisionFromCard(${img.id})">&times;</button>
        `;
        list.appendChild(div);
    });
}
window.copyBriefToClipboard = function () {
    if (!currentVisionAnalysis) return;

    let text = "DESIGN BRIEF - LYNCH LANDSCAPE\n";
    text += "================================\n";
    text += `Total Images: ${currentVisionAnalysis.total_images}\n\n`;

    text += "STYLE MATCH:\n";
    currentVisionAnalysis.top_styles.forEach(s => {
        text += `- ${s.label}: ${Math.round(s.avg * 100)}%\n`;
    });

    text += "\nTOP ELEMENTS:\n";
    currentVisionAnalysis.top_elements.forEach(e => {
        text += `- ${e.label}: ${e.count} references\n`;
    });

    navigator.clipboard.writeText(text);
    alert("Brief copied to clipboard!");
}

async function renderReviewList() {
    const list = document.getElementById('modal-review-list');
    list.innerHTML = '';

    visionBoard.forEach(id => {
        const img = imageCache[id];
        if (!img) return;

        const div = document.createElement('div');
        div.className = 'review-item';
        div.innerHTML = `
            <img src="/thumbnails/${img.thumbnail_path}" class="review-thumb">
            <div class="review-info">
                <h5>${img.caption || 'Product Detail'}</h5>
                <textarea onchange="window.saveNoteLocal(${img.id}, this.value)" 
                    placeholder="Notes for this shot...">${visionNotes[img.id] || ''}</textarea>
            </div>
            <button class="remove-btn" onclick="window.removeFromVision(${img.id})">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
        `;
        list.appendChild(div);
    });
}

window.saveNoteLocal = function (id, text) {
    visionNotes[id] = text;
    localStorage.setItem('visionNotes', JSON.stringify(visionNotes));
}

window.removeFromVision = function (id) {
    toggleVisionFromCard(id); // Reuse the toggle logic

    // If empty, close? Or just re-render
    if (visionBoard.length === 0) {
        closeVisionModal();
    } else {
        renderReviewList();
    }
}

window.closeVisionModal = function () {
    visionModal.classList.add('hidden');
}

window.submitLead = async function (e) {
    e.preventDefault();
    const btn = document.getElementById('submitVisionBtn');
    btn.disabled = true;
    btn.textContent = "Sending...";

    const name = document.getElementById('lead-name').value;
    const email = document.getElementById('lead-email').value;
    const phone = document.getElementById('lead-phone').value;
    const address = document.getElementById('lead-address').value;
    const timeline = document.querySelector('input[name="timeline"]:checked').value;
    const budget = document.querySelector('input[name="budget"]:checked').value;

    try {
        const res = await fetch(`${API_BASE}/leads/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name, email, phone, address, timeline, budget,
                image_ids: visionBoard,
                image_notes: visionNotes
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            alert("Vision Sent! Check your email.");
            // Clear board
            visionBoard = [];
            visionNotes = {};
            localStorage.removeItem('visionBoard');
            localStorage.removeItem('visionNotes');
            updateVisionUI();
            closeVisionModal();
        } else {
            alert("Error sending vision.");
        }
    } catch (err) {
        console.error(err);
        alert("Failed to send.");
    } finally {
        btn.disabled = false;
        btn.textContent = "Finalize Vision";
    }
}

// Notes Modal (Classic View)
const notesModal = document.getElementById('notesModal');
const notesInput = document.getElementById('notesInput');
const saveNotesBtn = document.getElementById('saveNotesBtn');
const cancelNotesBtn = document.getElementById('cancelNotesBtn');
let editingImgId = null;

function openNotesModal(img) {
    editingImgId = img.id;
    notesInput.value = img.notes || "";
    notesModal.classList.remove('hidden');
}
cancelNotesBtn.onclick = () => notesModal.classList.add('hidden');
saveNotesBtn.onclick = async () => {
    if (!editingImgId) return;
    const txt = notesInput.value;
    await fetch(`${API_BASE}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: editingImgId, notes: txt })
    });
    const img = currentResults.find(i => i.id === editingImgId);
    if (img) img.notes = txt;
    notesModal.classList.add('hidden');
};

try {
    init();
} catch (err) {
    console.error("Init failed:", err);
    alert("Application Error: " + err.message);
}

// --- SINGLE PATH MOMENTUM SYSTEM ---

function handleArchetypeClick(label) {
    console.log("Archetype Clicked:", label);
    activeArchetype = label;
    activeChips.clear();

    // Cinematic Glide: Smooth scroll to the top of the Filter Bar
    const header = document.querySelector('.header');
    if (header) {
        const top = header.getBoundingClientRect().top + window.pageYOffset;
        window.scrollTo({ top: top, behavior: 'smooth' });
    }

    // UI: Render chips above grid
    renderSmartChips();

    // Action: Trigger unified search
    performSearch();

    // Vision: Update meter
    updateVisionMeter();
}

function renderSmartChips() {
    const container = document.getElementById('smart-chips-container');
    if (!container || !activeArchetype) return;

    const config = ARCHETYPE_CONFIG[activeArchetype];
    if (!config) return;

    container.classList.remove('hidden');
    container.innerHTML = `
        <div class="context-bridge" style="width: 100%; margin-bottom: 1.5rem; animation: fadeIn 0.8s ease-out;">
            <h3 style="font-family: 'Playfair Display', serif; font-size: 1.75rem; color: #081D34; margin: 0 0 4px 0;">Exploring: ${activeArchetype}</h3>
            <p style="font-size: 0.875rem; color: #6b7280; font-weight: 400; margin: 0;">Select a filter below OR type your own specific vision (e.g., "Infinity Edge")</p>
        </div>
        <div style="font-size: 0.7rem; font-weight: 700; color: #9ca3af; text-transform: uppercase; margin-bottom: 8px; width: 100%; letter-spacing: 0.05em;">
            Suggested Refinements:
        </div>
        ${config.suggested_chips.map(chip => `
            <div class="smart-chip ${activeChips.has(chip) ? 'active' : ''}" 
                 onclick="window.toggleChip('${chip}')">
                ${chip}
            </div>
        `).join('')}
    `;
}

window.toggleChip = function (chip) {
    if (activeChips.has(chip)) {
        activeChips.delete(chip);
    } else {
        activeChips.add(chip);
    }
    renderSmartChips();
    performSearch();
};

function updateVisionMeter() {
    let score = 0;
    if (activeArchetype) score += 20;
    score += Math.min(visionBoard.length * 20, 60);
    if (hasViewedProject) score += 20;

    const container = document.getElementById('vision-meter-container');
    if (!container) return;

    let stageClass = 'low';
    let statusText = 'Start your vision';
    if (score >= 100) {
        stageClass = 'high';
        statusText = 'Vision Complete';
    } else if (score >= 50) {
        stageClass = 'mid';
        statusText = 'Keep going...';
    }

    container.innerHTML = `
        <div class="meter-label">
            <span>Vision Strength</span>
            <span>${score}%</span>
        </div>
        <div class="meter-track">
            <div class="meter-fill ${stageClass}" style="width: ${score}%"></div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
            <span style="font-size: 0.65rem; color: #6b7280;">${statusText}</span>
            <button id="finalize-brief-btn" class="finalize-btn ${score >= 100 ? 'active' : ''}" 
                    ${score >= 100 ? '' : 'disabled'}
                    onclick="window.copyBriefToClipboard()">
                Finalize Brief
            </button>
        </div>
    `;
}

// Final Step: Populate meter on load
updateVisionMeter();
