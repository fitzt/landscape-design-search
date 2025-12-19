/* ... existing init stuff ... */
const API_BASE = '/api';

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
    try {
        await loadFolders();
        await loadCollections();
        updateVisionUI();

        // Ensure Onboarding is visible state
        resultsGrid.innerHTML = ONBOARDING_HTML;
        currentResults = [];

    } catch (e) {
        console.error("Init Error:", e);
        alert("Init Error: " + e.message);
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

// Onboarding HTML
const ONBOARDING_HTML = `
<div class="empty-state">
    <div class="onboarding-guide">
        <h2>Build Your Vision Board</h2>
        <p class="guide-subtitle">Follow these steps to create a design profile for our architects.</p>
        <div class="steps-grid">
            <div class="step-card">
                <div class="step-icon">1</div>
                <h3>Search</h3>
                <p>Start with a broad term like "Pool", "Patio", or "Retaining Wall".</p>
            </div>
            <div class="step-card">
                <div class="step-icon">2</div>
                <h3>Refine 🔍</h3>
                <p>Click the <b>Magnifying Glass</b> on any image to find visually similar styles.</p>
            </div>
            <div class="step-card">
                <div class="step-icon">3</div>
                <h3>Collect ❤️</h3>
                <p>Tap the <b>Heart</b> to save images that match your dream landscape.</p>
            </div>
            <div class="step-card">
                <div class="step-icon">4</div>
                <h3>Analyze 🧠</h3>
                <p>Click "Start Project Vision" to get your <b>AI Design Report</b>.</p>
            </div>
        </div>
    </div>
</div>
`;

// New state for FLIP
let isReflowing = false;

async function performSearch() {
    console.log("performSearch called");
    const query = searchInput.value.trim();
    const folder = folderFilter.value;

    // "Empty State" Check
    if (!query && !folder) {
        resultsGrid.innerHTML = ONBOARDING_HTML;
        currentResults = [];
        return;
    }

    // Allow empty query
    const res = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query: query || "",
            top_k: 24,
            folder: folder || null
        })
    });
    const data = await res.json();
    updateGridWithFlip(data.results);
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

        // Image Click -> Lightbox
        // But we need a separate button for "Find Similar"

        const thumbUrl = `/thumbnails/${img.thumbnail_path}`;
        const inVision = visionBoard.includes(img.id);
        const visionIcon = inVision ? '✨' : '';

        // Card HTML
        // NOTE: onclick="event.stopPropagation()" is crucial for buttons inside the card

        const isSelected = visionBoard.includes(img.id);
        const heartClass = isSelected ? 'active' : '';
        const heartIcon = isSelected ? '❤️' : '🤍';

        card.innerHTML = `
            <img src="${thumbUrl}" loading="lazy" alt="${img.filename}">
            <div class="card-overlay">
                <div class="card-actions">
                    <button class="icon-btn" onclick="event.stopPropagation(); triggerSimilaritySearch(${img.id})" title="Find Similar">
                        🔍
                    </button>
                    <button class="icon-btn ${heartClass}" onclick="event.stopPropagation(); toggleVisionFromCard(${img.id})" title="Add to Vision">
                        ${heartIcon}
                    </button>
                </div>
            </div>
        `;
        // Main click -> Lightbox
        card.onclick = () => openLightbox(index);

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
    lightboxFav.classList.toggle('active', !!img.favorite);

    let visionBtn = document.getElementById('lightboxVision');
    if (!visionBtn) {
        visionBtn = document.createElement('button');
        visionBtn.id = 'lightboxVision';
        visionBtn.className = 'control-btn';
        lightboxFav.parentNode.insertBefore(visionBtn, lightboxFav.nextSibling);
        visionBtn.onclick = toggleVision;
    }
    const inVision = visionBoard.includes(img.id);
    visionBtn.textContent = inVision ? "✨ In Vision" : "+ Add to Vision";
    visionBtn.classList.toggle('active', inVision);

    // New: Find Similar in Lightbox
    let similarBtn = document.getElementById('lightboxSimilar');
    if (!similarBtn) {
        similarBtn = document.createElement('button');
        similarBtn.id = 'lightboxSimilar';
        similarBtn.className = 'control-btn';
        similarBtn.textContent = "🔍 Find Similar";
        lightboxFav.parentNode.insertBefore(similarBtn, lightboxFav.nextSibling); // Insert before Vision? Or after?
        // Let's Insert after Fav, before Vision to group actions
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
window.toggleVisionFromCard = function (id) {
    console.log("toggleVisionFromCard called with ID:", id);
    const idx = visionBoard.indexOf(id);
    if (idx === -1) {
        visionBoard.push(id);
    } else {
        visionBoard.splice(idx, 1);
    }
    localStorage.setItem('visionBoard', JSON.stringify(visionBoard));

    updateVisionUI(); // Updates Dock
    updateLightboxUI(); // Updates Modal if open

    // Update Card UI directly without full re-render
    // Find card with data-id
    const card = resultsGrid.querySelector(`.card[data-id="${id}"]`);
    if (card) {
        // Find the heart button
        const btn = card.querySelectorAll('.icon-btn')[1]; // 2nd button
        const isSel = visionBoard.includes(id);
        btn.innerHTML = isSel ? '❤️' : '🤍';
        btn.classList.toggle('active', isSel);
    }
}

function updateVisionUI() {
    const cnt = visionBoard.length;
    // Update Dock
    const dock = document.getElementById('vision-dock');
    const dockCount = document.getElementById('dock-count');
    const dockItems = document.getElementById('dock-items');

    dockCount.innerText = cnt;
    dock.classList.toggle('visible', cnt > 0);

    // Render Dock Items
    dockItems.innerHTML = '';
    visionBoard.forEach(id => {
        // Find img data (might need cache if not in currentResults)
        // For now, if not in current results, we might show a placeholder or try to find it.
        // We really need a global cache of loaded images for this to be perfect.
        // Or just use what we have.
        let img = currentResults.find(r => r.id === id);

        // If not in currentResults, check visionDetailsCache (from modal logic) or just use placeholder?
        // Let's use visionDetailsCache if available.
        if (!img && visionDetailsCache[id]) img = visionDetailsCache[id];

        if (img) {
            const thumb = document.createElement('img');
            thumb.src = `/thumbnails/${img.thumbnail_path}`;
            thumb.className = 'dock-thumb';
            thumb.title = "Click to remove";
            thumb.onclick = () => toggleVisionFromCard(id); // Clicking removes it
            dockItems.appendChild(thumb);
        } else {
            // Fetch it? Or just show generic
            // const span = document.createElement('span');
            // span.innerText = `#${id}`;
            // dockItems.appendChild(span);
        }
    });
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
let visionDetailsCache = {};
let visionNotes = JSON.parse(localStorage.getItem('visionNotes')) || {};
let currentVisionAnalysis = null;

window.openVisionModal = async function () {
    if (visionBoard.length === 0) return;
    visionModal.classList.remove('hidden');

    // Fetch Details for ALL IDs in the board
    try {
        const res = await fetch(`${API_BASE}/images/details`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: visionBoard })
        });
        const data = await res.json();

        // Update Cache
        data.images.forEach(img => {
            visionDetailsCache[img.id] = img;
        });
    } catch (e) {
        console.error("Failed to fetch vision details", e);
    }

    renderReviewList();

    // Fetch and render vision analysis
    await fetchVisionAnalysis();
}

