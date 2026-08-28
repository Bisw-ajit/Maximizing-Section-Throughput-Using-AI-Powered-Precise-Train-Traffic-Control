import React, { useState, useMemo } from 'react';
import { useNetwork, useDigitalTwin } from '../../hooks/useRailData';
import { useAppStore } from '../../stores/useAppStore';
import { Train, Node, Section } from '../../types/api';
import { AlertTriangle, Radio, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import './NetworkMap.css';

// Built-in fallback network definitions so map renders 100% instantly
const DEFAULT_FALLBACK_NODES: Node[] = [
  { node_id: 'CTK', name: 'Cuttack', node_type: 'STATION', latitude: 20.4625, longitude: 85.8828, platform_count: 4 },
  { node_id: 'BGBR', name: 'Barang', node_type: 'INTERMEDIATE', latitude: 20.3840, longitude: 85.8450, platform_count: 2 },
  { node_id: 'BBS', name: 'Bhubaneswar', node_type: 'STATION', latitude: 20.2961, longitude: 85.8245, platform_count: 6 },
  { node_id: 'RET', name: 'Retang', node_type: 'INTERMEDIATE', latitude: 20.2150, longitude: 85.7420, platform_count: 2 },
  { node_id: 'KUR', name: 'Khurda Road Junction', node_type: 'JUNCTION', latitude: 20.1736, longitude: 85.6177, platform_count: 4, is_junction: true },
  { node_id: 'SIL', name: 'Sakhigopal', node_type: 'INTERMEDIATE', latitude: 19.9520, longitude: 85.7950, platform_count: 2 },
  { node_id: 'PURI', name: 'Puri', node_type: 'STATION', latitude: 19.8135, longitude: 85.8312, platform_count: 8 },
  { node_id: 'BALU', name: 'Balugaon', node_type: 'INTERMEDIATE', latitude: 19.7420, longitude: 85.2050, platform_count: 2 },
  { node_id: 'KLK', name: 'Khallikote', node_type: 'STATION', latitude: 19.6069, longitude: 85.0939, platform_count: 2 },
  { node_id: 'CAP', name: 'Chatrapur', node_type: 'INTERMEDIATE', latitude: 19.3580, longitude: 84.9850, platform_count: 2 },
  { node_id: 'BAM', name: 'Brahmapur', node_type: 'STATION', latitude: 19.3149, longitude: 84.7941, platform_count: 4 },
];

const DEFAULT_FALLBACK_SECTIONS: Section[] = [
  { section_id: 'CTK-BGBR', from_node: 'CTK', to_node: 'BGBR', length_km: 12.0, capacity: 2, allowed_movements: 'BOTH', is_bidirectional: true },
  { section_id: 'BGBR-BBS', from_node: 'BGBR', to_node: 'BBS', length_km: 16.0, capacity: 2, allowed_movements: 'BOTH', is_bidirectional: true },
  { section_id: 'BBS-RET', from_node: 'BBS', to_node: 'RET', length_km: 10.0, capacity: 2, allowed_movements: 'BOTH', is_bidirectional: true },
  { section_id: 'RET-KUR', from_node: 'RET', to_node: 'KUR', length_km: 10.0, capacity: 2, allowed_movements: 'BOTH', is_bidirectional: true },
  { section_id: 'KUR-SIL', from_node: 'KUR', to_node: 'SIL', length_km: 28.0, capacity: 1, allowed_movements: 'BOTH', is_bidirectional: true },
  { section_id: 'SIL-PURI', from_node: 'SIL', to_node: 'PURI', length_km: 17.0, capacity: 1, allowed_movements: 'BOTH', is_bidirectional: true },
  { section_id: 'KUR-BALU', from_node: 'KUR', to_node: 'BALU', length_km: 35.0, capacity: 1, allowed_movements: 'BOTH', is_bidirectional: true },
  { section_id: 'BALU-KLK', from_node: 'BALU', to_node: 'KLK', length_km: 30.0, capacity: 1, allowed_movements: 'BOTH', is_bidirectional: true },
  { section_id: 'KLK-CAP', from_node: 'KLK', to_node: 'CAP', length_km: 20.0, capacity: 1, allowed_movements: 'BOTH', is_bidirectional: true },
  { section_id: 'CAP-BAM', from_node: 'CAP', to_node: 'BAM', length_km: 15.0, capacity: 1, allowed_movements: 'BOTH', is_bidirectional: true },
];

// Schematic node coordinate mappings (Control Room CTC layout)
const SCHEMATIC_POSITIONS: Record<string, { x: number; y: number }> = {
  CTK:  { x: 500, y: 70 },
  BGBR: { x: 500, y: 135 },
  BBS:  { x: 500, y: 200 },
  RET:  { x: 500, y: 265 },
  KUR:  { x: 500, y: 345 }, // Khurda Road Junction
  // Puri Branch (South-East)
  SIL:  { x: 720, y: 460 },
  PURI: { x: 900, y: 570 },
  // Brahmapur Line (South-West)
  BALU: { x: 340, y: 430 },
  KLK:  { x: 240, y: 495 },
  CAP:  { x: 150, y: 555 },
  BAM:  { x: 70,  y: 610 },
};

// Geographical fallback projection coordinates (scaled lat/lng)
const GEO_MIN_LNG = 84.6;
const GEO_MAX_LNG = 86.0;
const GEO_MIN_LAT = 19.2;
const GEO_MAX_LAT = 20.6;

function getGeoPosition(lng: number, lat: number) {
  const x = 70 + ((lng - GEO_MIN_LNG) / (GEO_MAX_LNG - GEO_MIN_LNG)) * 880;
  const y = 610 - ((lat - GEO_MIN_LAT) / (GEO_MAX_LAT - GEO_MIN_LAT)) * 540;
  return { x, y };
}

export const NetworkMap: React.FC = () => {
  const { data: network } = useNetwork();
  const { data: twin } = useDigitalTwin(true);
  const { setSelectedTrainId, selectedTrainId } = useAppStore();

  const [mapMode, setMapMode] = useState<'ctc' | 'schematic' | 'geo'>('ctc');
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [hoveredSectionId, setHoveredSectionId] = useState<string | null>(null);

  const activeNodes = useMemo(() => {
    return network?.nodes && network.nodes.length > 0 ? network.nodes : DEFAULT_FALLBACK_NODES;
  }, [network]);

  const activeSections = useMemo(() => {
    return network?.sections && network.sections.length > 0 ? network.sections : DEFAULT_FALLBACK_SECTIONS;
  }, [network]);

  // Compute node positions map based on selected map mode
  const nodeCoords = useMemo(() => {
    const coords: Record<string, { x: number; y: number }> = {};
    activeNodes.forEach((node) => {
      if (mapMode === 'geo') {
        coords[node.node_id] = getGeoPosition(node.longitude, node.latitude);
      } else {
        coords[node.node_id] = SCHEMATIC_POSITIONS[node.node_id] || { x: 500, y: 300 };
      }
    });
    return coords;
  }, [activeNodes, mapMode]);

  // Identify active conflict sections based on occupancy or held status
  const conflictSections = useMemo(() => {
    if (!twin || !twin.section_occupancy) return new Set<string>();
    const conflicts = new Set<string>();

    // Single-line bottleneck checks & multi-occupancy
    Object.entries(twin.section_occupancy).forEach(([secId, trainIds]) => {
      if (trainIds.length > 1) {
        conflicts.add(secId);
      }
    });

    // Check held/delayed trains
    twin.trains.forEach((train: Train) => {
      if (train.status === 'HELD' && train.current_section) {
        conflicts.add(train.current_section);
      }
    });

    return conflicts;
  }, [twin]);

  // Compute animated real-time train positions
  const trainPositions = useMemo(() => {
    if (!twin?.trains) return [];

    const activeTrains = twin.trains.filter((t) => t.status !== 'COMPLETED');
    const sectionTrainCounts: Record<string, number> = {};

    return activeTrains.map((train) => {
      let x = 500;
      let y = 300;
      let angle = 0;
      let sectionId = train.current_section;

      if (train.current_node && nodeCoords[train.current_node]) {
        x = nodeCoords[train.current_node].x;
        y = nodeCoords[train.current_node].y;
      } else if (train.current_section) {
        const parts = train.current_section.split('-');
        let fromId = parts[0];
        let toId = parts[1];

        // Match section in activeSections
        const sec = activeSections.find(
          (s) =>
            s.section_id === train.current_section ||
            `${s.to_node}-${s.from_node}` === train.current_section
        );

        if (sec && (!fromId || !toId)) {
          fromId = sec.from_node;
          toId = sec.to_node;
        }

        const p1 = nodeCoords[fromId];
        const p2 = nodeCoords[toId];

        if (p1 && p2) {
          const progress = Math.min(1.0, Math.max(0.0, train.journey_progress || 0.5));
          const dx = p2.x - p1.x;
          const dy = p2.y - p1.y;
          angle = (Math.atan2(dy, dx) * 180) / Math.PI;

          x = p1.x + dx * progress;
          y = p1.y + dy * progress;

          // Apply slight perpendicular offset for overlapping trains
          const secKey = [fromId, toId].sort().join('-');
          sectionTrainCounts[secKey] = (sectionTrainCounts[secKey] || 0) + 1;
          const countIndex = sectionTrainCounts[secKey] - 1;

          if (countIndex > 0) {
            const len = Math.sqrt(dx * dx + dy * dy) || 1;
            const perpX = (-dy / len) * 14 * countIndex;
            const perpY = (dx / len) * 14 * countIndex;
            x += perpX;
            y += perpY;
          }
        }
      }

      return {
        train,
        x,
        y,
        angle,
        sectionId,
        isDelayed: train.delay_minutes > 0,
        isHeld: train.status === 'HELD',
      };
    });
  }, [twin, activeSections, nodeCoords]);

  return (
    <div className={`network-map-container mode-${mapMode}`}>
      {/* Control Room Top Header Overlay */}
      <div className="control-room-header">
        <div className="cr-title">
          <Radio size={16} className="cr-live-pulse" />
          <span>RAILWAY CTC DISPATCH BOARD — CENTRAL CONTROL ROOM</span>
          <span className="cr-subtext">Cuttack–Bhubaneswar–Khurda Road–Puri–Brahmapur Network</span>
        </div>

        <div className="cr-controls">
          {/* Mode Switcher */}
          <div className="mode-toggle-group">
            <button
              className={`mode-btn ${mapMode === 'ctc' ? 'active' : ''}`}
              onClick={() => setMapMode('ctc')}
              title="CTC Control Room Dark Mode"
            >
              CTC Dark
            </button>
            <button
              className={`mode-btn ${mapMode === 'schematic' ? 'active' : ''}`}
              onClick={() => setMapMode('schematic')}
              title="Suburban Transit Schematic Diagram"
            >
              Transit Map
            </button>
            <button
              className={`mode-btn ${mapMode === 'geo' ? 'active' : ''}`}
              onClick={() => setMapMode('geo')}
              title="Geographical Lat/Lng View"
            >
              Geographic
            </button>
          </div>

          {/* Zoom controls */}
          <div className="zoom-btn-group">
            <button onClick={() => setZoomLevel((z) => Math.min(z + 0.15, 1.8))} title="Zoom In">
              <ZoomIn size={14} />
            </button>
            <button onClick={() => setZoomLevel(1)} title="Reset View">
              <Maximize2 size={14} />
            </button>
            <button onClick={() => setZoomLevel((z) => Math.max(z - 0.15, 0.75))} title="Zoom Out">
              <ZoomOut size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="svg-map-wrapper">
        <svg
          viewBox="0 0 1050 680"
          className="schematic-svg"
          style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center center' }}
        >
          <defs>
            {/* Track Line Gradient / Shadows */}
            <filter id="glow-danger" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="glow-track" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2.5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Render Railway Sections (Tracks) */}
          <g className="rail-tracks-layer">
            {activeSections.map((sec) => {
              const p1 = nodeCoords[sec.from_node];
              const p2 = nodeCoords[sec.to_node];
              if (!p1 || !p2) return null;

              const isSingle = (sec as any).track_type === 'SINGLE' || sec.capacity === 1;
              const hasConflict = conflictSections.has(sec.section_id) || conflictSections.has(`${sec.to_node}-${sec.from_node}`);
              const isHovered = hoveredSectionId === sec.section_id;

              const midX = (p1.x + p2.x) / 2;
              const midY = (p1.y + p2.y) / 2;

              return (
                <g
                  key={sec.section_id}
                  className={`track-section-group ${hasConflict ? 'conflict-track' : ''} ${isHovered ? 'hovered' : ''}`}
                  onMouseEnter={() => setHoveredSectionId(sec.section_id)}
                  onMouseLeave={() => setHoveredSectionId(null)}
                >
                  {/* Outer aura for conflict or hover */}
                  {hasConflict && (
                    <line
                      x1={p1.x}
                      y1={p1.y}
                      x2={p2.x}
                      y2={p2.y}
                      className="track-aura-conflict"
                      filter="url(#glow-danger)"
                    />
                  )}

                  {/* Main Track Line */}
                  <line
                    x1={p1.x}
                    y1={p1.y}
                    x2={p2.x}
                    y2={p2.y}
                    className={`track-line ${isSingle ? 'single-track' : 'double-track'} ${hasConflict ? 'conflict' : ''}`}
                  />

                  {/* Parallel track line for Double-track sections */}
                  {!isSingle && (
                    <line
                      x1={p1.x + 4}
                      y1={p1.y + 4}
                      x2={p2.x + 4}
                      y2={p2.y + 4}
                      className="track-line-parallel"
                    />
                  )}

                  {/* Section Distance Badge */}
                  <g className="distance-badge-group" transform={`translate(${midX}, ${midY})`}>
                    <rect
                      x="-26"
                      y="-10"
                      width="52"
                      height="20"
                      rx="10"
                      className={`dist-bg ${isSingle ? 'single-badge' : ''}`}
                    />
                    <text x="0" y="3" className="dist-text">
                      {sec.length_km} km
                    </text>
                  </g>
                </g>
              );
            })}
          </g>

          {/* Render Station & Junction Nodes */}
          <g className="station-nodes-layer">
            {activeNodes.map((node) => {
              const pos = nodeCoords[node.node_id];
              if (!pos) return null;

              const isJunction = node.is_junction || node.node_type === 'JUNCTION';
              const platCount = node.platform_count ?? 2;
              const isTerminal = platCount >= 4 && !isJunction;
              const isIntermediate = node.node_type === 'INTERMEDIATE';

              return (
                <g
                  key={node.node_id}
                  className={`station-node-group ${isJunction ? 'junction-node' : ''} ${isTerminal ? 'terminal-node' : ''}`}
                  transform={`translate(${pos.x}, ${pos.y})`}
                >
                  {/* Outer pulse for Junction */}
                  {isJunction && <circle r="22" className="junction-pulse" />}

                  {/* Node Icon/Circle */}
                  {isJunction ? (
                    <g className="junction-symbol">
                      <rect x="-16" y="-16" width="32" height="32" rx="8" className="junction-box" />
                      <circle r="6" className="junction-core" />
                    </g>
                  ) : isTerminal ? (
                    <g className="terminal-symbol">
                      <circle r="14" className="terminal-ring-outer" />
                      <circle r="8" className="terminal-ring-inner" />
                    </g>
                  ) : (
                    <circle r={isIntermediate ? 6 : 9} className={`station-disc ${isIntermediate ? 'intermediate' : ''}`} />
                  )}

                  {/* Station Code & Name Label */}
                  <text
                    x="0"
                    y={isJunction ? 32 : 24}
                    className={`station-label ${isJunction ? 'junction-label' : ''} ${isTerminal ? 'terminal-label' : ''}`}
                  >
                    {node.name} ({node.node_id})
                  </text>

                  {/* Platform count pill for major stations */}
                  {platCount > 2 && (
                    <g transform={`translate(0, ${isJunction ? -26 : -20})`}>
                      <rect x="-24" y="-8" width="48" height="15" rx="7" className="plat-bg" />
                      <text x="0" y="3" className="plat-text">
                        {platCount} PF
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </g>

          {/* Render Real-Time Animated Moving Trains */}
          <g className="train-markers-layer">
            {trainPositions.map(({ train, x, y, angle, isDelayed, isHeld }) => {
              const isSelected = selectedTrainId === train.train_id;

              return (
                <g
                  key={train.train_id}
                  className={`train-marker-group priority-${train.priority} ${isSelected ? 'selected' : ''} ${isHeld ? 'held' : ''}`}
                  transform={`translate(${x}, ${y})`}
                  onClick={() => setSelectedTrainId(train.train_id)}
                >
                  {/* Selection / High-priority aura glow */}
                  <circle r="20" className="train-aura" filter="url(#glow-track)" />

                  {/* Direction Arrow Indicator */}
                  <path
                    d="M 0 -12 L 6 2 L -6 2 Z"
                    className="direction-arrow"
                    transform={`rotate(${angle + (train.direction === 'NORTHBOUND' ? 180 : 0)})`}
                  />

                  {/* Main Train Capsule Badge */}
                  <g className="train-badge-capsule">
                    <rect x="-50" y="-14" width="100" height="28" rx="14" className="train-capsule-bg" />
                    <text x="-40" y="-1" className="train-icon-symbol">
                      {train.priority === 1 ? '🚨' : '🚆'}
                    </text>
                    <text x="-24" y="-1" className="train-no-text">
                      #{train.train_number}
                    </text>
                    <text x="-24" y="9" className="train-name-text">
                      {train.name.split(' ')[0]}
                    </text>
                  </g>

                  {/* Delay / Status Indicator Badge */}
                  {isDelayed && (
                    <g transform="translate(36, -14)">
                      <rect x="-10" y="-6" width="34" height="14" rx="7" className="delay-badge-bg" />
                      <text x="7" y="4" className="delay-badge-text">
                        +{train.delay_minutes.toFixed(0)}m
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {/* Control Room Live Legend & Status Bar */}
      <div className="map-overlay-legend">
        <div className="legend-item">
          <span className="legend-symbol junction"></span> Junction (Khurda Road)
        </div>
        <div className="legend-item">
          <span className="legend-symbol terminal"></span> Major Station/Terminal
        </div>
        <div className="legend-item">
          <span className="legend-symbol double-line"></span> Double Track
        </div>
        <div className="legend-item">
          <span className="legend-symbol single-line"></span> Single Track (Passing Loop)
        </div>
        <div className="legend-item">
          <span className="legend-symbol train-p1"></span> Priority 1 (Rajdhani)
        </div>
        <div className="legend-item">
          <span className="legend-symbol train-p2"></span> Priority 2/3 Express
        </div>
        <div className="legend-item conflict-legend">
          <AlertTriangle size={13} className="text-red-500" /> Active Conflict Warning
        </div>
      </div>
    </div>
  );
};
