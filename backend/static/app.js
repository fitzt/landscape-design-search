import { CLIENT_CONFIG } from './clientSettings.js';
import { SEED_CONFIG, ARCHETYPE_CONFIG } from './seedData.js';

const API_BASE = '/api';
const VERSION = CLIENT_CONFIG.version;
console.log(`${CLIENT_CONFIG.brandName} Intelligence Engine ${VERSION} initialized.`);

// GLOBAL ERROR TRAP for Debugging
window.onerror = function (msg, url, line, col, error) {
    console.error(`Error: ${msg}\nLine: ${line}`);
    return false;
};

// --- BRANDING UTILS ---
function applyBranding() {
    // 1. App-level Metadata
    document.title = `${CLIENT_CONFIG.brandName} | ${CLIENT_CONFIG.tagline}`;
    const metaDesc = document.getElementById('meta-description');
    if (metaDesc) metaDesc.content = `Semantic search for ${CLIENT_CONFIG.brandName} portfolio`;

    // 2. CSS Variables
    const root = document.documentElement;
    root.style.setProperty('--brand-font-primary', CLIENT_CONFIG.primaryFont);
    root.style.setProperty('--brand-font-secondary', CLIENT_CONFIG.secondaryFont);
    root.style.setProperty('--brand-color-primary', CLIENT_CONFIG.primaryColor);
    root.style.setProperty('--brand-color-accent', CLIENT_CONFIG.accentColor);

    // 3. UI Elements
    const brandNameEl = document.getElementById('brand-name');
    const brandTaglineEl = document.getElementById('brand-tagline');
    const brandVersionEl = document.getElementById('brand-version');
    const brandLogoEl = document.getElementById('brand-logo');
    const modalBrandNameEl = document.getElementById('modal-brand-name');
    const modalLocationEl = document.getElementById('modal-brand-location');
    const sidebarBrandNameEl = document.getElementById('modal-sidebar-brand-name');
    const sidebarBrandSubEl = document.getElementById('modal-sidebar-brand-sub');
    const sidebarVersionEl = document.getElementById('sidebar-version');
    const versionBadgeEl = document.getElementById('version-badge');

    if (brandNameEl) brandNameEl.textContent = CLIENT_CONFIG.brandName;
    if (brandTaglineEl) {
        brandTaglineEl.innerHTML = `${CLIENT_CONFIG.tagline} <span id="brand-version" style="opacity: 0.5; margin-left: 8px;">${CLIENT_CONFIG.version}</span>`;
    }
    if (brandLogoEl) {
        brandLogoEl.src = CLIENT_CONFIG.logoUrl;
        brandLogoEl.alt = `${CLIENT_CONFIG.brandName} Logo`;
    }
    if (modalBrandNameEl) modalBrandNameEl.textContent = CLIENT_CONFIG.brandName;
    if (modalLocationEl) modalLocationEl.textContent = CLIENT_CONFIG.location;

    if (sidebarVersionEl) sidebarVersionEl.textContent = `PRO ${CLIENT_CONFIG.version}`;
    if (versionBadgeEl) versionBadgeEl.textContent = `${CLIENT_CONFIG.version} | OBJECT INTELLIGENCE`;

    // Sidebar usually split for aesthetic
    if (sidebarBrandNameEl) {
        const parts = CLIENT_CONFIG.brandName.split('&');
        sidebarBrandNameEl.textContent = parts[0].trim().toUpperCase();
        if (sidebarBrandSubEl && parts[1]) sidebarBrandSubEl.textContent = parts[1].trim().toUpperCase();
    }
}
window.applyBranding = applyBranding;

// --- UI UTILS ---
function showToast(message, duration = 3000) {
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toast-message');
    if (!toast || !toastMsg) return;

    toastMsg.textContent = message;
    toast.classList.add('visible');

    setTimeout(() => {
        toast.classList.remove('visible');
    }, duration);
}
window.showToast = showToast;

// State
let currentResults = [];
let currentLightboxIndex = -1;
let folders = [];
let collections = [];
let visionBoard = JSON.parse(localStorage.getItem('visionBoard')) || [];
let visionCutouts = JSON.parse(localStorage.getItem('visionCutouts')) || [];
let imageCache = {}; // Global metadata cache

// Global state for the active object selection (v15 Engine)
let activeObjectData = null;

// --- PREFERENCE SCORING ENGINE ---
let PreferenceScore = {
    styles: {},
    elements: {}
};

function trackPreference(type, key) {
    if (!key) return;
    const increment = type === 'styles' ? 10 : 20;
    if (!PreferenceScore[type][key]) PreferenceScore[type][key] = 0;
    PreferenceScore[type][key] += increment;
    console.log(`[Preference Tracking] %c${type.toUpperCase()}: ${key} %c+${increment} | Total Score:`,
        "color: #00ff9d; font-weight: bold", "color: #ffffff", PreferenceScore);
}

// (Configs moved to seedData.js)
const SEED_IDS = SEED_CONFIG.map(s => s.id);
const ARCHETYPES = Object.fromEntries(SEED_CONFIG.map(s => [s.id, s.label]));

// New state for Single Path
let activeArchetype = null;
let activeChips = new Set();
let hasViewedProject = false;
let isProjectMode = false;
let currentProjectSlug = null;

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
const lightbox = document.getElementById('lightbox');
const lightboxImage = document.getElementById('lightboxImage');
const lightboxClose = document.getElementById('lightboxClose');
const lightboxNext = document.getElementById('lightboxNext');
const lightboxPrev = document.getElementById('lightboxPrev');
const lightboxFav = document.getElementById('lightboxFav');
const lightboxNotes = document.getElementById('lightboxNotes');
const lightboxAddToCollection = document.getElementById('lightboxAddToCollection');
const visionModal = document.getElementById('vision-modal');

