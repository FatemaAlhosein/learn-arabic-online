/**
 * markdown_editor.js
 * ------------------
 * Turns any <textarea data-markdown-editor="true"> into a split-pane
 * live-preview editor inside the Django admin.
 *
 * Depends on: marked.js (loaded by the widget's Media class)
 */

(function () {
  "use strict";

  // Wait until marked.js is fully loaded (it's async via CDN)
  function waitForMarked(cb) {
    if (typeof marked !== "undefined") {
      cb();
    } else {
      setTimeout(function () { waitForMarked(cb); }, 50);
    }
  }

  function initEditor(textarea) {
    if (textarea.dataset.mdEditorInitialised) return;
    textarea.dataset.mdEditorInitialised = "true";

    // ── Build the wrapper ──────────────────────────────────────────────
    const wrapper = document.createElement("div");
    wrapper.className = "md-editor-wrapper";

    // toolbar
    const toolbar = document.createElement("div");
    toolbar.className = "md-editor-toolbar";
    toolbar.innerHTML = `
      <span class="md-editor-label">✏️ Markdown source</span>
      <span class="md-editor-label" style="margin-left:auto">👁 Preview</span>
      <button type="button" class="md-editor-btn" id="md-fullscreen-btn" title="Toggle fullscreen">⛶</button>
    `;

    // pane container
    const panes = document.createElement("div");
    panes.className = "md-editor-panes";

    // left: textarea pane
    const leftPane = document.createElement("div");
    leftPane.className = "md-editor-pane md-editor-source";

    // right: preview pane
    const rightPane = document.createElement("div");
    rightPane.className = "md-editor-pane md-editor-preview prose";
    rightPane.setAttribute("aria-label", "Rendered preview");

    // move textarea into left pane
    textarea.parentNode.insertBefore(wrapper, textarea);
    leftPane.appendChild(textarea);
    panes.appendChild(leftPane);
    panes.appendChild(rightPane);
    wrapper.appendChild(toolbar);
    wrapper.appendChild(panes);

    // ── Render function ────────────────────────────────────────────────
    function render() {
      const src = textarea.value;
      rightPane.innerHTML = src
        ? marked.parse(src)
        : '<p class="md-editor-placeholder">Preview will appear here…</p>';
    }

    // ── Wire up events ─────────────────────────────────────────────────
    textarea.addEventListener("input", render);
    textarea.addEventListener("keyup", render);   // catches paste via keyboard

    // Fullscreen toggle
    const fsBtn = toolbar.querySelector("#md-fullscreen-btn");
    fsBtn.addEventListener("click", function () {
      wrapper.classList.toggle("md-editor-fullscreen");
      fsBtn.textContent = wrapper.classList.contains("md-editor-fullscreen") ? "✕" : "⛶";
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && wrapper.classList.contains("md-editor-fullscreen")) {
        wrapper.classList.remove("md-editor-fullscreen");
        fsBtn.textContent = "⛶";
      }
    });

    // Initial render
    render();
  }

  function initAll() {
    document.querySelectorAll("textarea[data-markdown-editor='true']")
      .forEach(initEditor);
  }

  waitForMarked(function () {
    // Configure marked: safe mode off (we trust admin users), GFM on
    marked.setOptions({ gfm: true, breaks: true });
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initAll);
    } else {
      initAll();
    }
  });
})();