async function fetchVisionAnalysis() {
    const analysisPanel = document.getElementById('vision-analysis-panel');
    const loadingEl = document.getElementById('analysis-loading');
    const contentEl = document.getElementById('analysis-content');

    if (visionBoard.length < 3) {
        // Hide analysis for small boards
        analysisPanel.classList.add('hidden');
        return;
    }

    // Show panel and loading state
    analysisPanel.classList.remove('hidden');
    loadingEl.classList.remove('hidden');
    contentEl.classList.add('hidden');

    try {
        const res = await fetch(`${API_BASE}/vision/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_ids: visionBoard })
        });

        if (!res.ok) throw new Error('Analysis failed');

        currentVisionAnalysis = await res.json();

        // Hide loading, show content
        loadingEl.classList.add('hidden');
        contentEl.classList.remove('hidden');

        // Render analysis
        renderVisionAnalysis(currentVisionAnalysis);

    } catch (e) {
        console.error("Vision analysis error:", e);
        loadingEl.innerHTML = '<p style="color: #ef4444;">Analysis unavailable</p>';
    }
}

function renderVisionAnalysis(analysis) {
    // Render Themes
    const themesContainer = document.getElementById('themes-container');
    themesContainer.innerHTML = '';

    if (analysis.themes && analysis.themes.length > 0) {
        analysis.themes.slice(0, 3).forEach(theme => {
            const chip = document.createElement('div');
            chip.className = 'theme-chip';
            chip.innerHTML = `
                <span class="theme-name">${theme.name}</span>
                <span class="theme-confidence">${Math.round(theme.confidence * 100)}%</span>
            `;
            themesContainer.appendChild(chip);
        });
    }

    // Render Top Elements
    const elementsContainer = document.getElementById('elements-container');
    elementsContainer.innerHTML = '';

    if (analysis.top_elements && analysis.top_elements.length > 0) {
        analysis.top_elements.slice(0, 6).forEach(elem => {
            const chip = document.createElement('div');
            chip.className = 'element-chip';
            chip.innerHTML = `
                <span class="element-label">${elem.label}</span>
                <span class="element-count">${elem.count}/${analysis.total_images} (${elem.percentage}%)</span>
            `;
            elementsContainer.appendChild(chip);
        });
    }

    // Render Materials
    const materialsContainer = document.getElementById('materials-container');
    materialsContainer.innerHTML = '';

    if (analysis.materials && analysis.materials.length > 0) {
        analysis.materials.forEach(material => {
            const chip = document.createElement('span');
            chip.className = 'tag-chip';
            chip.textContent = material;
            materialsContainer.appendChild(chip);
        });
    } else {
        materialsContainer.innerHTML = '<span class="tag-chip" style="opacity: 0.5;">No materials detected</span>';
    }

    // Render Planting
    const plantingContainer = document.getElementById('planting-container');
    plantingContainer.innerHTML = '';

    if (analysis.planting_signals && analysis.planting_signals.length > 0) {
        analysis.planting_signals.forEach(plant => {
            const chip = document.createElement('span');
            chip.className = 'tag-chip';
            chip.textContent = plant;
            plantingContainer.appendChild(chip);
        });
    } else {
        plantingContainer.innerHTML = '<span class="tag-chip" style="opacity: 0.5;">No planting detected</span>';
    }

    // Render Insights
    const insightsContainer = document.getElementById('insights-container');
    insightsContainer.innerHTML = '';

    if (analysis.unconscious_patterns && analysis.unconscious_patterns.length > 0) {
        analysis.unconscious_patterns.forEach(insight => {
            const item = document.createElement('div');
            item.className = 'insight-item';
            item.textContent = insight;
            insightsContainer.appendChild(item);
        });
    }
}

window.copyBriefToClipboard = async function () {
    if (!currentVisionAnalysis || !currentVisionAnalysis.sales_brief) {
        alert('No analysis available to copy');
        return;
    }

    try {
        await navigator.clipboard.writeText(currentVisionAnalysis.sales_brief);

        // Visual feedback
        const btn = document.getElementById('copy-brief-btn');
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓ Copied!';
        btn.style.background = '#10b981';

        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.background = '#111';
        }, 2000);

    } catch (e) {
        console.error('Copy failed:', e);
        alert('Failed to copy. Please try again.');
    }
}

async function renderReviewList() {
    visionReviewList.innerHTML = '';

    visionBoard.forEach(id => {
        let img = visionDetailsCache[id];
        if (!img) img = currentResults.find(r => r.id === id);

        const thumbUrl = img ? `/thumbnails/${img.thumbnail_path}` : 'logo.jpg';
        const currentNote = visionNotes[id] || "";

        const item = document.createElement('div');
        item.className = 'review-item';
        item.innerHTML = `
            <img src="${thumbUrl}" class="review-thumb">
            <div class="review-inputs">
                <input type="text" 
                    placeholder="Why this one? (e.g. Love the firepit)" 
                    class="note-input"
                    data-id="${id}"
                    value="${currentNote}"
                    oninput="saveNoteLocal(${id}, this.value)">
            </div>
            <button class="remove-btn" onclick="removeFromVision(${id})">&times;</button>
        `;
        visionReviewList.appendChild(item);
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