// --- INIT ---
async function init() {
    console.log("Initializing Portfolio search...");

    // Initialize Branding & UI FIRST (White labeling requirement)
    applyBranding();

    // Check if we should show instructions (Versioned for v13)
    // DISABLED FOR LEAHY per user request
    const isLeahy = CLIENT_CONFIG.projectSlug === 'leahy';
    if (isLeahy) {
        document.getElementById('instructions-overlay')?.classList.add('hidden');
        document.getElementById('analysis-sidebar')?.classList.add('hidden');
    } else {
        const lastShown = localStorage.getItem('instructionsShown_v13');
        if (!lastShown) {
            document.getElementById('instructions-overlay')?.classList.remove('hidden');
        } else {
            document.getElementById('instructions-overlay')?.classList.add('hidden');
        }
    }

    // Load initial seeds if nothing's happening
    try {
        if (visionBoard.length === 0) {
            await loadSeedPortfolio();
        } else {
            await performSearch(""); // Default view
        }
    } catch (e) {
        console.warn("Could not load initial images. Backend might be offline.", e);
        resultsGrid.innerHTML = '<div class="empty-state">Backend API offline. Run "python backend/app.py" to see images.</div>';
    }

    // Deep-linking support
    const urlParams = new URLSearchParams(window.location.search);
    const linkedImageId = urlParams.get('image_id');
    if (linkedImageId) {
        console.log("Deep-linking to image:", linkedImageId);
        try {
            const res = await fetch(`${API_BASE}/images/details`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: [parseInt(linkedImageId)] })
            });
            const data = await res.json();
            if (data.images && data.images.length > 0) {
                const img = data.images[0];
                imageCache[img.id] = img;
                // Prepend to current results so openLightbox(0) works
                currentResults = [img, ...currentResults];
                updateGridWithFlip(currentResults);
                openLightbox(0);
            }
        } catch (e) {
            console.error("Deep-linking failed", e);
        }
    }

    try {
        await loadFolders();
        await loadCollections();
    } catch (e) {
        console.warn("Folder/Collection metadata failed to load.", e);
    }

    try {
        // Ensure metadata for visionBoard items is loaded
        if (visionBoard.length > 0) {
            updateVisionUI();
            const missingIds = visionBoard.filter(id => !imageCache[id]);
            if (missingIds.length > 0) {
                const res = await fetch(`${API_BASE}/images/details`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids: missingIds })
                });
                const data = await res.json();
                if (data.images) {
                    data.images.forEach(img => imageCache[img.id] = img);
                    updateVisionUI(); // Re-render once data in
                }
            }
        }
    } catch (e) {
        console.error("Vision metadata recovery failed", e);
    }
}

window.closeInstructions = function () {
    const overlay = document.getElementById('instructions-overlay');
    if (overlay) {
        overlay.style.opacity = '0';
        setTimeout(() => {
            overlay.classList.add('hidden');
            localStorage.setItem('instructionsShown_v13', 'true');
        }, 400);
    }
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

// --- EVENT LISTENERS ---
if (searchBtn) searchBtn.addEventListener('click', () => performSearch());
if (searchInput) {
    searchInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') performSearch(); });
    searchInput.addEventListener('search', (e) => { if (searchInput.value === '') performSearch(); });
}
if (folderFilter) folderFilter.addEventListener('change', performSearch);

if (lightboxClose) lightboxClose.addEventListener('click', closeLightbox);
if (lightboxNext) lightboxNext.addEventListener('click', nextImage);
if (lightboxPrev) lightboxPrev.addEventListener('click', prevImage);

document.addEventListener('keydown', (e) => {
    if (lightbox && lightbox.classList.contains('hidden')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowRight') nextImage();
    if (e.key === 'ArrowLeft') prevImage();
});

if (lightboxFav) {
    lightboxFav.addEventListener('click', async () => {
        try {
            const img = currentResults[currentLightboxIndex];
            const newStatus = !img.favorite;
            img.favorite = newStatus;
            updateLightboxUI();
            await fetch(`${API_BASE}/favorite`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: img.id, favorite: newStatus })
            });
        } catch (e) { console.error("Favorite Error:", e); }
    });
}

if (lightboxNotes) {
    lightboxNotes.addEventListener('click', () => {
        const img = currentResults[currentLightboxIndex];
        if (img) openNotesModal(img);
    });
}

if (lightboxAddToCollection) {
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
}

// --- LOADERS ---
async function loadFolders() {
    const res = await fetch(`${API_BASE}/folders`);
    const data = await res.json();
    folders = data.folders;
    if (folderFilter) {
        folderFilter.innerHTML = '<option value="">All Folders</option>';
        folders.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f;
            opt.textContent = f.split('/').pop() || f;
            folderFilter.appendChild(opt);
        });
    }
}

async function loadCollections() {
    try {
        const res = await fetch(`${API_BASE}/collections`);
        collections = await res.json();
        if (lightboxAddToCollection) {
            lightboxAddToCollection.innerHTML = '<option value="">+ Add to Collection</option>';
            collections.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.name;
                lightboxAddToCollection.appendChild(opt);
            });
        }
    } catch (e) { console.error("Load Collections Error:", e); }
}

// --- SEARCH LOGIC ---
async function performSearch(query = searchInput.value.trim(), folder = folderFilter?.value) {
    // Export globally for lightbox interaction
    if (!window.performSearch) window.performSearch = performSearch;

    let combinedQuery = query;
    if (activeArchetype) {
        const config = ARCHETYPE_CONFIG[activeArchetype];
        if (config) combinedQuery = `${combinedQuery} ${config.style_query}`.trim();
    }
    if (activeChips.size > 0) {
        combinedQuery = `${combinedQuery} ${Array.from(activeChips).join(' ')}`.trim();
    }

    resultsGrid.innerHTML = '<div class="loading">Architecting results...</div>';

    if (!combinedQuery && !folder && !isProjectMode) {
        loadSeedPortfolio();
        return;
    }

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

    if (data.results) {
        data.results.forEach(img => { if (img.id) imageCache[img.id] = img; });
    }
    updateGridWithFlip(data.results, data.trust_header);

}

