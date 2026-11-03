/**
 * Cartog Interactive Cytoscape Viewer Runtime Controller
 * 100% offline, self-contained client controller.
 */

(function () {
  'use strict';

  // Wait for DOM to be ready
  window.addEventListener('DOMContentLoaded', () => {
    initViewer();
  });

  function initViewer() {
    const data = window.CARTOG_VIEW_DATA || { elements: [], meta: {} };

    // Register Cytoscape extensions if loaded
    if (typeof cytoscapeExpandCollapse !== 'undefined') {
      try {
        cytoscape.use(cytoscapeExpandCollapse);
      } catch (e) {
        // already registered or automatic
      }
    }

    if (typeof fcose !== 'undefined') {
      try {
        cytoscape.use(fcose);
      } catch (e) {
        // already registered or automatic
      }
    }

    const container = document.getElementById('cy-container');
    if (!container) return;

    // Define Cytoscape style rules
    const stylesheet = [
      // Base node styling
      {
        selector: 'node',
        style: {
          'label': 'data(label)',
          'color': '#e6edf3',
          'font-family': '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
          'font-size': '11px',
          'text-valign': 'center',
          'text-halign': 'center',
          'background-color': '#21262d',
          'border-width': 1.5,
          'border-color': '#30363d',
          'shape': 'round-rectangle',
          'padding': '8px',
          'text-max-width': '120px',
          'text-wrap': 'ellipsis',
          'transition-property': 'background-color, border-color, width, height',
          'transition-duration': '0.2s'
        }
      },
      // Compound parent nodes
      {
        selector: ':parent',
        style: {
          'text-valign': 'top',
          'text-halign': 'center',
          'background-color': '#161b22',
          'background-opacity': 0.65,
          'border-width': 1.5,
          'border-color': '#30363d',
          'border-style': 'solid',
          'padding': '35px',
          'font-weight': 600,
          'font-size': '12px'
        }
      },
      {
        selector: ':parent[kind = "folder"], :parent[kind = "subsystem"]',
        style: {
          'padding': '50px'
        }
      },
      // Kinds - specific node styling
      {
        selector: 'node[kind = "subsystem"]',
        style: {
          'border-color': '#8957e5',
          'color': '#d2a8ff'
        }
      },
      {
        selector: 'node[kind = "folder"]',
        style: {
          'border-color': '#3fb950',
          'border-style': 'dashed',
          'color': '#7ee787'
        }
      },
      {
        selector: 'node[kind = "file"]',
        style: {
          'background-color': '#162235',
          'border-color': '#58a6ff',
          'color': '#79c0ff'
        }
      },
      {
        selector: 'node[kind = "class"]',
        style: {
          'background-color': '#2e1c0c',
          'border-color': '#f0883e',
          'color': '#ffa657'
        }
      },
      {
        selector: 'node[kind = "function"], node[kind = "method"]',
        style: {
          'background-color': '#2b2207',
          'border-color': '#d29922',
          'color': '#e3b341',
          'font-size': '10px'
        }
      },
      {
        selector: 'node[kind = "route"], node[kind = "command"]',
        style: {
          'background-color': '#3b1227',
          'border-color': '#f778ba',
          'color': '#ff9bce',
          'shape': 'round-diamond'
        }
      },
      {
        selector: 'node[is_helper = 1]',
        style: {
          'background-color': '#1c2128',
          'border-color': '#6e7681',
          'color': '#8b949e',
          'border-style': 'dotted'
        }
      },
      // Collapsed compound styling
      {
        selector: '.cy-expand-collapse-collapsed-node',
        style: {
          'shape': 'round-rectangle',
          'background-color': '#1c2128',
          'border-width': 2,
          'border-style': 'solid',
          'border-color': '#58a6ff',
          'text-valign': 'center',
          'text-halign': 'center',
          'font-weight': 600,
          'padding': '12px'
        }
      },
      // Hover / Selection states
      {
        selector: 'node:selected',
        style: {
          'border-color': '#ffffff',
          'border-width': 3,
          'shadow-blur': 12,
          'shadow-color': '#58a6ff',
          'shadow-opacity': 0.6
        }
      },
      // Edges base: Orthogonal Manhattan routing by default
      {
        selector: 'edge',
        style: {
          'curve-style': 'taxi',
          'taxi-direction': 'auto',
          'taxi-turn': 20,
          'taxi-radius': 4,
          'target-arrow-shape': 'triangle',
          'arrow-scale': 0.85,
          'line-color': '#3b4354',
          'target-arrow-color': '#3b4354',
          'width': 1.5,
          'opacity': 0.8,
          'label': 'data(label)',
          'font-size': '9px',
          'color': '#8b949e',
          'text-rotation': 'autorotate',
          'text-background-opacity': 0.85,
          'text-background-color': '#161b22',
          'text-background-padding': '2px',
          'text-background-shape': 'round-rectangle',
          'text-border-color': '#30363d',
          'text-border-width': 1,
          'text-border-opacity': 0.7
        }
      },
      // Edge kinds
      {
        selector: 'edge[kind = "calls"]',
        style: {
          'line-color': '#58a6ff',
          'target-arrow-color': '#58a6ff',
          'width': 1.8,
          'opacity': 0.85
        }
      },
      {
        selector: 'edge[kind = "imports"]',
        style: {
          'line-color': '#bc8cff',
          'target-arrow-color': '#bc8cff',
          'line-style': 'dotted',
          'width': 1.5
        }
      },
      {
        selector: 'edge[kind = "references"]',
        style: {
          'display': 'none',
          'line-color': '#39c5bb',
          'target-arrow-color': '#39c5bb',
          'line-style': 'dashed',
          'width': 1.2,
          'opacity': 0.5
        }
      },
      {
        selector: 'edge[kind = "overrides"]',
        style: {
          'line-color': '#f0883e',
          'target-arrow-color': '#f0883e',
          'line-style': 'dashed',
          'target-arrow-shape': 'triangle'
        }
      },
      {
        selector: 'edge[kind = "serves"]',
        style: {
          'line-color': '#f778ba',
          'target-arrow-color': '#f778ba',
          'target-arrow-shape': 'circle'
        }
      },
      {
        selector: 'edge:selected',
        style: {
          'line-color': '#ffffff',
          'target-arrow-color': '#ffffff',
          'width': 3,
          'opacity': 1.0
        }
      }
    ];

    // Blueprint Layout configuration: generous spacing, decoupled repulsion, gentle gravity
    const fcoseLayout = {
      name: 'fcose',
      quality: 'default',
      randomize: true,
      animate: false,
      nodeDimensionsIncludeLabels: true,
      uniformNodeDimensions: false,
      packComponents: true,
      nodeRepulsion: 85000,
      idealEdgeLength: 240,
      edgeElasticity: 0.25,
      nestingFactor: 1.4,
      gravity: 0.05,
      gravityRange: 1.5,
      numIter: 2500,
      tile: true,
      tilingPaddingVertical: 55,
      tilingPaddingHorizontal: 55
    };

    // Initialize Cytoscape
    const cy = cytoscape({
      container: container,
      elements: data.elements,
      style: stylesheet,
      layout: fcoseLayout,
      wheelSensitivity: 0.2,
      minZoom: 0.1,
      maxZoom: 3.5
    });

    window.cy = cy;

    // Initialize expand-collapse extension if available
    let api = null;
    if (cy.expandCollapse) {
      api = cy.expandCollapse({
        layoutBy: {
          name: 'fcose',
          randomize: false,
          animate: true,
          animationDuration: 450,
          fit: false,
          nodeDimensionsIncludeLabels: true,
          uniformNodeDimensions: false,
          packComponents: true,
          nodeRepulsion: 85000,
          idealEdgeLength: 240,
          edgeElasticity: 0.25,
          nestingFactor: 1.4,
          gravity: 0.05,
          gravityRange: 1.5,
          tile: true,
          tilingPaddingVertical: 55,
          tilingPaddingHorizontal: 55
        },
        fisheye: false,
        animate: true,
        animationDuration: 300,
        undoable: false,
        cueEnabled: true
      });
      window.cyExpandCollapseApi = api;

      // Start with file and class containers collapsed for a clean high-level view
      setTimeout(() => {
        const compoundsToCollapse = cy.nodes(':parent[kind = "file"], :parent[kind = "class"]');
        if (compoundsToCollapse.length > 0) {
          api.collapse(compoundsToCollapse);
        }
      }, 50);
    }

    // Node click handler -> Populate sidebar
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      displayNodeDetails(node, cy);
    });

    // Background click -> Clear selection
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        clearSidebar();
      }
    });

    // Setup Toolbar Button Events
    setupToolbar(cy, api);
  }

  function displayNodeDetails(node, cy) {
    const sidebar = document.getElementById('sidebar');
    const detailsContainer = document.getElementById('node-details');
    if (!sidebar || !detailsContainer) return;

    sidebar.classList.remove('hidden');

    const d = node.data();
    const kind = d.kind || 'node';
    const name = d.label || d.name || d.id;
    const qualifiedName = d.qualified_name || name;
    const relPath = d.path || '';
    const line = d.line || 1;

    // Calculate callers (incoming calls) & callees (outgoing calls)
    const incomingCalls = node.incomers('edge[kind = "calls"]');
    const outgoingCalls = node.outgoers('edge[kind = "calls"]');
    const incomingImports = node.incomers('edge[kind = "imports"]');
    const outgoingImports = node.outgoers('edge[kind = "imports"]');

    let html = `
      <div class="sidebar-section">
        <span class="sidebar-badge badge-${kind}">${kind}</span>
        <div class="sidebar-title" style="margin-top: 4px;">${escapeHtml(name)}</div>
      </div>

      <div class="sidebar-section">
        <div class="sidebar-label">Qualified Name</div>
        <div class="sidebar-value"><code>${escapeHtml(qualifiedName)}</code></div>
      </div>
    `;

    if (relPath) {
      const targetPath = (window.CARTOG_VIEW_DATA?.meta?.target_path || '').replace(/\\/g, '/');
      const cleanRel = relPath.replace(/\\/g, '/');
      const fullPath = targetPath ? `${targetPath}/${cleanRel}` : cleanRel;
      const vscodeUrl = `vscode://file/${fullPath}:${line}`;

      html += `
        <div class="sidebar-section">
          <div class="sidebar-label">Location (Line ${line})</div>
          <div class="sidebar-value"><code>${escapeHtml(cleanRel)}:${line}</code></div>
          <a href="${vscodeUrl}" class="vscode-link" title="Open in VS Code" style="margin-top: 6px;">
            <span>&#9998;</span> Open in VS Code
          </a>
        </div>
      `;
    }

    if (d.description) {
      html += `
        <div class="sidebar-section">
          <div class="sidebar-label">Description</div>
          <div class="sidebar-value">${escapeHtml(d.description)}</div>
        </div>
      `;
    }

    // Callers list
    if (incomingCalls.length > 0) {
      html += `
        <div class="sidebar-section">
          <div class="sidebar-label">Callers (${incomingCalls.length})</div>
          <ul class="relation-list">
      `;
      incomingCalls.forEach((edge) => {
        const src = edge.source();
        html += `<li class="relation-item">${escapeHtml(src.data('label') || src.data('id'))}</li>`;
      });
      html += `</ul></div>`;
    }

    // Callees list
    if (outgoingCalls.length > 0) {
      html += `
        <div class="sidebar-section">
          <div class="sidebar-label">Callees (${outgoingCalls.length})</div>
          <ul class="relation-list">
      `;
      outgoingCalls.forEach((edge) => {
        const tgt = edge.target();
        html += `<li class="relation-item">${escapeHtml(tgt.data('label') || tgt.data('id'))}</li>`;
      });
      html += `</ul></div>`;
    }

    // Imports list
    if (outgoingImports.length > 0) {
      html += `
        <div class="sidebar-section">
          <div class="sidebar-label">Imports (${outgoingImports.length})</div>
          <ul class="relation-list">
      `;
      outgoingImports.forEach((edge) => {
        const tgt = edge.target();
        html += `<li class="relation-item">${escapeHtml(tgt.data('label') || tgt.data('id'))}</li>`;
      });
      html += `</ul></div>`;
    }

    detailsContainer.innerHTML = html;
  }

  function clearSidebar() {
    const detailsContainer = document.getElementById('node-details');
    if (detailsContainer) {
      detailsContainer.innerHTML = `
        <div class="sidebar-section" style="color: var(--text-muted); font-size: 0.85rem; text-align: center; margin-top: 32px;">
          Select any node or symbol in the diagram to inspect properties, dependencies, and code coordinates.
        </div>
      `;
    }
  }

  function applyLayout(layoutName, cy) {
    if (layoutName === 'dag') {
      cy.layout({
        name: 'breadthfirst',
        directed: true,
        spacingFactor: 2.0,
        animate: true,
        animationDuration: 400,
        fit: true,
        padding: 50
      }).run();
    } else if (layoutName === 'grid') {
      cy.layout({
        name: 'grid',
        fit: true,
        padding: 50,
        animate: true,
        animationDuration: 400
      }).run();
    } else {
      cy.layout({
        name: 'fcose',
        quality: 'default',
        randomize: false,
        animate: true,
        animationDuration: 500,
        fit: true,
        padding: 50,
        nodeDimensionsIncludeLabels: true,
        uniformNodeDimensions: false,
        packComponents: true,
        nodeRepulsion: 85000,
        idealEdgeLength: 240,
        edgeElasticity: 0.25,
        nestingFactor: 1.4,
        gravity: 0.05,
        gravityRange: 1.5,
        tile: true,
        tilingPaddingVertical: 55,
        tilingPaddingHorizontal: 55
      }).run();
    }
  }

  function applyRouting(routingName, cy) {
    cy.batch(() => {
      if (routingName === 'straight') {
        cy.edges().style({
          'curve-style': 'straight'
        });
      } else if (routingName === 'bezier') {
        cy.edges().style({
          'curve-style': 'bezier'
        });
      } else {
        cy.edges().style({
          'curve-style': 'taxi',
          'taxi-direction': 'auto',
          'taxi-turn': 20,
          'taxi-radius': 4
        });
      }
    });
  }

  function setupToolbar(cy, api) {
    const selectLayout = document.getElementById('select-layout');
    if (selectLayout) {
      selectLayout.addEventListener('change', (e) => {
        applyLayout(e.target.value, cy);
      });
    }

    const selectRouting = document.getElementById('select-routing');
    if (selectRouting) {
      selectRouting.addEventListener('change', (e) => {
        applyRouting(e.target.value, cy);
      });
    }

    const btnToggleReferences = document.getElementById('btn-toggle-references');
    if (btnToggleReferences) {
      let showReferences = false;
      btnToggleReferences.addEventListener('click', () => {
        showReferences = !showReferences;
        btnToggleReferences.innerHTML = showReferences
          ? '&#9678; References: On'
          : '&#9678; References: Off';
        btnToggleReferences.classList.toggle('active', showReferences);
        cy.batch(() => {
          cy.edges('[kind = "references"]').forEach(edge => {
            edge.style('display', showReferences ? 'element' : 'none');
          });
        });
      });
    }

    const btnToggleHelpers = document.getElementById('btn-toggle-helpers');
    if (btnToggleHelpers) {
      let showHelpers = true;
      btnToggleHelpers.addEventListener('click', () => {
        showHelpers = !showHelpers;
        btnToggleHelpers.innerHTML = showHelpers
          ? '&#9881; Helpers: Shown'
          : '&#9881; Helpers: Hidden';
        btnToggleHelpers.classList.toggle('active', !showHelpers);
        cy.batch(() => {
          cy.nodes('[is_helper = 1]').forEach(node => {
            node.style('display', showHelpers ? 'element' : 'none');
          });
        });
      });
    }

    const btnFit = document.getElementById('btn-fit');
    if (btnFit) {
      btnFit.addEventListener('click', () => {
        cy.animate({ fit: { padding: 40 }, duration: 400 });
      });
    }

    const btnExpandAll = document.getElementById('btn-expand-all');
    if (btnExpandAll && api) {
      btnExpandAll.addEventListener('click', () => {
        api.expandAll();
        setTimeout(() => {
          const layoutVal = document.getElementById('select-layout')?.value || 'fcose';
          applyLayout(layoutVal, cy);
        }, 100);
      });
    }

    const btnCollapseAll = document.getElementById('btn-collapse-all');
    if (btnCollapseAll && api) {
      btnCollapseAll.addEventListener('click', () => {
        api.collapseAll();
      });
    }

    const btnResetLayout = document.getElementById('btn-reset-layout');
    if (btnResetLayout) {
      btnResetLayout.addEventListener('click', () => {
        const layoutVal = document.getElementById('select-layout')?.value || 'fcose';
        applyLayout(layoutVal, cy);
      });
    }

    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        if (!query) {
          cy.nodes().style('opacity', 1.0);
          cy.edges().style('opacity', 0.75);
          return;
        }

        cy.batch(() => {
          cy.nodes().each((node) => {
            const label = (node.data('label') || '').toLowerCase();
            const qname = (node.data('qualified_name') || '').toLowerCase();
            const path = (node.data('path') || '').toLowerCase();
            const matches = label.includes(query) || qname.includes(query) || path.includes(query);

            if (matches) {
              node.style('opacity', 1.0);
              node.style('border-width', 3);
            } else {
              node.style('opacity', 0.2);
              node.style('border-width', 1.5);
            }
          });
          cy.edges().style('opacity', 0.15);
        });
      });
    }

    const btnCloseSidebar = document.getElementById('btn-close-sidebar');
    const sidebar = document.getElementById('sidebar');
    if (btnCloseSidebar && sidebar) {
      btnCloseSidebar.addEventListener('click', () => {
        sidebar.classList.add('hidden');
      });
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
})();

