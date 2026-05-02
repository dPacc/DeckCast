/* ============================================================
   DeckCast — Web UI Application
   ============================================================ */

const App = (() => {
  'use strict';

  // ---- State ----
  let clips = [];
  let folders = [];
  let currentFolder = null; // null = "All Recordings"
  let searchQuery = '';
  let sortBy = 'date';
  let sortOrder = 'desc';
  let selectedClips = new Set();
  let contextClipId = null;
  let inlineEditClipId = null;
  let isLoading = true;

  // ---- DOM Cache ----
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => [...(root || document).querySelectorAll(sel)];

  const dom = {};
  function cacheDom() {
    dom.header = $('#header');
    dom.clipGrid = $('#clip-grid');
    dom.emptyState = $('#empty-state');
    dom.sidebarNav = $('#sidebar-nav');
    dom.sidebar = $('#sidebar');
    dom.sidebarOverlay = $('#sidebar-overlay');
    dom.hamburgerBtn = $('#hamburger-btn');
    dom.sidebarClose = $('#sidebar-close');
    dom.searchInput = $('#search-input');
    dom.searchClear = $('#search-clear');
    dom.sortSelect = $('#sort-select');
    dom.refreshBtn = $('#refresh-btn');
    dom.settingsBtn = $('#settings-btn');
    dom.bulkBar = $('#bulk-bar');
    dom.bulkCount = $('#bulk-count');
    dom.selectAllCheckbox = $('#select-all-checkbox');
    dom.bulkMoveBtn = $('#bulk-move-btn');
    dom.bulkDeleteBtn = $('#bulk-delete-btn');
    dom.bulkCancelBtn = $('#bulk-cancel-btn');
    dom.contextMenu = $('#context-menu');
    dom.newFolderBtn = $('#new-folder-btn');
    dom.toastContainer = $('#toast-container');

    // Dialogs
    dom.renameDialog = $('#rename-dialog');
    dom.renameInput = $('#rename-input');
    dom.renameCancel = $('#rename-cancel');
    dom.renameSave = $('#rename-save');

    dom.deleteDialog = $('#delete-dialog');
    dom.deleteMessage = $('#delete-message');
    dom.deleteCancel = $('#delete-cancel');
    dom.deleteConfirm = $('#delete-confirm');

    dom.folderDialog = $('#folder-dialog');
    dom.folderNameInput = $('#folder-name-input');
    dom.folderCancel = $('#folder-cancel');
    dom.folderCreate = $('#folder-create');

    dom.moveDialog = $('#move-dialog');
    dom.folderPicker = $('#folder-picker');
    dom.moveCancel = $('#move-cancel');

    dom.settingsDialog = $('#settings-dialog');
    dom.settingsClose = $('#settings-close');
    dom.uploadZone = $('#upload-zone');
    dom.secretsFileInput = $('#secrets-file-input');
    dom.ytStatus = $('#yt-status');
    dom.ytStatusIndicator = $('#yt-status-indicator');
    dom.ytStatusText = $('#yt-status-text');

    dom.videoLightbox = $('#video-lightbox');
    dom.lightboxClose = $('#lightbox-close');
    dom.lightboxVideo = $('#lightbox-video');
    dom.lightboxTitle = $('#lightbox-title');
    dom.lightboxMeta = $('#lightbox-meta');

    dom.liveIndicator = $('#live-indicator');
  }

  // ============================================================
  // API
  // ============================================================

  async function api(method, path, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(path, opts);
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(text || `HTTP ${res.status}`);
    }
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) return res.json();
    return null;
  }

  async function fetchClips(folderId) {
    let url = '/api/clips';
    const params = [];
    if (folderId) params.push(`folder=${encodeURIComponent(folderId)}`);
    if (params.length) url += '?' + params.join('&');
    return api('GET', url);
  }

  async function fetchFolders() {
    return api('GET', '/api/folders');
  }

  async function renameClip(clipId, newName) {
    return api('PUT', `/api/clips/${encodeURIComponent(clipId)}/rename`, { name: newName });
  }

  async function deleteClip(clipId) {
    return api('DELETE', `/api/clips/${encodeURIComponent(clipId)}`, { confirm: true });
  }

  async function createFolder(name) {
    return api('POST', '/api/folders', { name });
  }

  async function renameFolder(folderId, newName) {
    return api('PUT', `/api/folders/${encodeURIComponent(folderId)}`, { name: newName });
  }

  async function deleteFolder(folderId) {
    return api('DELETE', `/api/folders/${encodeURIComponent(folderId)}`);
  }

  async function assignClipsToFolder(folderId, clipIds) {
    return api('POST', `/api/folders/${encodeURIComponent(folderId)}/clips`, { clip_ids: clipIds });
  }

  async function removeClipsFromFolder(folderId, clipIds) {
    return api('DELETE', `/api/folders/${encodeURIComponent(folderId)}/clips`, { clip_ids: clipIds });
  }

  async function uploadClientSecrets(file) {
    const text = await file.text();
    const json = JSON.parse(text);
    return api('POST', '/api/youtube/client-secrets', json);
  }

  async function checkClientSecretsStatus() {
    return api('GET', '/api/youtube/client-secrets/status');
  }

  // ============================================================
  // Utility
  // ============================================================

  function formatSize(bytes) {
    if (bytes == null || bytes === 0) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
    return (bytes / 1073741824).toFixed(2) + ' GB';
  }

  function formatDuration(seconds) {
    if (!seconds || seconds <= 0) return '0:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    const sp = s < 10 ? '0' + s : '' + s;
    if (h > 0) {
      const mp = m < 10 ? '0' + m : '' + m;
      return h + ':' + mp + ':' + sp;
    }
    return m + ':' + sp;
  }

  function formatDate(timestamp) {
    if (!timestamp) return '';
    const d = new Date(timestamp * 1000);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
    if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
    if (diff < 604800000) return Math.floor(diff / 86400000) + 'd ago';
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function clipId(clip) {
    return clip.id || clip.filename || clip.path;
  }

  function escapeHtml(str) {
    const el = document.createElement('span');
    el.textContent = str;
    return el.innerHTML;
  }

  // ============================================================
  // Filtering & Sorting
  // ============================================================

  function getFilteredClips() {
    let result = clips.slice();

    // Search filter
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(c =>
        (c.filename || '').toLowerCase().includes(q) ||
        (c.original_filename || '').toLowerCase().includes(q) ||
        (c.game || '').toLowerCase().includes(q) ||
        formatDate(c.modified).toLowerCase().includes(q)
      );
    }

    // Sort
    result.sort((a, b) => {
      let va, vb;
      switch (sortBy) {
        case 'date':
          va = a.modified || 0;
          vb = b.modified || 0;
          break;
        case 'size':
          va = a.size || 0;
          vb = b.size || 0;
          break;
        case 'name':
          va = (a.filename || a.original_filename || '').toLowerCase();
          vb = (b.filename || b.original_filename || '').toLowerCase();
          return sortOrder === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
        case 'game':
          va = (a.game || '').toLowerCase();
          vb = (b.game || '').toLowerCase();
          return sortOrder === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
        default:
          va = a.modified || 0;
          vb = b.modified || 0;
      }
      return sortOrder === 'asc' ? va - vb : vb - va;
    });

    return result;
  }

  // ============================================================
  // Rendering
  // ============================================================

  function renderSkeletons(count) {
    dom.clipGrid.innerHTML = '';
    dom.emptyState.classList.add('hidden');
    const tpl = $('#skeleton-card-template');
    for (let i = 0; i < count; i++) {
      const clone = tpl.content.cloneNode(true);
      dom.clipGrid.appendChild(clone);
    }
  }

  function renderClipGrid() {
    const filtered = getFilteredClips();
    dom.clipGrid.innerHTML = '';

    if (filtered.length === 0) {
      dom.emptyState.classList.remove('hidden');
      return;
    }

    dom.emptyState.classList.add('hidden');
    const tpl = $('#clip-card-template');

    filtered.forEach(clip => {
      const clone = tpl.content.cloneNode(true);
      const card = clone.querySelector('.clip-card');
      const id = clipId(clip);

      card.dataset.clipId = id;

      // Checkbox
      const checkbox = card.querySelector('.clip-checkbox');
      checkbox.checked = selectedClips.has(id);
      if (selectedClips.has(id)) card.classList.add('selected');

      checkbox.addEventListener('change', () => {
        if (checkbox.checked) {
          selectedClips.add(id);
          card.classList.add('selected');
        } else {
          selectedClips.delete(id);
          card.classList.remove('selected');
        }
        updateBulkBar();
      });

      // Thumbnail
      const thumbImg = card.querySelector('.clip-thumb-img');
      const thumbArea = card.querySelector('.clip-thumb');
      if (clip.thumbnail_url) {
        thumbImg.src = clip.thumbnail_url;
        thumbImg.alt = clip.filename || clip.original_filename;
      } else {
        thumbImg.src = `/api/clips/${encodeURIComponent(id)}/thumbnail`;
        thumbImg.alt = clip.filename || clip.original_filename;
      }
      thumbImg.onerror = function() {
        this.style.display = 'none';
        thumbArea.style.background = 'linear-gradient(135deg, var(--bg-input), var(--bg-hover))';
      };

      // Click thumbnail for preview
      thumbArea.addEventListener('click', () => showVideoPreview(clip));

      // Duration badge
      const durBadge = card.querySelector('.badge-duration');
      durBadge.textContent = formatDuration(clip.duration);

      // Game badge
      const gameBadge = card.querySelector('.badge-game');
      gameBadge.textContent = clip.game || 'Unknown Game';

      // Clip name (clickable to rename inline)
      const nameEl = card.querySelector('.clip-name');
      nameEl.textContent = clip.filename || clip.original_filename;
      nameEl.addEventListener('click', (e) => {
        e.stopPropagation();
        startInlineRename(card, clip);
      });
      nameEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          startInlineRename(card, clip);
        }
      });

      // Meta
      card.querySelector('.clip-size').textContent = formatSize(clip.size);
      card.querySelector('.clip-date').textContent = formatDate(clip.modified);

      // Download button — use clip ID for most reliable matching
      const dlBtn = card.querySelector('.clip-download');
      dlBtn.href = `/download/${encodeURIComponent(id)}`;
      dlBtn.setAttribute('download', '');

      // More button (context menu)
      const moreBtn = card.querySelector('.clip-more');
      moreBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        showContextMenu(e.clientX, e.clientY, id);
      });

      // Right-click context menu
      card.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showContextMenu(e.clientX, e.clientY, id);
      });

      // Drag & drop
      card.addEventListener('dragstart', (e) => handleDragStart(e, id));
      card.addEventListener('dragend', handleDragEnd);

      dom.clipGrid.appendChild(clone);
    });

    // Apply bulk mode class
    if (selectedClips.size > 0) {
      dom.clipGrid.classList.add('bulk-mode');
    } else {
      dom.clipGrid.classList.remove('bulk-mode');
    }
  }

  function renderFolderSidebar() {
    dom.sidebarNav.innerHTML = '';

    // "All Recordings" item
    const allItem = createFolderElement(null, 'All Recordings', clips.length);
    if (currentFolder === null) allItem.classList.add('active');
    allItem.querySelector('.folder-icon').innerHTML = '<rect x="2" y="4" width="20" height="14" rx="3" stroke="currentColor" stroke-width="2" fill="none"/><path d="M9 8.5L16 12L9 15.5V8.5Z" fill="currentColor"/>';
    dom.sidebarNav.appendChild(allItem);

    // Folder items
    folders.forEach(folder => {
      const count = folder.clip_count || (folder.clips ? folder.clips.length : 0);
      const item = createFolderElement(folder.id, folder.name, count);
      if (currentFolder === folder.id) item.classList.add('active');
      dom.sidebarNav.appendChild(item);
    });
  }

  function createFolderElement(folderId, name, count) {
    const tpl = $('#folder-item-template');
    const clone = tpl.content.cloneNode(true);
    const item = clone.querySelector('.folder-item');

    item.dataset.folderId = folderId || '';
    item.querySelector('.folder-name').textContent = name;
    item.querySelector('.folder-count').textContent = count;

    item.addEventListener('click', (e) => {
      e.preventDefault();
      currentFolder = folderId;
      closeSidebar();
      loadClips();
    });

    // Drag-over for folder drop target
    if (folderId) {
      item.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        item.classList.add('drag-over');
      });

      item.addEventListener('dragleave', () => {
        item.classList.remove('drag-over');
      });

      item.addEventListener('drop', (e) => {
        e.preventDefault();
        item.classList.remove('drag-over');
        handleDrop(e, folderId);
      });
    }

    return item;
  }

  function renderEmptyState() {
    dom.clipGrid.innerHTML = '';
    dom.emptyState.classList.remove('hidden');
  }

  // ============================================================
  // Inline Rename
  // ============================================================

  function startInlineRename(card, clip) {
    const id = clipId(clip);
    if (inlineEditClipId === id) return;
    cancelInlineRename();
    inlineEditClipId = id;

    const nameEl = card.querySelector('.clip-name');
    const currentName = clip.filename || clip.original_filename;
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'clip-name-input';
    input.value = currentName;

    nameEl.replaceWith(input);
    input.focus();
    input.select();

    function commit() {
      const newName = input.value.trim();
      if (newName && newName !== currentName) {
        doRenameClip(id, newName);
      }
      endEdit();
    }

    function endEdit() {
      inlineEditClipId = null;
      const newNameEl = document.createElement('h3');
      newNameEl.className = 'clip-name';
      newNameEl.tabIndex = 0;
      newNameEl.setAttribute('role', 'button');
      newNameEl.setAttribute('aria-label', 'Click to rename');
      newNameEl.textContent = input.value.trim() || (clip.filename || clip.original_filename);
      input.replaceWith(newNameEl);
      newNameEl.addEventListener('click', (e) => {
        e.stopPropagation();
        const parentCard = newNameEl.closest('.clip-card');
        startInlineRename(parentCard, clip);
      });
      newNameEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const parentCard = newNameEl.closest('.clip-card');
          startInlineRename(parentCard, clip);
        }
      });
    }

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        commit();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        endEdit();
      }
    });

    input.addEventListener('blur', () => {
      // Small delay to allow Enter keydown to process first
      setTimeout(() => {
        if (inlineEditClipId === id) commit();
      }, 100);
    });
  }

  function cancelInlineRename() {
    if (inlineEditClipId) {
      // Force re-render to reset inline edits
      inlineEditClipId = null;
    }
  }

  // ============================================================
  // Dialogs
  // ============================================================

  function openDialog(dialog) {
    dialog.showModal();
  }

  function closeDialog(dialog) {
    dialog.close();
  }

  // -- Rename Dialog (fallback for context menu) --
  let renameTargetId = null;

  function showRenameDialog(id, currentName) {
    renameTargetId = id;
    dom.renameInput.value = currentName;
    openDialog(dom.renameDialog);
    setTimeout(() => {
      dom.renameInput.focus();
      dom.renameInput.select();
    }, 50);
  }

  function handleRenameSave() {
    const newName = dom.renameInput.value.trim();
    if (!newName || !renameTargetId) {
      closeDialog(dom.renameDialog);
      return;
    }
    doRenameClip(renameTargetId, newName);
    closeDialog(dom.renameDialog);
  }

  async function doRenameClip(id, newName) {
    try {
      await renameClip(id, newName);
      // Update local state — server returns display name in .filename
      const clip = clips.find(c => clipId(c) === id);
      if (clip) {
        clip.filename = newName;
      }
      renderClipGrid();
      showToast('Renamed successfully');
    } catch (err) {
      showToast('Failed to rename: ' + err.message, 'error');
    }
  }

  // -- Delete Dialog --
  let deleteTargetIds = [];

  function showDeleteDialog(ids, displayName) {
    deleteTargetIds = Array.isArray(ids) ? ids : [ids];
    if (deleteTargetIds.length === 1) {
      dom.deleteMessage.textContent = `Are you sure you want to permanently delete "${displayName}"? This cannot be undone.`;
    } else {
      dom.deleteMessage.textContent = `Are you sure you want to permanently delete ${deleteTargetIds.length} recordings? This cannot be undone.`;
    }
    openDialog(dom.deleteDialog);
    setTimeout(() => dom.deleteConfirm.focus(), 50);
  }

  async function handleDeleteConfirm() {
    closeDialog(dom.deleteDialog);
    try {
      for (const id of deleteTargetIds) {
        await deleteClip(id);
      }
      clips = clips.filter(c => !deleteTargetIds.includes(clipId(c)));
      deleteTargetIds.forEach(id => selectedClips.delete(id));
      updateBulkBar();
      renderClipGrid();
      renderFolderSidebar();
      showToast(deleteTargetIds.length === 1 ? 'Recording deleted' : `${deleteTargetIds.length} recordings deleted`);
    } catch (err) {
      showToast('Failed to delete: ' + err.message, 'error');
    }
    deleteTargetIds = [];
  }

  // -- Create Folder Dialog --
  function showCreateFolderDialog() {
    dom.folderNameInput.value = '';
    openDialog(dom.folderDialog);
    setTimeout(() => dom.folderNameInput.focus(), 50);
  }

  async function handleFolderCreate() {
    const name = dom.folderNameInput.value.trim();
    if (!name) return;
    closeDialog(dom.folderDialog);
    try {
      await createFolder(name);
      await loadFolders();
      showToast(`Folder "${name}" created`);
    } catch (err) {
      showToast('Failed to create folder: ' + err.message, 'error');
    }
  }

  // -- Move to Folder Dialog --
  let moveTargetIds = [];

  function showMoveFolderDialog(ids) {
    moveTargetIds = Array.isArray(ids) ? ids : [ids];
    dom.folderPicker.innerHTML = '';

    if (folders.length === 0) {
      const none = document.createElement('p');
      none.className = 'folder-pick-none';
      none.textContent = 'No folders yet. Create one first.';
      dom.folderPicker.appendChild(none);
    } else {
      // Option to remove from current folder
      if (currentFolder) {
        const removeItem = document.createElement('div');
        removeItem.className = 'folder-pick-item';
        removeItem.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          <span>Remove from folder</span>
        `;
        removeItem.addEventListener('click', async () => {
          closeDialog(dom.moveDialog);
          try {
            await removeClipsFromFolder(currentFolder, moveTargetIds);
            await loadClips();
            await loadFolders();
            showToast('Removed from folder');
          } catch (err) {
            showToast('Failed: ' + err.message, 'error');
          }
        });
        dom.folderPicker.appendChild(removeItem);
      }

      folders.forEach(folder => {
        const item = document.createElement('div');
        item.className = 'folder-pick-item';
        item.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
          <span>${escapeHtml(folder.name)}</span>
        `;
        item.addEventListener('click', async () => {
          closeDialog(dom.moveDialog);
          try {
            await assignClipsToFolder(folder.id, moveTargetIds);
            await loadFolders();
            showToast(`Moved to "${folder.name}"`);
            if (currentFolder && currentFolder !== folder.id) {
              await loadClips();
            }
          } catch (err) {
            showToast('Failed to move: ' + err.message, 'error');
          }
        });
        dom.folderPicker.appendChild(item);
      });
    }

    openDialog(dom.moveDialog);
  }

  // -- Settings Dialog --
  function showSettingsDialog() {
    openDialog(dom.settingsDialog);
    checkYoutubeStatus();
  }

  async function checkYoutubeStatus() {
    dom.ytStatusText.textContent = 'Checking...';
    dom.ytStatusIndicator.className = 'status-indicator';
    try {
      const result = await checkClientSecretsStatus();
      if (result && result.has_client_secrets) {
        dom.ytStatusIndicator.classList.add('status-ok');
        dom.ytStatusText.textContent = 'client_secrets.json uploaded';
      } else {
        dom.ytStatusIndicator.classList.add('status-missing');
        dom.ytStatusText.textContent = 'Not configured';
      }
    } catch {
      dom.ytStatusIndicator.classList.add('status-missing');
      dom.ytStatusText.textContent = 'Unable to check status';
    }
  }

  async function handleSecretsUpload(file) {
    try {
      await uploadClientSecrets(file);
      showToast('client_secrets.json uploaded successfully');
      checkYoutubeStatus();
    } catch (err) {
      showToast('Upload failed: ' + err.message, 'error');
    }
  }

  // -- Cast Status (Live Indicator) --
  async function checkCastStatus() {
    try {
      const result = await api('GET', '/api/cast/status');
      if (result && result.live) {
        dom.liveIndicator.classList.remove('hidden');
      } else {
        dom.liveIndicator.classList.add('hidden');
      }
    } catch {
      dom.liveIndicator.classList.add('hidden');
    }
  }

  // -- Video Preview Lightbox --
  function showVideoPreview(clip) {
    const id = clipId(clip);
    dom.lightboxVideo.src = `/stream/${encodeURIComponent(id)}`;
    dom.lightboxTitle.textContent = clip.filename || clip.original_filename;
    dom.lightboxMeta.textContent = `${clip.game || 'Unknown Game'} · ${formatDuration(clip.duration)} · ${formatSize(clip.size)}`;
    openDialog(dom.videoLightbox);
  }

  function closeVideoPreview() {
    dom.lightboxVideo.pause();
    dom.lightboxVideo.removeAttribute('src');
    dom.lightboxVideo.load();
    closeDialog(dom.videoLightbox);
  }

  // ============================================================
  // Context Menu
  // ============================================================

  function showContextMenu(x, y, id) {
    contextClipId = id;
    const menu = dom.contextMenu;
    menu.classList.remove('hidden');

    // Position
    const mw = menu.offsetWidth;
    const mh = menu.offsetHeight;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    let left = x;
    let top = y;
    if (x + mw > vw) left = vw - mw - 8;
    if (y + mh > vh) top = vh - mh - 8;
    if (left < 0) left = 8;
    if (top < 0) top = 8;

    menu.style.left = left + 'px';
    menu.style.top = top + 'px';
  }

  function hideContextMenu() {
    dom.contextMenu.classList.add('hidden');
    contextClipId = null;
  }

  function handleContextAction(action) {
    const id = contextClipId;
    if (!id) return;

    const clip = clips.find(c => clipId(c) === id);
    if (!clip) return;

    hideContextMenu();

    switch (action) {
      case 'preview':
        showVideoPreview(clip);
        break;
      case 'download': {
        const a = document.createElement('a');
        a.href = `/download/${encodeURIComponent(id)}`;
        a.download = '';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        break;
      }
      case 'download-enhanced': {
        showToast('Enhancing to 1080p... this may take a moment', 'warning');
        const ae = document.createElement('a');
        ae.href = `/download-enhanced/${encodeURIComponent(id)}`;
        ae.download = '';
        document.body.appendChild(ae);
        ae.click();
        document.body.removeChild(ae);
        break;
      }
      case 'rename':
        showRenameDialog(id, clip.filename || clip.original_filename);
        break;
      case 'move':
        showMoveFolderDialog(id);
        break;
      case 'delete':
        showDeleteDialog(id, clip.filename || clip.original_filename);
        break;
    }
  }

  // ============================================================
  // Toast Notifications
  // ============================================================

  function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = '';
    switch (type) {
      case 'success':
        iconSvg = '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>';
        break;
      case 'error':
        iconSvg = '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
        break;
      case 'warning':
        iconSvg = '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
        break;
    }

    toast.innerHTML = iconSvg + `<span class="toast-message">${escapeHtml(message)}</span>`;
    dom.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('toast-out');
      toast.addEventListener('animationend', () => toast.remove());
    }, 3000);
  }

  // ============================================================
  // Drag & Drop
  // ============================================================

  let dragClipId = null;

  function handleDragStart(e, id) {
    dragClipId = id;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', id);
    const card = e.target.closest('.clip-card');
    if (card) {
      setTimeout(() => card.classList.add('dragging'), 0);
    }
  }

  function handleDragEnd(e) {
    const card = e.target.closest('.clip-card');
    if (card) card.classList.remove('dragging');
    dragClipId = null;
  }

  async function handleDrop(e, folderId) {
    const droppedId = e.dataTransfer.getData('text/plain') || dragClipId;
    if (!droppedId || !folderId) return;

    // If we have selected clips and the dragged one is among them, move all selected
    let idsToMove;
    if (selectedClips.has(droppedId) && selectedClips.size > 1) {
      idsToMove = [...selectedClips];
    } else {
      idsToMove = [droppedId];
    }

    try {
      await assignClipsToFolder(folderId, idsToMove);
      await loadFolders();
      const folder = folders.find(f => f.id === folderId);
      showToast(`Moved ${idsToMove.length} clip${idsToMove.length > 1 ? 's' : ''} to "${folder ? folder.name : 'folder'}"`);
      if (currentFolder && currentFolder !== folderId) {
        await loadClips();
      }
    } catch (err) {
      showToast('Failed to move: ' + err.message, 'error');
    }
  }

  // ============================================================
  // Bulk Actions
  // ============================================================

  function updateBulkBar() {
    const count = selectedClips.size;
    if (count > 0) {
      dom.bulkBar.classList.remove('hidden');
      dom.bulkCount.textContent = `${count} selected`;
      dom.selectAllCheckbox.checked = count === getFilteredClips().length;
      dom.clipGrid.classList.add('bulk-mode');
    } else {
      dom.bulkBar.classList.add('hidden');
      dom.selectAllCheckbox.checked = false;
      dom.clipGrid.classList.remove('bulk-mode');
    }
  }

  function handleSelectAll(checked) {
    const filtered = getFilteredClips();
    if (checked) {
      filtered.forEach(c => selectedClips.add(clipId(c)));
    } else {
      selectedClips.clear();
    }
    renderClipGrid();
    updateBulkBar();
  }

  function clearSelection() {
    selectedClips.clear();
    updateBulkBar();
    renderClipGrid();
  }

  // ============================================================
  // Search & Sort
  // ============================================================

  function handleSearch(query) {
    searchQuery = query;
    dom.searchClear.classList.toggle('hidden', !query);
    renderClipGrid();
  }

  function handleSort(value) {
    const parts = value.split('-');
    sortBy = parts[0];
    sortOrder = parts[1] || 'desc';
    renderClipGrid();
  }

  // ============================================================
  // Sidebar
  // ============================================================

  function openSidebar() {
    dom.sidebar.classList.add('open');
    dom.sidebarOverlay.classList.remove('hidden');
  }

  function closeSidebar() {
    dom.sidebar.classList.remove('open');
    dom.sidebarOverlay.classList.add('hidden');
  }

  // ============================================================
  // Data Loading
  // ============================================================

  async function loadClips() {
    isLoading = true;
    renderSkeletons(8);
    try {
      const data = await fetchClips(currentFolder);
      clips = Array.isArray(data) ? data : [];
      isLoading = false;
      renderClipGrid();
    } catch (err) {
      isLoading = false;
      clips = [];
      renderEmptyState();
      showToast('Failed to load recordings: ' + err.message, 'error');
    }
  }

  async function loadFolders() {
    try {
      const data = await fetchFolders();
      folders = Array.isArray(data) ? data : [];
      renderFolderSidebar();
    } catch {
      // Folders endpoint may not exist yet; silently continue
      folders = [];
      renderFolderSidebar();
    }
  }

  async function refresh() {
    // Spin the refresh icon
    const icon = dom.refreshBtn.querySelector('svg');
    icon.style.transition = 'transform 600ms ease';
    icon.style.transform = 'rotate(360deg)';
    setTimeout(() => {
      icon.style.transition = '';
      icon.style.transform = '';
    }, 650);

    await Promise.all([loadClips(), loadFolders()]);
    showToast('Refreshed');
  }

  // ============================================================
  // Event Binding
  // ============================================================

  function bindEvents() {
    // Sidebar toggle
    dom.hamburgerBtn.addEventListener('click', openSidebar);
    dom.sidebarClose.addEventListener('click', closeSidebar);
    dom.sidebarOverlay.addEventListener('click', closeSidebar);

    // Search
    dom.searchInput.addEventListener('input', (e) => handleSearch(e.target.value));
    dom.searchClear.addEventListener('click', () => {
      dom.searchInput.value = '';
      handleSearch('');
      dom.searchInput.focus();
    });

    // Sort
    dom.sortSelect.addEventListener('change', (e) => handleSort(e.target.value));

    // Refresh
    dom.refreshBtn.addEventListener('click', refresh);

    // Settings
    dom.settingsBtn.addEventListener('click', showSettingsDialog);
    dom.settingsClose.addEventListener('click', () => closeDialog(dom.settingsDialog));

    // Settings tab switching
    $$('.settings-nav-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        $$('.settings-nav-item').forEach(b => b.classList.remove('active'));
        $$('.settings-tab').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        const target = $(`#tab-${tab}`);
        if (target) target.classList.add('active');
        if (tab === 'youtube') checkYoutubeStatus();
      });
    });

    // Create folder
    dom.newFolderBtn.addEventListener('click', showCreateFolderDialog);

    // Rename dialog
    dom.renameCancel.addEventListener('click', () => closeDialog(dom.renameDialog));
    dom.renameSave.addEventListener('click', handleRenameSave);
    dom.renameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleRenameSave();
    });

    // Delete dialog
    dom.deleteCancel.addEventListener('click', () => closeDialog(dom.deleteDialog));
    dom.deleteConfirm.addEventListener('click', handleDeleteConfirm);

    // Folder create dialog
    dom.folderCancel.addEventListener('click', () => closeDialog(dom.folderDialog));
    dom.folderCreate.addEventListener('click', handleFolderCreate);
    dom.folderNameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleFolderCreate();
    });

    // Move dialog
    dom.moveCancel.addEventListener('click', () => closeDialog(dom.moveDialog));

    // Video lightbox
    dom.lightboxClose.addEventListener('click', closeVideoPreview);

    // Bulk bar
    dom.selectAllCheckbox.addEventListener('change', (e) => handleSelectAll(e.target.checked));
    dom.bulkDeleteBtn.addEventListener('click', () => {
      if (selectedClips.size === 0) return;
      showDeleteDialog([...selectedClips], '');
    });
    dom.bulkMoveBtn.addEventListener('click', () => {
      if (selectedClips.size === 0) return;
      showMoveFolderDialog([...selectedClips]);
    });
    dom.bulkCancelBtn.addEventListener('click', clearSelection);

    // Context menu actions
    $$('.context-item', dom.contextMenu).forEach(item => {
      item.addEventListener('click', () => {
        handleContextAction(item.dataset.action);
      });
    });

    // Close context menu on click outside
    document.addEventListener('click', (e) => {
      if (!dom.contextMenu.contains(e.target)) {
        hideContextMenu();
      }
    });

    // Close context menu on scroll
    document.addEventListener('scroll', hideContextMenu, { passive: true });

    // Upload zone for client secrets
    dom.uploadZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dom.uploadZone.classList.add('drag-active');
    });
    dom.uploadZone.addEventListener('dragleave', () => {
      dom.uploadZone.classList.remove('drag-active');
    });
    dom.uploadZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dom.uploadZone.classList.remove('drag-active');
      const file = e.dataTransfer.files[0];
      if (file) handleSecretsUpload(file);
    });
    dom.secretsFileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) handleSecretsUpload(file);
      e.target.value = '';
    });

    // Global keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // Escape closes dialogs and context menu
      if (e.key === 'Escape') {
        hideContextMenu();
        if (dom.videoLightbox.open) {
          closeVideoPreview();
          return;
        }
        // Close any open dialog
        [dom.renameDialog, dom.deleteDialog, dom.folderDialog, dom.moveDialog, dom.settingsDialog].forEach(d => {
          if (d.open) closeDialog(d);
        });
        // Clear selection
        if (selectedClips.size > 0 && !document.querySelector('dialog[open]')) {
          clearSelection();
        }
      }

      // Ctrl/Cmd+A to select all (when not in input)
      if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
        const tag = document.activeElement.tagName;
        if (tag !== 'INPUT' && tag !== 'TEXTAREA') {
          e.preventDefault();
          handleSelectAll(true);
        }
      }

      // Ctrl/Cmd+F to focus search
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        dom.searchInput.focus();
        dom.searchInput.select();
      }
    });

    // Dialog backdrop click to close
    [dom.renameDialog, dom.deleteDialog, dom.folderDialog, dom.moveDialog, dom.settingsDialog, dom.videoLightbox].forEach(dialog => {
      dialog.addEventListener('click', (e) => {
        if (e.target === dialog) {
          if (dialog === dom.videoLightbox) {
            closeVideoPreview();
          } else {
            closeDialog(dialog);
          }
        }
      });
    });

    // Pull-to-refresh on mobile (simple approach: detect overscroll)
    let touchStartY = 0;
    let isPulling = false;
    document.addEventListener('touchstart', (e) => {
      if (window.scrollY === 0) {
        touchStartY = e.touches[0].clientY;
      }
    }, { passive: true });

    document.addEventListener('touchmove', (e) => {
      if (window.scrollY === 0) {
        const diff = e.touches[0].clientY - touchStartY;
        if (diff > 80 && !isPulling) {
          isPulling = true;
        }
      }
    }, { passive: true });

    document.addEventListener('touchend', () => {
      if (isPulling) {
        isPulling = false;
        refresh();
      }
    }, { passive: true });
  }

  // ============================================================
  // Init
  // ============================================================

  async function init() {
    cacheDom();
    bindEvents();
    renderSkeletons(8);
    await Promise.all([loadClips(), loadFolders()]);
    checkCastStatus();
    setInterval(checkCastStatus, 5000);
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', App.init);