// --- GRID LOGIC ---
function updateGridWithFlip(newResults, trustHeader = null) {
    const firstPositions = new Map();
    resultsGrid.querySelectorAll('.card').forEach(card => {
        const id = card.dataset.id;
        if (id) firstPositions.set(id, card.getBoundingClientRect());
    });

    const trustContainer = document.getElementById('trust-header-container');
    if (trustContainer) {
        if (trustHeader) {
            trustContainer.textContent = trustHeader;
            trustContainer.classList.remove('hidden');
        } else {
            trustContainer.classList.add('hidden');
        }
    }

    currentResults = newResults;
    if (currentResults.length === 0) {
        resultsGrid.innerHTML = '<div class="empty-state">No results found.</div>';
        return;
    }

    resultsGrid.innerHTML = ''; // Clear previous

    currentResults.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.dataset.id = item.id || `fact_${index}`;
        card.dataset.type = item.type || (item.hero_image ? 'project' : 'image');

        if (card.dataset.type === 'fact_card' || card.dataset.type === 'knowledge_card') {
            renderFactCard(card, item);
        } else if (card.dataset.type === 'project') {
            renderProjectCard(card, item, index);
        } else {
            renderImageCard(card, item, index);
        }

        resultsGrid.appendChild(card);
    });

    // FLIP Animation
    requestAnimationFrame(() => {
        resultsGrid.querySelectorAll('.card').forEach(card => {
            const id = card.dataset.id;
            const first = firstPositions.get(id);
            if (first) {
                const last = card.getBoundingClientRect();
                const deltaX = first.left - last.left;
                const deltaY = first.top - last.top;
                card.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
                card.style.transition = 'none';
                requestAnimationFrame(() => {
                    card.style.transition = 'transform 0.6s cubic-bezier(0.2, 0, 0.2, 1)';
                    card.style.transform = '';
                });
            } else {
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

function renderImageCard(card, img, index) {
    card.onmouseenter = () => { if (visionBoard.length === 0) calculateLiveAnalysis([img]); };
    card.onmouseleave = () => { if (visionBoard.length === 0) calculateLiveAnalysis([]); };

    const thumbUrl = `/thumbnails/${img.thumbnail_path}`;
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
    `;

    card.onclick = () => {
        if (SEED_IDS.includes(parseInt(img.id))) {
            handleArchetypeClick(ARCHETYPES[img.id]);
        } else {
            openLightbox(index);
        }
    };
}

function renderProjectCard(card, project, index) {
    const hero = project.hero_image;
    const thumbUrl = `/thumbnails/${hero.thumbnail_path}`;

    card.classList.add('project-card');
    card.innerHTML = `
        <img src="${thumbUrl}" loading="lazy" alt="${hero.filename}">
        <div class="card-overlay">
            <div class="project-info">
                <div class="project-title">${project.id.startsWith('temp_') ? 'Portfolio Collection' : 'Design Project'}</div>
            </div>
        </div>
    `;

    card.onclick = () => openLightbox(index);
}

function renderFactCard(card, fact) {
    card.classList.add('fact-card');

    const title = fact.title || "Pro Insight";
    const text = fact.fact || fact.text;
    const local = fact.local_context || "";
    const tags = fact.visual_tags || fact.visual_match_tags || [];

    card.innerHTML = `
        <div class="fact-content">
            <div class="fact-icon">🎓</div>
            <div class="fact-title">${title}</div>
            <div class="fact-text">${text}</div>
            ${local ? `<div class="fact-local">${local}</div>` : ''}
            <div class="fact-tags">
                ${tags.map(t => `<span class="fact-tag">#${t}</span>`).join('')}
            </div>
        </div>
    `;
    card.onclick = () => {
        showToast("Educational Insight - Knowledge Engine");
    };
}

// --- LIGHTBOX LOGIC ---
function openLightbox(index) {
    currentLightboxIndex = index;
    const item = currentResults[index];
    if (item && item.design_style) {
        trackPreference('styles', item.design_style);
    }
    updateLightboxUI();
    lightbox.classList.remove('hidden');
}

function closeLightbox() {
    lightbox.classList.add('hidden');
}

function updateLightboxUI() {
    if (currentLightboxIndex < 0 || currentLightboxIndex >= currentResults.length) return;
    const item = currentResults[currentLightboxIndex];
    const isProject = !!item.hero_image;

    // Reset carousel elements
    const label = document.getElementById('lightbox-phase-label');
    if (label) label.classList.add('hidden');
    const indicators = document.getElementById('lightbox-indicators');
    if (indicators) indicators.innerHTML = '';

    // Handle Project Container
    if (isProject) {
        renderProjectLightbox(item);
        return;
    }

    // Standard Image Lightbox
    const img = item;
    lightboxImage.src = `/images/${img.filename}`;

    // Favorites
    if (lightboxFav) {
        lightboxFav.classList.toggle('active', !!img.favorite);
    }

    // Project Button - HIDE IN LEAHY CONSULTATION MODE
    const projectBtn = document.getElementById('lightboxProject');
    if (projectBtn) {
        if (img.project_slug && CLIENT_CONFIG.projectSlug !== 'leahy') {
            projectBtn.style.display = 'block';
            projectBtn.onclick = () => window.enterProjectMode(img.project_slug);
        } else {
            projectBtn.style.display = 'none';
        }
    }

    // Vision Button
    let visionBtn = document.getElementById('lightboxVision');
    if (!visionBtn && lightboxFav) {
        visionBtn = document.createElement('button');
        visionBtn.id = 'lightboxVision';
        visionBtn.className = 'control-btn';
        const target = document.getElementById('lightboxSimilar') || lightboxFav;
        target.parentNode.insertBefore(visionBtn, target.nextSibling);
        visionBtn.onclick = toggleVision;
    }
    if (visionBtn) {
        const inVision = visionBoard.includes(img.id);
        const btnIcon = inVision ? ICONS.CHECK_CIRCLE : ICONS.PLUS;
        visionBtn.innerHTML = `${btnIcon} <span>Vision</span>`;
        visionBtn.classList.toggle('active', inVision);
    }

    // Similar Button
    let similarBtn = document.getElementById('lightboxSimilar');
    if (!similarBtn && lightboxFav) {
        similarBtn = document.createElement('button');
        similarBtn.id = 'lightboxSimilar';
        similarBtn.className = 'control-btn';
        similarBtn.textContent = "🔍 Find Similar";
        if (lightboxFav.parentNode) {
            lightboxFav.parentNode.insertBefore(similarBtn, lightboxFav.nextSibling);
        }
        similarBtn.onclick = () => {
            triggerSimilaritySearch(currentResults[currentLightboxIndex].id);
        };
    }

    // --- IGNITE OBJECT INTELLIGENCE ---
    if (lightboxImage.complete) {
        renderImageObjects(img);
    } else {
        lightboxImage.onload = () => renderImageObjects(img);
    }
}

function renderProjectLightbox(project) {
    const allAssets = [...project.assets.after, ...project.assets.context];
    let assetIndex = 0;

    const label = document.getElementById('lightbox-phase-label');
    const indicators = document.getElementById('lightbox-indicators');

    const updateAsset = (idx) => {
        assetIndex = idx; // Update shared index
        const asset = allAssets[idx];
        lightboxImage.src = `/images/${asset.filename}`;

        console.log("Setting lightbox asset:", asset.filename);

        if (label) {
            label.textContent = asset.phase.toUpperCase();
            label.className = `phase-label phase-${asset.phase}`;
            label.style.display = 'block';
            label.classList.remove('hidden');
        }

        if (indicators) {
            indicators.querySelectorAll('.indicator').forEach((el, i) => {
                el.classList.toggle('active', i === idx);
            });
        }
    };

    // Initial render
    updateAsset(0);

    if (indicators) {
        indicators.innerHTML = allAssets.map((a, i) =>
            `<div class="indicator ${i === 0 ? 'active' : ''}" onclick="window.setLightboxAsset(${i})"></div>`
        ).join('');
    }

    // Connect prev/next buttons for project carousel
    document.getElementById('lightboxPrev').onclick = () => {
        const nextIdx = (assetIndex - 1 + allAssets.length) % allAssets.length;
        updateAsset(nextIdx);
    };
    document.getElementById('lightboxNext').onclick = () => {
        const nextIdx = (assetIndex + 1) % allAssets.length;
        updateAsset(nextIdx);
    };

    window.setLightboxAsset = updateAsset;
}

// --- SEARCH HELPERS ---
async function triggerSimilaritySearch(id) {
    console.log("Finding similar to", id);
    try {
        const res = await fetch(`${API_BASE}/similar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, top_k: 50 })
        });
        const data = await res.json();
        if (data.results) data.results.forEach(img => imageCache[img.id] = img);
        // searchInput.value = `By Image #${id}`; // Removed for "magic" UI
        updateGridWithFlip(data.results);
        closeLightbox();
    } catch (e) {
        console.error("Similarity search failed", e);
    }
}
window.triggerSimilaritySearch = triggerSimilaritySearch;

