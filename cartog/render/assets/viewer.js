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

      // Start with folder, file and class containers collapsed for a clean high-level view
      setTimeout(() => {
        const compoundsToCollapse = cy.nodes(':parent[kind = "folder"], :parent[kind = "file"], :parent[kind = "class"]');
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

  function sidebarSection() {
    const box = document.createElement('div');
    box.className = 'sidebar-section';
    return box;
  }

  function sidebarLabel(text) {
    const el = document.createElement('div');
    el.className = 'sidebar-label';
    el.textContent = text;
    return el;
  }

  function sidebarValue(text, asCode) {
    const el = document.createElement('div');
    el.className = 'sidebar-value';
    if (asCode) {
      const code = document.createElement('code');
      code.textContent = text;
      el.appendChild(code);
    } else {
      el.textContent = text;
    }
    return el;
  }

  function sidebarRelations(title, items) {
    const box = sidebarSection();
    box.appendChild(sidebarLabel(title));
    const list = document.createElement('ul');
    list.className = 'relation-list';
    items.forEach((item) => {
      const entry = document.createElement('li');
      entry.className = 'relation-item';
      entry.textContent = item;
      list.appendChild(entry);
    });
    box.appendChild(list);
    return box;
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

    const fragment = document.createDocumentFragment();

    const header = sidebarSection();
    const badge = document.createElement('span');
    badge.className = 'sidebar-badge badge-' + String(kind).replace(/[^\w-]/g, '');
    badge.textContent = kind;
    header.appendChild(badge);
    const title = document.createElement('div');
    title.className = 'sidebar-title';
    title.style.marginTop = '4px';
    title.textContent = name;
    header.appendChild(title);
    fragment.appendChild(header);

    const qualified = sidebarSection();
    qualified.appendChild(sidebarLabel('Qualified Name'));
    qualified.appendChild(sidebarValue(qualifiedName, true));
    fragment.appendChild(qualified);

    if (relPath) {
      const targetPath = (window.CARTOG_VIEW_DATA?.meta?.target_path || '').replace(/\\/g, '/');
      const cleanRel = relPath.replace(/\\/g, '/');
      const fullPath = targetPath ? `${targetPath}/${cleanRel}` : cleanRel;
      const vscodeUrl = `vscode://file/${fullPath}:${line}`;

      const location = sidebarSection();
      location.appendChild(sidebarLabel(`Location (Line ${line})`));
      location.appendChild(sidebarValue(`${cleanRel}:${line}`, true));
      const link = document.createElement('a');
      link.href = vscodeUrl;
      link.className = 'vscode-link';
      link.title = 'Open in VS Code';
      link.style.marginTop = '6px';
      link.textContent = '\u270E Open in VS Code';
      location.appendChild(link);
      fragment.appendChild(location);
    }

    if (d.description) {
      const description = sidebarSection();
      description.appendChild(sidebarLabel('Description'));
      description.appendChild(sidebarValue(d.description));
      fragment.appendChild(description);
    }

    const nodeLabel = (element) => element.data('label') || element.data('id');

    if (incomingCalls.length > 0) {
      fragment.appendChild(sidebarRelations(
        `Callers (${incomingCalls.length})`,
        incomingCalls.map((edge) => nodeLabel(edge.source()))
      ));
    }

    if (outgoingCalls.length > 0) {
      fragment.appendChild(sidebarRelations(
        `Callees (${outgoingCalls.length})`,
        outgoingCalls.map((edge) => nodeLabel(edge.target()))
      ));
    }

    if (outgoingImports.length > 0) {
      fragment.appendChild(sidebarRelations(
        `Imports (${outgoingImports.length})`,
        outgoingImports.map((edge) => nodeLabel(edge.target()))
      ));
    }

    detailsContainer.replaceChildren(fragment);
  }

  function clearSidebar() {
    const detailsContainer = document.getElementById('node-details');
    if (detailsContainer) {
      const empty = document.createElement('div');
      empty.className = 'sidebar-section';
      empty.style.color = 'var(--text-muted)';
      empty.style.fontSize = '0.85rem';
      empty.style.textAlign = 'center';
      empty.style.marginTop = '32px';
      empty.textContent =
        'Select any node or symbol in the diagram to inspect properties, dependencies, and code coordinates.';
      detailsContainer.replaceChildren(empty);
    }
  }

  function applyLayout(layoutName, cy) {
    if (layoutName === 'dag') {
      // Left-to-right flow: BFS from root nodes, assign x by depth.
      // Cytoscape's breadthfirst is top-down only, so we compute positions manually.
      const outEdges = new Map();
      cy.edges().forEach(e => {
        const s = e.source().id();
        if (!outEdges.has(s)) outEdges.set(s, []);
        outEdges.get(s).push(e.target().id());
      });
      const inDegree = new Map();
      cy.nodes().forEach(n => inDegree.set(n.id(), 0));
      cy.edges().forEach(e => {
        const t = e.target().id();
        inDegree.set(t, (inDegree.get(t) || 0) + 1);
      });
      const roots = cy.nodes().filter(n => (inDegree.get(n.id()) || 0) === 0);
      if (roots.length === 0) roots = cy.nodes().filter((n, i) => i === 0);
      const depthMap = new Map();
      const queue = [];
      roots.forEach(r => { queue.push(r.id()); depthMap.set(r.id(), 0); });
      const visited = new Set();
      while (queue.length > 0) {
        const id = queue.shift();
        if (visited.has(id)) continue;
        visited.add(id);
        const depth = depthMap.get(id) || 0;
        (outEdges.get(id) || []).forEach(tid => {
          if (!visited.has(tid) && !depthMap.has(tid)) {
            depthMap.set(tid, depth + 1);
            queue.push(tid);
          }
        });
      }
      // Assign positions by depth, stacking within each level.
      const levels = new Map();
      depthMap.forEach((d, id) => {
        if (!levels.has(d)) levels.set(d, []);
        levels.get(d).push(id);
      });
      const hSpacing = 220;
      const vSpacing = 90;
      cy.batch(() => {
        levels.forEach((ids, depth) => {
          ids.forEach((id, idx) => {
            const node = cy.getElementById(id);
            node.position({ x: depth * hSpacing, y: idx * vSpacing });
          });
        });
      });
      cy.animate({ fit: { padding: 50 }, duration: 400 });
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
    const isFlowMode = (data.meta || {}).is_flow || (data.entry_points || []).length > 0;
    const selectLayout = document.getElementById('select-layout');
    if (selectLayout && isFlowMode) {
      selectLayout.value = 'dag';
    }
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
        btnToggleReferences.textContent = showReferences
          ? '\u25CE References: On'
          : '\u25CE References: Off';
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
        btnToggleHelpers.textContent = showHelpers
          ? '\u2699 Helpers: Shown'
          : '\u2699 Helpers: Hidden';
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

    const entryFilter = document.getElementById('entry-filter');
    const entryPoints = (data.entry_points || []);
    const isFlowMode = (data.meta || {}).is_flow || entryPoints.length > 0;
    if (entryFilter && entryPoints.length > 0) {
      entryFilter.style.display = '';
      // Multi-select: allow selecting multiple entry points to see combined flows.
      entryFilter.setAttribute('multiple', 'multiple');
      entryFilter.setAttribute('size', '1');
      const allOpt = document.createElement('option');
      allOpt.value = '__all__';
      allOpt.textContent = 'All entry points';
      entryFilter.appendChild(allOpt);
      entryPoints.forEach((ep) => {
        const opt = document.createElement('option');
        opt.value = ep.id || ep.name;
        opt.textContent = ep.name;
        opt.title = ep.path || ep.id || '';
        entryFilter.appendChild(opt);
      });
      const visitedById = new Map(entryPoints.map((ep) => [ep.id || ep.name, new Set(ep.visited || [])]));
      function applyEntryFilter() {
        const selected = Array.from(entryFilter.selectedOptions).map(o => o.value);
        cy.batch(() => {
          if (selected.length === 0 || selected.includes('__all__')) {
            cy.nodes().style('display', 'element');
            cy.edges().style('display', 'element');
          } else {
            const visited = new Set();
            selected.forEach(val => {
              const v = visitedById.get(val);
              if (v) v.forEach(id => visited.add(id));
            });
            cy.nodes().each((node) => {
              node.style('display', visited.has(node.id()) ? 'element' : 'none');
            });
            cy.edges().each((edge) => {
              const s = edge.source().id();
              const t = edge.target().id();
              edge.style('display', (visited.has(s) && visited.has(t)) ? 'element' : 'none');
            });
          }
        });
        try { cy.fit(cy.nodes(':visible'), 60); } catch (err) { /* ignore */ }
      }
      entryFilter.addEventListener('change', applyEntryFilter);
      // Auto-trace first entry point on load in flow mode (no search needed).
      const isFlowMode = (data.meta || {}).is_flow;
      if (isFlowMode && entryPoints.length > 0) {
        entryFilter.options[1].selected = true;
        applyEntryFilter();
        setTimeout(() => applyLayout('dag', cy), 100);
      }
    }

    const btnCloseSidebar = document.getElementById('btn-close-sidebar');
    const sidebar = document.getElementById('sidebar');
    if (btnCloseSidebar && sidebar) {
      btnCloseSidebar.addEventListener('click', () => {
        sidebar.classList.add('hidden');
      });
    }
  }
})();