// =========================================================
// --- NEW OBJECT INTELLIGENCE ENGINE (v15 - ASSET PIPELINE) ---
// =========================================================

// 1. The Renderer (Draws the shapes + The Hidden Menu)
async function renderImageObjects(imgMetadata) {
    const imageId = imgMetadata.id;
    const overlay = document.getElementById('image-objects-overlay');
    const objectsList = document.getElementById('objects-list-container');
    if (!overlay) return;

    // --- STEP A: IMMEDIATE GLOBAL RENDER ---
    // Clear previous SVG
    overlay.innerHTML = '';

    // Prepare Discovery List with Global Tags immediately
    if (objectsList) {
        objectsList.innerHTML = `
            <div class="elements-header">
                <h4 class="elements-title">Design Elements</h4>
            </div>
            <div class="chips-wrapper"></div>
        `;
        const chipsWrapper = objectsList.querySelector('.chips-wrapper');

        // Render Global Intelligence (GPT-4o tags) immediately
        const globalTags = new Set([
            ...(imgMetadata.architectural_features || []),
            ...(imgMetadata.material_palette || [])
        ]);

        if (globalTags.size > 0) {
            objectsList.classList.remove('hidden');
            globalTags.forEach(tag => {
                const chip = document.createElement('div');
                chip.className = 'object-chip global';
                chip.textContent = tag;
                chip.title = "Global scene analysis - Click to search";

                chip.onclick = (e) => {
                    e.stopPropagation();
                    const searchTerm = tag;
                    showToast(`Searching for ${searchTerm}...`);
                    closeLightbox();
                    document.getElementById('searchInput').value = searchTerm;
                    performSearch(searchTerm);
                };

                chipsWrapper.appendChild(chip);
            });
        } else {
            // Hide until spatial results come in
            objectsList.classList.add('hidden');
        }
    }

    // --- STEP B: ASYNC SPATIAL RENDER ---
    try {
        const chipsWrapper = objectsList ? objectsList.querySelector('.chips-wrapper') : null;
        const countBefore = chipsWrapper ? chipsWrapper.querySelectorAll('.object-chip').length : 0;

        const res = await fetch(`${API_BASE}/images/${imageId}/objects`);
        const data = await res.json();

        if (!data.data || data.data.length === 0) return;

        const svgWidth = data.width || 1024;
        const svgHeight = data.height || 1024;
        const viewBox = `0 0 ${svgWidth} ${svgHeight}`;

        const highConfidenceObjects = data.data.filter(obj => obj.confidence >= 0.6);

        if (highConfidenceObjects.length > 0) {
            // 1. Render SVG Polygons
            overlay.innerHTML = `
                <svg viewBox="${viewBox}" style="width:100%; height:100%; display:block;">
                    ${highConfidenceObjects.map(obj => `
                        <polygon 
                            id="poly-${obj.id}"
                            points="${obj.mask_polygon}" 
                            class="object-polygon pulse-once"
                            data-label="${obj.label}"
                            data-id="${obj.id}"
                            onclick="handleObjectClick(event, '${obj.id}', '${obj.label}', '${obj.mask_polygon}', '${imageId}')">
                            <title>${obj.label} (${Math.round(obj.confidence * 100)}%)</title>
                        </polygon>
                    `).join('')}
                </svg>
                <div id="smart-object-menu" class="object-menu hidden">
                    <div class="menu-header">
                        <span id="menu-label">Object</span>
                        <button onclick="closeSmartMenu()" class="menu-close">&times;</button>
                    </div>
                    <div class="menu-actions">
                        <button onclick="executeSearch()" class="menu-btn primary">
                            <span>🔍</span> Find Similar
                        </button>
                        <button onclick="executeExtract()" class="menu-btn secondary">
                            <span>✂️</span> Save to Dock
                        </button>
                    </div>
                </div>
            `;

            // 2. Add Spatial Chips to the list
            if (objectsList) {
                objectsList.classList.remove('hidden');
                const chipsWrapper = objectsList.querySelector('.chips-wrapper');

                // Group by label for deduplication
                const groupedElements = {};
                highConfidenceObjects.forEach(obj => {
                    if (!groupedElements[obj.label]) groupedElements[obj.label] = [];
                    groupedElements[obj.label].push(obj);
                });

                // Get current labels to avoid duplicates
                const existingLabels = new Set(Array.from(chipsWrapper.querySelectorAll('.object-chip')).map(c => c.textContent.toLowerCase()));

                Object.keys(groupedElements).forEach(label => {
                    // If a global tag already exists with this name, we might want to "upgrade" it 
                    // or just swap it. For now, let's just prepend spatial ones.

                    // Check for exact match in global tags and remove if found to avoid duplication
                    const globalMatch = Array.from(chipsWrapper.querySelectorAll('.object-chip.global'))
                        .find(c => c.textContent.toLowerCase() === label.toLowerCase());
                    if (globalMatch) globalMatch.remove();

                    const objs = groupedElements[label];
                    const chip = document.createElement('div');
                    chip.className = 'object-chip spatial';
                    chip.textContent = label;

                    chip.onmouseenter = () => {
                        objs.forEach(o => {
                            const poly = document.getElementById(`poly-${o.id}`);
                            if (poly) poly.classList.add('highlighted');
                        });
                    };
                    chip.onmouseleave = () => {
                        objs.forEach(o => {
                            const poly = document.getElementById(`poly-${o.id}`);
                            if (poly) poly.classList.remove('highlighted');
                        });
                    };

                    chip.onclick = (e) => {
                        const firstPoly = document.getElementById(`poly-${objs[0].id}`);
                        const rect = firstPoly ? firstPoly.getBoundingClientRect() : e.target.getBoundingClientRect();
                        const fakeEvent = {
                            clientX: rect.left + rect.width / 2,
                            clientY: rect.top + rect.height / 2,
                            stopPropagation: () => { }
                        };
                        handleObjectClick(fakeEvent, objs[0].id, label, objs[0].mask_polygon, imageId);
                    };

                    // Prepend spatial chips so they appear first
                    chipsWrapper.insertBefore(chip, chipsWrapper.firstChild);
                });

                const countAfter = chipsWrapper.querySelectorAll('.object-chip').length;
                if (countAfter > countBefore && window.isRefining) {
                    showNotification(`Deep Intelligence found ${countAfter - countBefore} new design elements!`);
                }
            }
        }
    } catch (err) {
        console.error("Error loading object masks:", err);
    }
}

// 3. The Refinement Trigger
window.refineImageAnalysis = async function (imageId) {
    const btn = document.querySelector('.refine-btn');
    if (!btn || btn.disabled) return;

    btn.disabled = true;
    window.isRefining = true;
    const originalHTML = btn.innerHTML;
    btn.innerHTML = `<span class="spinner">⏳</span> Intelligence Scan...`;

    try {
        showNotification('Initiating Deep Intelligence Scan (30-45s)...');

        // Add "keeping alive" notifications
        const statusMsgs = [
            "Analyzing spatial geometry...",
            "Classifying design elements...",
            "Extracting material palettes...",
            "Mapping architectural features..."
        ];
        let msgIndex = 0;
        const interval = setInterval(() => {
            if (window.isRefining && msgIndex < statusMsgs.length) {
                showToast(statusMsgs[msgIndex++]);
            }
        }, 8000);

        console.log(`Triggering deep analysis for ${imageId}...`);
        const res = await fetch(`${API_BASE}/images/${imageId}/refine`, {
            method: 'POST'
        });

        clearInterval(interval);

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `Server error: ${res.status}`);
        }

        const data = await res.json();

        if (data.status === 'success') {
            showNotification('Deep Intelligence Updated');

            // Refresh metadata from DB
            const refreshRes = await fetch(`${API_BASE}/images/details`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: [imageId] })
            });
            const refreshData = await refreshRes.json();

            if (refreshData.images && refreshData.images.length > 0) {
                const updatedImg = refreshData.images[0];
                // Update local cache
                currentResults[currentLightboxIndex] = updatedImg;
                // Re-render
                await renderImageObjects(updatedImg);
            }
        } else {
            showNotification('Analysis completed with warnings.');
        }
    } catch (err) {
        console.error("Refinement failed:", err);
        showNotification(`Intelligence Error: ${err.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHTML;
        }
        window.isRefining = false;
    }
}

// 2. The Interaction Handler (Opens the Menu)
window.handleObjectClick = function (event, id, label, polygonPoints, imageId) {
    event.stopPropagation(); // Stop lightbox from closing

    // Micro Preference Tracking
    trackPreference('elements', label);

    // Save state
    activeObjectData = { id, label, polygonPoints, imageId };

    const menu = document.getElementById('smart-object-menu');
    const menuLabel = document.getElementById('menu-label');

    if (menu) {
        menuLabel.textContent = label;
        // Simple positioning logic
        menu.style.left = `${event.clientX + 20}px`;
        menu.style.top = `${event.clientY}px`;

        menu.classList.remove('hidden');
    }
};
// 3. Action: Search (The "Find Similar" button)
window.executeSearch = async function () {
    if (!activeObjectData) return;

    showToast(`Searching for ${activeObjectData.label}s...`);
    closeSmartMenu();
    closeLightbox(); // Close modal to see results

    try {
        const res = await fetch(`${API_BASE}/search/by-object`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ object_id: activeObjectData.id, top_k: 50 })
        });
        const data = await res.json();

        // Update Grid
        document.getElementById('searchInput').value = `Visual Match: ${activeObjectData.label}`;
        updateGridWithFlip(data.results);

    } catch (e) {
        console.error("Search failed", e);
    }
};

// 4. Action: Extract (The "Save to Dock" button)
window.executeExtract = function () {
    if (!activeObjectData) return;

    showToast(`Extracting ${activeObjectData.label}...`);
    addToVisionDock(activeObjectData);
    closeSmartMenu();
};

window.closeSmartMenu = function () {
    const menu = document.getElementById('smart-object-menu');
    if (menu) {
        menu.classList.remove('visible');
        menu.classList.add('hidden');
    }
};

// 5. The Dock Logic (Adds the item to the bottom bar)
function addToVisionDock(objectData) {
    // Add to state if not exists
    const exists = visionCutouts.some(c => c.id === objectData.id);
    if (!exists) {
        visionCutouts.push(objectData);
        localStorage.setItem('visionCutouts', JSON.stringify(visionCutouts));
    }

    updateVisionUI();
    showToast(`Added ${objectData.label} to Vision Board`);
}

// 6. Auto-Ignition (Ensures it loads when lightbox opens)
const lightboxImgEl = document.getElementById('lightboxImage');
if (lightboxImgEl) {
    lightboxImgEl.addEventListener('load', function () {
        // Extract ID from src URL
        const urlParts = this.src.split('/');
        const imageId = urlParts[urlParts.length - 2];
        if (imageId && !isNaN(imageId)) {
            renderImageObjects(imageId);
        }
    });
}
// ==========================================


// --- VISION & ANALYSIS UTILS ---
function toggleVision() {
    const img = currentResults[currentLightboxIndex];
    toggleVisionFromCard(img.id);
}

window.toggleVisionFromCard = async function (id) {
    const idx = visionBoard.indexOf(id);
    if (idx === -1) {
        visionBoard.push(id);
        if (!imageCache[id]) {
            try {
                const res = await fetch(`${API_BASE}/images/details`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids: [id] })
                });
                const data = await res.json();
                if (data.images && data.images[0]) imageCache[id] = data.images[0];
            } catch (e) { console.error("Metadata fetch failed", e); }
        }
    } else {
        visionBoard.splice(idx, 1);
    }
    localStorage.setItem('visionBoard', JSON.stringify(visionBoard));
    updateVisionUI();
    updateLightboxUI();

    const card = resultsGrid.querySelector(`.card[data-id="${id}"]`);
    if (card) {
        const btn = card.querySelectorAll('.icon-btn')[1];
        const isSel = visionBoard.includes(id);
        btn.innerHTML = isSel ? ICONS.CHECK_CIRCLE : ICONS.PLUS;
        btn.classList.toggle('active', isSel);
    }
}

function updateVisionUI() {
    const dock = document.getElementById('vision-dock');
    const dockCount = document.getElementById('dock-count');
    const dockItems = document.getElementById('dock-items');
    const analysisSidebar = document.getElementById('analysis-sidebar');

    const totalCount = visionBoard.length + visionCutouts.length;

    if (totalCount > 0) {
        if (dock) {
            dock.classList.remove('hidden');
            dock.classList.add('visible');
        }
        if (analysisSidebar) analysisSidebar.classList.remove('hidden');
        if (dockCount) dockCount.textContent = totalCount;

        if (dockItems) {
            dockItems.innerHTML = '';

            // Render Full Images
            visionBoard.forEach(id => {
                const img = imageCache[id];
                if (!img) return;
                const thumbUrl = `/thumbnails/${img.thumbnail_path}`;
                const item = document.createElement('div');
                item.className = 'dock-item-wrapper full-image';
                item.innerHTML = `
                    <div class="dock-img-container">
                        <img src="${thumbUrl}" class="dock-full-img" alt="Gallery Image">
                    </div>
                    <span class="dock-label">Portfolio #${id}</span>
                    <button onclick="window.removeFromVision(${id})" class="dock-remove">&times;</button>
                `;
                dockItems.appendChild(item);
            });

            // Render Cutouts
            visionCutouts.forEach(data => {
                const imgUrl = `/api/image/${data.imageId}/raw`;
                const item = document.createElement('div');
                item.className = 'dock-item-wrapper cutout';
                item.innerHTML = `
                    <div class="dock-cutout-container">
                        <img src="${imgUrl}" class="dock-cutout-img" alt="${data.label}">
                    </div>
                    <span class="dock-label">${data.label}</span>
                    <button onclick="window.removeFromVisionCutout('${data.id}')" class="dock-remove">&times;</button>
                `;
                dockItems.appendChild(item);
            });

        }

        calculateLiveAnalysis();
    } else {
        if (dock) {
            dock.classList.add('hidden');
            dock.classList.remove('visible');
        }
        if (analysisSidebar) analysisSidebar.classList.add('hidden');
    }
}

window.removeFromVision = function (id) {
    const idx = visionBoard.indexOf(id);
    if (idx !== -1) {
        visionBoard.splice(idx, 1);
        localStorage.setItem('visionBoard', JSON.stringify(visionBoard));
        updateVisionUI();
        updateLightboxUI();

        // Refresh modal if open
        const modal = document.getElementById('vision-modal');
        if (modal && !modal.classList.contains('hidden')) {
            window.populateModalReview();
        }

        // Update card if visible
        const card = resultsGrid.querySelector(`.card[data-id="${id}"]`);
        if (card) {
            const btn = card.querySelectorAll('.icon-btn')[1];
            btn.innerHTML = ICONS.PLUS;
            btn.classList.remove('active');
        }
    }
};

window.removeFromVisionCutout = function (id) {
    visionCutouts = visionCutouts.filter(c => c.id !== id);
    localStorage.setItem('visionCutouts', JSON.stringify(visionCutouts));
    updateVisionUI();

    // Refresh modal if open
    const modal = document.getElementById('vision-modal');
    if (modal && !modal.classList.contains('hidden')) {
        window.populateModalReview();
    }
};

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

// --- PROJECT MODE ---
window.enterProjectMode = async function (slug) {
    if (!slug) return;
    isProjectMode = true;
    currentProjectSlug = slug;
    hasViewedProject = true;


    currentResults = [];
    resultsGrid.innerHTML = '<div class="loading">Architecting project...</div>';

    try {
        const res = await fetch(`${API_BASE}/projects/${slug}`);
        if (res.ok) {
            const project = await res.json();
            renderProjectHero(project);
        } else {
            renderProjectHero({ display_title: slug, location: 'Portfolio', description: '', awards: [] });
        }
    } catch (err) { console.error("Error fetching project metadata:", err); }

    await performSearch('', '');
    updateVisionMeter();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    if (lightbox) lightbox.classList.add('hidden');
}

window.exitProjectMode = function () {
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

// --- ANALYSIS ENGINE ---
let analysisDebounceTimer = null;
let lastAnalysisIds = "";

async function calculateLiveAnalysis(overrideImages = null) {
    const ids = overrideImages ? overrideImages.map(img => img.id) : visionBoard;
    const idsString = ids.sort().join(',');

    // Skip if nothing changed and not hovering
    if (!overrideImages && idsString === lastAnalysisIds) return;
    if (!overrideImages) lastAnalysisIds = idsString;

    const dominantEl = document.getElementById('dominant-style');
    const materialsEl = document.getElementById('materials-list');
    const privacyEl = document.getElementById('privacy-val');
    const terrainEl = document.getElementById('terrain-val');
    const balanceEl = document.getElementById('balance-val');
    const spatialEl = document.getElementById('spatial-intent-list');

    if (ids.length === 0) {
        if (dominantEl) dominantEl.textContent = '---';
        if (materialsEl) materialsEl.textContent = '---';
        if (privacyEl) privacyEl.textContent = '---';
        if (terrainEl) terrainEl.textContent = '---';
        if (balanceEl) balanceEl.textContent = '---';
        if (spatialEl) spatialEl.textContent = '---';
        return;
    }

    // Debounce the heavy lifting
    clearTimeout(analysisDebounceTimer);
    analysisDebounceTimer = setTimeout(async () => {
        try {
            const res = await fetch(`${API_BASE}/vision/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_ids: ids })
            });
            const analysis = await res.json();

            if (analysis.error) throw new Error(analysis.error);

            // 1. Dominant Style (Theme)
            if (dominantEl) {
                const primaryTheme = analysis.themes?.[0]?.name || "Architectural Discovery";
                dominantEl.textContent = primaryTheme;
            }

            // 2. Primary Materials
            if (materialsEl) {
                const mats = analysis.materials?.slice(0, 3).join(', ') || "Awaiting Data";
                materialsEl.textContent = mats;
            }

            // 3. Site Dynamics (Site Intelligence)
            if (privacyEl) privacyEl.textContent = analysis.privacy_level || (ids.length === 1 ? (overrideImages[0].privacy_level || "Standard") : "Mixed");
            if (terrainEl) terrainEl.textContent = analysis.terrain_type || (ids.length === 1 ? (overrideImages[0].terrain_type || "Standard") : "Mixed");
            if (balanceEl) balanceEl.textContent = analysis.hardscape_ratio || (ids.length === 1 ? (overrideImages[0].hardscape_ratio || "Balanced") : "Mixed");

            // 4. Spatial Intent
            if (spatialEl) {
                const intents = analysis.top_elements?.filter(e => e.category === 'spatial_purpose' || e.category === 'layout').slice(0, 3).map(e => e.label).join(', ') || "Curating Flow...";
                spatialEl.textContent = intents;
            }

            // Global update for brief
            window.currentVisionAnalysis = analysis;
            updateVisionMeter();

        } catch (err) {
            console.warn("Analysis failed:", err);
        }
    }, 150);
}

// --- ARCHETYPES ---
function handleArchetypeClick(label) {
    activeArchetype = label;
    activeChips.clear();
    const header = document.querySelector('.header');
    if (header) {
        const top = header.getBoundingClientRect().top + window.pageYOffset;
        window.scrollTo({ top: top, behavior: 'smooth' });
    }
    renderSmartChips();
    performSearch();
    updateVisionMeter();
}

function renderSmartChips() {
    const container = document.getElementById('smart-chips-container');
    if (!container) return;
    // Removed config dependency for debugging
    container.classList.remove('hidden');
    container.innerHTML = `
        <div class="context-bridge" style="width: 100%; margin-bottom: 1.5rem;">
            <!-- Removed 'Search for' suggestions per user request -->
        </div>
    `;
}

window.toggleChip = function (chip) {
    if (activeChips.has(chip)) activeChips.delete(chip);
    else activeChips.add(chip);
    renderSmartChips();
    performSearch();
    updateVisionMeter();
};

function updateVisionMeter() {
    const scoreEl = document.getElementById('vision-score');
    const fillEl = document.getElementById('vision-meter-fill');
    if (!scoreEl || !fillEl) return;

    let score = 0;
    if (activeArchetype) score += 20;
    score += Math.min(visionBoard.length * 15, 60);
    if (hasViewedProject) score += 20;

    score = Math.min(score, 100);
    scoreEl.textContent = `${score}%`;
    fillEl.style.width = `${score}%`;

    // Stages
    fillEl.classList.remove('low', 'mid', 'high');
    if (score >= 90) fillEl.classList.add('high');
    else if (score >= 40) fillEl.classList.add('mid');
    else fillEl.classList.add('low');

    // Finalize button state
    const finalizeBtn = document.getElementById('finalize-vision-trigger');
    if (finalizeBtn) {
        if (score >= 100) {
            finalizeBtn.classList.add('active');
            finalizeBtn.disabled = false;
        } else {
            finalizeBtn.classList.remove('active');
            // User requested to FIX it, but original code might have allowed it earlier?
            // "Finalize Brief once again connected to user's clicks"
        }
    }
}



window.copyBriefToClipboard = function () {
    const analysis = window.currentVisionAnalysis;
    if (!analysis || !analysis.sales_brief) {
        showToast("We need a few more selections to generate your brief...");
        return;
    }

    const briefText = analysis.sales_brief;

    navigator.clipboard.writeText(briefText).then(() => {
        showToast("Design Brief copied to clipboard!");
        window.openVisionModal();
    }).catch(err => {
        console.warn('Clipboard access denied, opening modal anyway.');
        window.openVisionModal();
    });
};

window.submitLead = function (event) {
    if (event) event.preventDefault();
    const name = document.getElementById('lead-name')?.value;
    const email = document.getElementById('lead-email')?.value;

    showToast(`Thank you, ${name}! Your vision is being processed.`);

    // Simulate API call delay
    const btn = document.getElementById('submitVisionBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Submitting...';
    }

    setTimeout(() => {
        window.closeVisionModal();
        showToast("Vision Board Finalized & Sent!");
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Finalize Vision';
        }
    }, 1500);
};


window.openVisionModal = function () {
    const modal = document.getElementById('vision-modal');
    if (modal) {
        modal.classList.remove('hidden');
        window.populateModalReview();
    }
};

window.populateModalReview = function () {
    const list = document.getElementById('modal-review-list');
    if (!list) return;

    list.innerHTML = '';

    // Full Images
    visionBoard.forEach(id => {
        const img = imageCache[id];
        if (!img) return;
        const thumbUrl = `/thumbnails/${img.thumbnail_path}`;
        const item = document.createElement('div');
        item.className = 'review-item';
        item.innerHTML = `
            <img src="${thumbUrl}" class="review-thumb" alt="Portfolio Image">
            <div class="review-inputs">
                <span style="font-size: 0.8rem; font-weight: 600;">Portfolio #${id}</span>
                <input type="text" class="note-input" placeholder="Add a specific note about this style...">
            </div>
            <button class="remove-btn" onclick="window.removeFromVision(${id})">&times;</button>
        `;
        list.appendChild(item);
    });

    // Color/Cutouts
    visionCutouts.forEach(data => {
        const imgUrl = `/api/image/${data.imageId}/raw`;
        const item = document.createElement('div');
        item.className = 'review-item';
        item.innerHTML = `
            <img src="${imgUrl}" class="review-thumb" style="object-fit: contain; background: #eee; padding: 4px;" alt="${data.label}">
            <div class="review-inputs">
                <span style="font-size: 0.8rem; font-weight: 600;">Detail: ${data.label}</span>
                <input type="text" class="note-input" placeholder="Note about this material/detail...">
            </div>
            <button class="remove-btn" onclick="window.removeFromVisionCutout('${data.id}')">&times;</button>
        `;
        list.appendChild(item);
    });

    if (visionBoard.length === 0 && visionCutouts.length === 0) {
        list.innerHTML = '<p style="text-align: center; color: #999; padding: 2rem;">No items selected yet.</p>';
    }
};

window.closeVisionModal = function () {
    const modal = document.getElementById('vision-modal');
    if (modal) modal.classList.add('hidden');
};

// Initial Run
try {
    init();
} catch (err) { console.error("Init failed:", err); }

// --- DRAWER ---
window.toggleMobileDrawer = function () {
    const sidebar = document.getElementById('analysis-sidebar');
    const backdrop = document.getElementById('drawer-backdrop');
    if (!sidebar || !backdrop) return;
    sidebar.classList.toggle('active');
    backdrop.classList.toggle('active');
};
const backdrop = document.getElementById('drawer-backdrop');
if (backdrop) {
    backdrop.onclick = function () {
        const sidebar = document.getElementById('analysis-sidebar');
        if (sidebar) sidebar.classList.remove('active');
        this.classList.remove('active');
    };
}