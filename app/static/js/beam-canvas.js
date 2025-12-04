/**
 * Interactive SVG Beam Canvas - NZ Style Elevation
 * 
 * Provides visual, interactive beam design interface
 * User can click elements to edit values, drag point loads, etc.
 * 
 * VERSION: With dynamic scaling and centering
 * - Implements Option 1A: Smart centering with dynamic scale
 * - Implements Option 2A: Minimum width requirement with horizontal scroll
 */

class BeamCanvas {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.svg = null;
        
        // Separate X and Y scaling
        this.scaleX = 0.15; // Dynamic - pixels per mm (horizontal)
        this.scaleY = 0.15; // Constant - pixels per mm (vertical) - keeps beam depth consistent
        this.padding = { top: 100, right: 20, bottom: 80, left: 20 };
        
        // Scale constraints for X-axis only
        this.MAX_SCALE_X = 0.18; // Max 180px per meter (0.18px per mm) - for small spans
        this.MIN_SCALE_X = 0.05; // Min 50px per meter (0.05px per mm) - for large spans
        
        // Minimum container width (adds horizontal scroll if needed)
        this.MIN_CONTAINER_WIDTH = 800;
        
        // Visual element dimensions (constants)
        this.VISUAL = {
            beamDepth: 200,      // mm
            flooringDepth: 25,   // mm
            plateWidth: 90,      // mm (same for wall and point load)
            plateHeight: 45,     // mm (same for wall and point load)
        };
        
        // Dragging state
        this.draggedLoad = null;
        this.isDragging = false;
        
        // Beam state - single source of truth
        this.state = {
            name: options.name || "Beam-1",
            member_type: options.member_type || null,
            spacing: options.spacing || 0.4, // meters
            
            supports: options.supports || [
                { position: 90, type: "pinned" },      // mm - left inside face
                { position: 6090, type: "pinned" }     // mm - right inside face (6000mm clear span)
            ],
            
            udl: options.udl || {
                dead_load: 0.5,  // kPa
                live_load: 1.5,  // kPa
                sdl: 0.2,        // kPa - Superimposed Dead Load
                total: 0         // kN/m - Calculated
            },
            
            point_loads: options.point_loads || [],
            // Each point load: { id: unique_id, magnitude: kN, position: mm from left edge of beam }
            
            results: options.results || null
        };
        
        // Assign IDs to any point loads that don't have them
        this.state.point_loads.forEach((pl, index) => {
            if (!pl.id) {
                pl.id = `pl_${Date.now()}_${index}`;
            }
        });
        
        this.calculateUDL();
        this.initialize();
    }
    
    initialize() {
        // Apply minimum width to container for horizontal scroll
        this.container.style.minWidth = `${this.MIN_CONTAINER_WIDTH}px`;
        this.container.style.overflowX = 'auto';
        
        // Create SVG element
        let width = this.container.offsetWidth;
        
        if (width === 0) {
            width = this.MIN_CONTAINER_WIDTH;
            console.log('Container not visible yet, using minimum width:', width);
        }
        
        const height = 500;
        
        console.log('Container width:', width, 'SVG height:', height);
        
        this.svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        this.svg.setAttribute("width", "100%");
        this.svg.setAttribute("height", height);
        this.svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        this.svg.setAttribute("preserveAspectRatio", "xMinYMid meet");  // Changed to xMin to prevent text squashing
        this.svg.style.border = "1px solid #e5e7eb";
        this.svg.style.borderRadius = "8px";
        this.svg.style.backgroundColor = "white";
        this.svg.style.display = "block";
        this.svg.style.minWidth = `${this.MIN_CONTAINER_WIDTH}px`;
        
        // Store SVG width for dynamic calculations
        this.svgWidth = width;
        
        this.container.innerHTML = '';
        this.container.appendChild(this.svg);
        
        this.draw();
    }
    
    // ===================================================================
    // DYNAMIC SCALING & CENTERING - OPTION 1A IMPLEMENTATION
    // ===================================================================
    
    calculateDynamicScale() {
        /**
         * Calculate optimal X-axis scale to:
         * 1. Center the beam in available width
         * 2. Scale X appropriately for span length
         * 3. Prevent cutoff on long spans
         * 
         * Y-axis scale remains constant to keep visual elements consistent
         */
        
        const beamLengthMM = this.getBeamLength();
        const containerWidth = this.svgWidth;
        
        // Reserve space for padding on left and right
        const horizontalMargin = 40; // Total left + right margin
        const availableWidth = containerWidth - horizontalMargin;
        
        // Calculate X scale needed to fit beam in available width
        const scaleToFit = availableWidth / beamLengthMM;
        
        // Constrain X scale between min and max
        this.scaleX = Math.max(this.MIN_SCALE_X, Math.min(this.MAX_SCALE_X, scaleToFit));
        
        // Calculate actual beam width at this scale
        const beamWidthPx = beamLengthMM * this.scaleX;
        
        // Calculate left padding to center the beam
        this.padding.left = (containerWidth - beamWidthPx) / 2;
        
        // Ensure minimum left padding
        this.padding.left = Math.max(20, this.padding.left);
        
        // Right padding mirrors left (though not strictly enforced)
        this.padding.right = this.padding.left;
        
        console.log('Dynamic scaling:', {
            beamLengthMM: beamLengthMM,
            containerWidth: containerWidth,
            scaleX: this.scaleX,
            scaleXPerMeter: (this.scaleX * 1000).toFixed(0) + 'px/m',
            scaleY: this.scaleY,
            scaleYPerMeter: (this.scaleY * 1000).toFixed(0) + 'px/m',
            beamWidthPx: beamWidthPx.toFixed(0),
            leftPadding: this.padding.left.toFixed(0)
        });
    }
    
    // ===================================================================
    // STATE & CALCULATIONS
    // ===================================================================
    
    calculateUDL() {
        const total_kPa = this.state.udl.dead_load + this.state.udl.live_load + this.state.udl.sdl;
        this.state.udl.total = total_kPa * this.state.spacing; // kN/m
    }
    
    getSpan() {
        // Clear span in mm between support inside faces
        if (this.state.supports.length < 2) return 6000;
        const sorted = [...this.state.supports].sort((a, b) => a.position - b.position);
        return sorted[sorted.length - 1].position - sorted[0].position;
    }
    
    getLeftInsideFace() {
        // Left support inside face position (datum for dimensions)
        const sorted = [...this.state.supports].sort((a, b) => a.position - b.position);
        return sorted[0].position;
    }
    
    getRightInsideFace() {
        // Right support inside face position
        const sorted = [...this.state.supports].sort((a, b) => a.position - b.position);
        return sorted[sorted.length - 1].position;
    }
    
    getBeamStart() {
        // Beam starts 45mm before left inside face (at center of left wall plate)
        return this.getLeftInsideFace() - 45;
    }
    
    getBeamEnd() {
        // Beam ends 45mm after right inside face (at center of right wall plate)
        return this.getRightInsideFace() + 45;
    }
    
    getBeamLength() {
        // Total beam length
        return this.getBeamEnd() - this.getBeamStart();
    }
    
    // Convert mm to SVG coordinates
    toSVGX(mm) {
        return this.padding.left + (mm * this.scaleX);
    }
    
    toSVGY(y) {
        return y;
    }
    
    // Convert SVG coordinates back to mm
    fromSVGX(svgX) {
        return (svgX - this.padding.left) / this.scaleX;
    }
    
    // Main draw function
    draw() {
        console.log('Drawing NZ-style beam elevation...', this.state);
        
        // Update container width in case it changed
        this.svgWidth = this.container.offsetWidth || 800;
        
        // CRITICAL: Calculate dynamic scale and padding FIRST
        this.calculateDynamicScale();
        
        // Clear SVG
        while (this.svg.firstChild) {
            this.svg.removeChild(this.svg.firstChild);
        }
        
        const span = this.getSpan();
        const leftInsideFace = this.getLeftInsideFace();
        const beamY = 250; // Base Y position for beam centerline
        
        console.log('Span:', span, 'mm, Left inside face at:', leftInsideFace, 'mm');
        
        // Draw in order (back to front)
        this.drawSupports(beamY);
        this.drawBeam(beamY);
        this.drawPointLoads(beamY);
        this.drawSpanDimension(beamY);
        this.drawLoadInfo(beamY);
        this.drawToolbar();
        
        // Sync hidden form fields
        this.syncFormFields();
        
        console.log('SVG elements:', this.svg.childNodes.length);
    }
    
    
    // ===================================================================
    // REUSABLE DRAWING METHODS
    // ===================================================================
    
    drawPlate(centerX, centerY, isCrossHatched = true, loadId = null) {
        // Draw a 90x45mm plate centered at the given position
        const plateW = this.VISUAL.plateWidth * this.scaleX;
        const plateH = this.VISUAL.plateHeight * this.scaleY;
        
        const x = this.toSVGX(centerX) - plateW / 2;
        const y = centerY - plateH / 2;
        
        // Rectangle
        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("x", x);
        rect.setAttribute("y", y);
        rect.setAttribute("width", plateW);
        rect.setAttribute("height", plateH);
        rect.setAttribute("fill", "white");
        rect.setAttribute("stroke", "black");
        rect.setAttribute("stroke-width", "2");
        
        // Store loadId as data attribute for reliable identification
        if (loadId) {
            rect.setAttribute("data-load-id", loadId);
        }
        
        this.svg.appendChild(rect);
        
        // Cross-hatch if requested
        if (isCrossHatched) {
            const x1 = x;
            const x2 = x + plateW;
            const y1 = y;
            const y2 = y + plateH;
            
            // Diagonal 1: top-left to bottom-right
            const diag1 = document.createElementNS("http://www.w3.org/2000/svg", "line");
            diag1.setAttribute("x1", x1);
            diag1.setAttribute("y1", y1);
            diag1.setAttribute("x2", x2);
            diag1.setAttribute("y2", y2);
            diag1.setAttribute("stroke", "black");
            diag1.setAttribute("stroke-width", "1");
            diag1.style.pointerEvents = "none";
            this.svg.appendChild(diag1);
            
            // Diagonal 2: top-right to bottom-left
            const diag2 = document.createElementNS("http://www.w3.org/2000/svg", "line");
            diag2.setAttribute("x1", x2);
            diag2.setAttribute("y1", y1);
            diag2.setAttribute("x2", x1);
            diag2.setAttribute("y2", y2);
            diag2.setAttribute("stroke", "black");
            diag2.setAttribute("stroke-width", "1");
            diag2.style.pointerEvents = "none";
            this.svg.appendChild(diag2);
        }
        
        return rect; // Return the rectangle element in case caller needs it
    }
    
    drawBeam(beamY) {
        const beamStart = this.getBeamStart();
        const beamEnd = this.getBeamEnd();
        const beamDepth = this.VISUAL.beamDepth;
        const flooringDepth = this.VISUAL.flooringDepth;
        
        const x1 = this.toSVGX(beamStart);
        const x2 = this.toSVGX(beamEnd);
        
        // Draw beam rectangle
        const beam = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        beam.setAttribute("x", x1);
        beam.setAttribute("y", beamY - (beamDepth * this.scaleY) / 2);
        beam.setAttribute("width", x2 - x1);
        beam.setAttribute("height", beamDepth * this.scaleY);
        beam.setAttribute("fill", "white");
        beam.setAttribute("stroke", "black");
        beam.setAttribute("stroke-width", "2");
        this.svg.appendChild(beam);
        
        // Draw flooring layer on top
        const flooring = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        flooring.setAttribute("x", x1);
        flooring.setAttribute("y", beamY - (beamDepth * this.scaleY) / 2 - (flooringDepth * this.scaleY));
        flooring.setAttribute("width", x2 - x1);
        flooring.setAttribute("height", flooringDepth * this.scaleY);
        flooring.setAttribute("fill", "#e5e7eb");
        flooring.setAttribute("stroke", "black");
        flooring.setAttribute("stroke-width", "1");
        this.svg.appendChild(flooring);
    }
    
    drawSupports(beamY) {
        // Draw wall plates at support positions
        this.state.supports.forEach(support => {
            const supportX = support.position; // mm - this is the inside face position
            
            // Draw wall plate (90x45mm, cross-hatched) centered on beam end
            // The beam end is 45mm before the inside face (for left) or 45mm after (for right)
            // So the wall plate should be centered at the beam end position
            const leftInsideFace = this.getLeftInsideFace();
            const rightInsideFace = this.getRightInsideFace();
            
            let wallPlateX;
            if (support.position === leftInsideFace) {
                // Left support - wall plate centered on beam start (45mm before inside face)
                wallPlateX = support.position - 45;
            } else if (support.position === rightInsideFace) {
                // Right support - wall plate centered on beam end (45mm after inside face)
                wallPlateX = support.position + 45;
            } else {
                // Interior support (not currently used, but handle it)
                wallPlateX = support.position;
            }
            
            // Wall plate is positioned below the beam
            // beamY is the beam centerline, beam extends down beamDepth/2
            // Wall plate should be touching the bottom of the beam
            const beamBottom = beamY + (this.VISUAL.beamDepth * this.scaleY) / 2;
            const wallPlateY = beamBottom + (this.VISUAL.plateHeight * this.scaleY) / 2;
            
            this.drawPlate(wallPlateX, wallPlateY, true);
        });
    }
    
    drawPointLoads(beamY) {
        // Sort point loads by position (left to right) for consistent naming
        const sortedLoads = [...this.state.point_loads].sort((a, b) => a.position - b.position);
        
        sortedLoads.forEach((pl, index) => {
            const plX = pl.position; // mm from left edge
            const plSVGX = this.toSVGX(plX);
            
            // Draw point load plate (90x45mm, cross-hatched)
            const plateY = beamY - (this.VISUAL.beamDepth * this.scaleY) / 2 - (this.VISUAL.flooringDepth * this.scaleY) - (this.VISUAL.plateHeight * this.scaleY) / 2;
            this.drawPlate(plX, plateY, true, pl.id);  // Pass loadId for identification
            
            // Label with magnitude above the plate
            const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
            label.setAttribute("x", plSVGX);
            label.setAttribute("y", plateY - (this.VISUAL.plateHeight * this.scaleY) / 2 - 10);
            label.setAttribute("text-anchor", "middle");
            label.setAttribute("font-size", "14");
            label.setAttribute("font-weight", "bold");
            label.setAttribute("fill", "#0066B3");
            label.textContent = `${pl.magnitude.toFixed(1)} kN`;
            label.style.cursor = "pointer";
            const originalIndex = this.state.point_loads.indexOf(pl);
            label.addEventListener('click', () => this.editPointLoadMagnitude(originalIndex));
            this.svg.appendChild(label);
            
            // Make plate draggable
            this.makePlateDraggable(pl.id, plX, plateY);
        });
        
        // Draw dimensions stacked by distance (longest on top)
        // Calculate distances and sort
        const leftInsideFace = this.getLeftInsideFace();
        const loadsWithDistance = sortedLoads.map((pl, idx) => ({
            load: pl,
            displayIndex: idx, // PL1, PL2, etc. based on position
            originalIndex: this.state.point_loads.indexOf(pl),
            distance: pl.position - leftInsideFace
        })).filter(item => item.distance > 0); // Only show dimensions for loads on the beam
        
        // Sort by distance (longest first) for stacking
        const loadsByDistance = [...loadsWithDistance].sort((a, b) => b.distance - a.distance);
        
        // Draw dimensions with vertical offset
        // Longest dimension on top (most negative Y offset)
        const baseDimY = beamY - 50;
        const verticalSpacing = 40;
        
        loadsByDistance.forEach((item, stackIndex) => {
            // Longest gets largest offset (most negative), so it's on top
            const dimY = baseDimY - ((loadsByDistance.length - 1 - stackIndex) * verticalSpacing);
            this.drawPointLoadDimension(item.load, item.displayIndex, item.originalIndex, beamY, dimY);
        });
    }
    
    drawPointLoadDimension(pl, displayIndex, originalIndex, beamY, dimY) {
        const leftInsideFace = this.getLeftInsideFace();
        const distanceFromLeft = pl.position - leftInsideFace; // mm
        
        if (distanceFromLeft <= 0) return; // Don't draw if before left support
        
        const x1 = this.toSVGX(leftInsideFace);
        const x2 = this.toSVGX(pl.position);
        
        const dimColor = "#999";
        
        // Vertical leader lines
        const leaderStart = beamY - 120;
        
        const leaderLine1 = document.createElementNS("http://www.w3.org/2000/svg", "line");
        leaderLine1.setAttribute("x1", x1);
        leaderLine1.setAttribute("y1", leaderStart);
        leaderLine1.setAttribute("x2", x1);
        leaderLine1.setAttribute("y2", dimY);
        leaderLine1.setAttribute("stroke", "#999");
        leaderLine1.setAttribute("stroke-width", "0.5");
        leaderLine1.setAttribute("stroke-dasharray", "2,2");
        this.svg.appendChild(leaderLine1);
        
        const leaderLine2 = document.createElementNS("http://www.w3.org/2000/svg", "line");
        leaderLine2.setAttribute("x1", x2);
        leaderLine2.setAttribute("y1", leaderStart);
        leaderLine2.setAttribute("x2", x2);
        leaderLine2.setAttribute("y2", dimY);
        leaderLine2.setAttribute("stroke", "#999");
        leaderLine2.setAttribute("stroke-width", "0.5");
        leaderLine2.setAttribute("stroke-dasharray", "2,2");
        this.svg.appendChild(leaderLine2);
        
        // Witness lines (forward slash style: /)
        const witnessLen = 10;
        
        const leftWitness = document.createElementNS("http://www.w3.org/2000/svg", "line");
        leftWitness.setAttribute("x1", x1 - witnessLen/2);
        leftWitness.setAttribute("y1", dimY + witnessLen/2);
        leftWitness.setAttribute("x2", x1 + witnessLen/2);
        leftWitness.setAttribute("y2", dimY - witnessLen/2);
        leftWitness.setAttribute("stroke", dimColor);
        leftWitness.setAttribute("stroke-width", "1.5");
        this.svg.appendChild(leftWitness);
        
        const rightWitness = document.createElementNS("http://www.w3.org/2000/svg", "line");
        rightWitness.setAttribute("x1", x2 - witnessLen/2);
        rightWitness.setAttribute("y1", dimY + witnessLen/2);
        rightWitness.setAttribute("x2", x2 + witnessLen/2);
        rightWitness.setAttribute("y2", dimY - witnessLen/2);
        rightWitness.setAttribute("stroke", dimColor);
        rightWitness.setAttribute("stroke-width", "1.5");
        this.svg.appendChild(rightWitness);
        
        // Dimension line
        const dimLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
        dimLine.setAttribute("x1", x1);
        dimLine.setAttribute("y1", dimY);
        dimLine.setAttribute("x2", x2);
        dimLine.setAttribute("y2", dimY);
        dimLine.setAttribute("stroke", dimColor);
        dimLine.setAttribute("stroke-width", "1");
        this.svg.appendChild(dimLine);
        
        // Label
        const midX = (x1 + x2) / 2;
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", midX);
        label.setAttribute("y", dimY - 5);
        label.setAttribute("text-anchor", "middle");
        label.setAttribute("font-size", "12");
        label.setAttribute("fill", dimColor);
        label.textContent = `${distanceFromLeft.toFixed(0)}`;
        label.style.cursor = "pointer";
        label.addEventListener('click', () => this.editPointLoadPosition(originalIndex));
        this.svg.appendChild(label);
        
        // Add "PLx" label above
        const plLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
        plLabel.setAttribute("x", midX);
        plLabel.setAttribute("y", dimY - 20);
        plLabel.setAttribute("text-anchor", "middle");
        plLabel.setAttribute("font-size", "12");
        plLabel.setAttribute("font-weight", "bold");
        plLabel.setAttribute("fill", "black");
        plLabel.textContent = `PL${displayIndex + 1}`;
        this.svg.appendChild(plLabel);
    }
    
    drawSpanDimension(beamY) {
        const span = this.getSpan();
        const leftInsideFace = this.getLeftInsideFace();
        const rightInsideFace = this.getRightInsideFace();
        
        const x1 = this.toSVGX(leftInsideFace);
        const x2 = this.toSVGX(rightInsideFace);
        const dimY = beamY + 60;
        
        // Vertical leader lines
        const leaderStart = beamY + 30;
        
        const leaderLine1 = document.createElementNS("http://www.w3.org/2000/svg", "line");
        leaderLine1.setAttribute("x1", x1);
        leaderLine1.setAttribute("y1", leaderStart);
        leaderLine1.setAttribute("x2", x1);
        leaderLine1.setAttribute("y2", dimY);
        leaderLine1.setAttribute("stroke", "#999");
        leaderLine1.setAttribute("stroke-width", "0.5");
        leaderLine1.setAttribute("stroke-dasharray", "2,2");
        this.svg.appendChild(leaderLine1);
        
        const leaderLine2 = document.createElementNS("http://www.w3.org/2000/svg", "line");
        leaderLine2.setAttribute("x1", x2);
        leaderLine2.setAttribute("y1", leaderStart);
        leaderLine2.setAttribute("x2", x2);
        leaderLine2.setAttribute("y2", dimY);
        leaderLine2.setAttribute("stroke", "#999");
        leaderLine2.setAttribute("stroke-width", "0.5");
        leaderLine2.setAttribute("stroke-dasharray", "2,2");
        this.svg.appendChild(leaderLine2);
        
        // Witness lines
        const witnessLen = 10;
        
        const leftWitness = document.createElementNS("http://www.w3.org/2000/svg", "line");
        leftWitness.setAttribute("x1", x1 - witnessLen/2);
        leftWitness.setAttribute("y1", dimY + witnessLen/2);
        leftWitness.setAttribute("x2", x1 + witnessLen/2);
        leftWitness.setAttribute("y2", dimY - witnessLen/2);
        leftWitness.setAttribute("stroke", "black");
        leftWitness.setAttribute("stroke-width", "1.5");
        this.svg.appendChild(leftWitness);
        
        const rightWitness = document.createElementNS("http://www.w3.org/2000/svg", "line");
        rightWitness.setAttribute("x1", x2 - witnessLen/2);
        rightWitness.setAttribute("y1", dimY + witnessLen/2);
        rightWitness.setAttribute("x2", x2 + witnessLen/2);
        rightWitness.setAttribute("y2", dimY - witnessLen/2);
        rightWitness.setAttribute("stroke", "black");
        rightWitness.setAttribute("stroke-width", "1.5");
        this.svg.appendChild(rightWitness);
        
        // Dimension line
        const dimLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
        dimLine.setAttribute("x1", x1);
        dimLine.setAttribute("y1", dimY);
        dimLine.setAttribute("x2", x2);
        dimLine.setAttribute("y2", dimY);
        dimLine.setAttribute("stroke", "black");
        dimLine.setAttribute("stroke-width", "1.5");
        this.svg.appendChild(dimLine);
        
        // Label (clickable)
        const midX = (x1 + x2) / 2;
        
        const labelBg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        labelBg.setAttribute("x", midX - 35);
        labelBg.setAttribute("y", dimY - 25);
        labelBg.setAttribute("width", 70);
        labelBg.setAttribute("height", 18);
        labelBg.setAttribute("fill", "white");
        labelBg.style.cursor = "pointer";
        labelBg.addEventListener('click', () => this.editSpan());
        this.svg.appendChild(labelBg);
        
        const labelText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        labelText.setAttribute("x", midX);
        labelText.setAttribute("y", dimY - 11);
        labelText.setAttribute("text-anchor", "middle");
        labelText.setAttribute("fill", "black");
        labelText.setAttribute("font-size", "12");
        labelText.setAttribute("font-weight", "bold");
        labelText.style.cursor = "pointer";
        labelText.textContent = "span";
        labelText.addEventListener('click', () => this.editSpan());
        this.svg.appendChild(labelText);
        
        // Dimension value
        const dimValue = document.createElementNS("http://www.w3.org/2000/svg", "text");
        dimValue.setAttribute("x", midX);
        dimValue.setAttribute("y", dimY + 15);
        dimValue.setAttribute("text-anchor", "middle");
        dimValue.setAttribute("font-size", "14");
        dimValue.setAttribute("font-weight", "bold");
        dimValue.setAttribute("fill", "black");
        dimValue.style.cursor = "pointer";
        dimValue.textContent = `${span.toFixed(0)}`;
        dimValue.addEventListener('click', () => this.editSpan());
        this.svg.appendChild(dimValue);
    }
    
    drawLoadInfo(beamY) {
        // Display UDL info below the span dimension for editing
        const leftStart = this.toSVGX(this.getLeftInsideFace());
        const rightEnd = this.toSVGX(this.getRightInsideFace());
        const udlMidX = (leftStart + rightEnd) / 2;
        
        // Position below span dimension (span is at beamY + 60)
        const spanDimY = beamY + 60;
        const udlInfoY = spanDimY + 35; // Below the span dimension
        
        const udlText = `UDL: ${this.state.udl.total.toFixed(2)} kN/m`;
        const spacingText = `@ ${(this.state.spacing * 1000).toFixed(0)}mm c/c`;
        
        // UDL label (clickable to edit)
        const udlLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
        udlLabel.setAttribute("x", udlMidX);
        udlLabel.setAttribute("y", udlInfoY);
        udlLabel.setAttribute("text-anchor", "middle");
        udlLabel.setAttribute("font-size", "14");
        udlLabel.setAttribute("fill", "#F69321"); // Lumberbank orange
        udlLabel.setAttribute("font-weight", "bold");
        udlLabel.textContent = udlText;
        udlLabel.style.cursor = "pointer";
        udlLabel.addEventListener('click', () => this.editLoads());
        this.svg.appendChild(udlLabel);
        
        // Spacing label (clickable to edit)
        const spacingLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
        spacingLabel.setAttribute("x", udlMidX);
        spacingLabel.setAttribute("y", udlInfoY + 18);
        spacingLabel.setAttribute("text-anchor", "middle");
        spacingLabel.setAttribute("font-size", "12");
        spacingLabel.setAttribute("fill", "#666");
        spacingLabel.textContent = spacingText;
        spacingLabel.style.cursor = "pointer";
        spacingLabel.addEventListener('click', () => this.editSpacing());
        this.svg.appendChild(spacingLabel);
    }
    
    drawToolbar() {
        // Add button in top-left to add point loads
        const btnX = 20;
        const btnY = 20;
        
        const btn = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        btn.setAttribute("x", btnX);
        btn.setAttribute("y", btnY);
        btn.setAttribute("width", 120);
        btn.setAttribute("height", 30);
        btn.setAttribute("fill", "#0066B3");
        btn.setAttribute("rx", "4");
        btn.style.cursor = "pointer";
        btn.addEventListener('click', () => this.addPointLoad());
        this.svg.appendChild(btn);
        
        const btnText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        btnText.setAttribute("x", btnX + 60);
        btnText.setAttribute("y", btnY + 20);
        btnText.setAttribute("text-anchor", "middle");
        btnText.setAttribute("font-size", "14");
        btnText.setAttribute("font-weight", "bold");
        btnText.setAttribute("fill", "white");
        btnText.style.cursor = "pointer";
        btnText.textContent = "+ Point Load";
        btnText.addEventListener('click', () => this.addPointLoad());
        btnText.style.pointerEvents = "none"; // Let clicks pass through to button
        this.svg.appendChild(btnText);
    }
    
    // ===================================================================
    // INTERACTIVITY - DRAGGING
    // ===================================================================
    
    makePlateDraggable(loadId, centerX, centerY) {
        // Find the plate rectangle by its data-load-id attribute
        const plateRect = this.svg.querySelector(`rect[data-load-id="${loadId}"]`);
        
        if (!plateRect) {
            console.warn('Could not find plate for loadId:', loadId);
            return;
        }
        
        plateRect.style.cursor = "grab";
        
        const self = this;
        let startX = 0;
        let startPosition = 0;
        
        plateRect.addEventListener('mousedown', function(e) {
            e.preventDefault();
            self.isDragging = true;
            self.draggedLoadId = loadId;
            startX = e.clientX;
            
            const pl = self.state.point_loads.find(pl => pl.id === loadId);
            startPosition = pl.position;
            
            plateRect.style.cursor = "grabbing";
            
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
        
        function onMouseMove(e) {
            if (!self.isDragging) return;
            
            const pl = self.state.point_loads.find(pl => pl.id === loadId);
            if (!pl) return;
            
            const deltaX = e.clientX - startX;
            const deltaMM = deltaX / self.scaleX;
            let newPosition = startPosition + deltaMM;
            
            // Snap to 50mm
            newPosition = Math.round(newPosition / 50) * 50;
            
            // Update position
            pl.position = newPosition;
            self.draw();
        }
        
        function onMouseUp() {
            self.isDragging = false;
            self.draggedLoadId = null;
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        }
    }
    
    // ===================================================================
    // EDIT HANDLERS
    // ===================================================================
    
    editSpan() {
        const currentSpan = this.getSpan();
        const newSpan = prompt(`Enter span (mm):`, currentSpan);
        
        if (newSpan && !isNaN(newSpan)) {
            const value = parseFloat(newSpan);
            
            if (value < 500 || value > 20000) {
                alert("⚠ Span must be between 500mm and 20000mm");
                return;
            }
            
            // Update right support position
            const leftPos = this.getLeftInsideFace();
            const rightSupport = this.state.supports.find(s => s.position > leftPos);
            if (rightSupport) {
                rightSupport.position = leftPos + value;
            }
            
            // Check if any point loads are now beyond the new span
            const newRightInsideFace = leftPos + value;
            let adjustedLoads = [];
            
            this.state.point_loads.forEach(pl => {
                if (pl.position > newRightInsideFace) {
                    // Move point load to right support position
                    pl.position = newRightInsideFace;
                    adjustedLoads.push(pl);
                }
            });
            
            // Notify user if any loads were adjusted
            if (adjustedLoads.length > 0) {
                const loadNames = adjustedLoads.map((pl, idx) => 
                    `PL${this.state.point_loads.indexOf(pl) + 1}`
                ).join(', ');
                alert(`ℹ️ ${loadNames} repositioned to end of beam. You can now reposition or delete as needed.`);
            }
            
            this.draw();
        }
    }
    
    editSpacing() {
        const currentSpacing = (this.state.spacing * 1000).toFixed(0);
        const newSpacing = prompt(`Enter spacing (mm):`, currentSpacing);
        
        if (newSpacing && !isNaN(newSpacing)) {
            const value = parseFloat(newSpacing) / 1000;
            
            if (value < 0.3 || value > 1.2) {
                alert("⚠ Spacing must be between 300mm and 1200mm");
                return;
            }
            
            this.state.spacing = value;
            this.calculateUDL();
            this.draw();
        }
    }
    
    editLoads() {
        // Create popup form for load editing
        const deadLoad = prompt(`Dead load (kPa):`, this.state.udl.dead_load);
        if (deadLoad === null) return;
        
        const liveLoad = prompt(`Live load (kPa):`, this.state.udl.live_load);
        if (liveLoad === null) return;
        
        const sdl = prompt(`SDL (kPa):`, this.state.udl.sdl);
        if (sdl === null) return;
        
        this.state.udl.dead_load = parseFloat(deadLoad);
        this.state.udl.live_load = parseFloat(liveLoad);
        this.state.udl.sdl = parseFloat(sdl);
        this.calculateUDL();
        this.draw();
    }
    
    editPointLoadMagnitude(index) {
        const pl = this.state.point_loads[index];
        const newMag = prompt(`Point load magnitude (kN):`, pl.magnitude.toFixed(1));
        
        if (newMag && !isNaN(newMag)) {
            pl.magnitude = parseFloat(newMag);
            this.draw();
        }
    }
    
    editPointLoadPosition(index) {
        const pl = this.state.point_loads[index];
        const leftInsideFace = this.getLeftInsideFace();
        const span = this.getSpan();
        const currentDist = pl.position - leftInsideFace;
        
        const newDist = prompt(`Distance from left support (mm):`, currentDist.toFixed(0));
        
        if (newDist && !isNaN(newDist)) {
            let value = parseFloat(newDist);
            
            if (value < 0 || value > span) {
                alert(`⚠ Position must be between 0 and ${span.toFixed(0)}mm`);
                return;
            }
            
            // Snap to 50mm
            value = Math.round(value / 50) * 50;
            
            // Convert from dimension (from support inside face) to absolute position (center of plate)
            pl.position = leftInsideFace + value;
            this.draw();
        }
    }
    
    addPointLoad() {
        const leftInsideFace = this.getLeftInsideFace();
        const span = this.getSpan();
        const position = leftInsideFace + (span / 2); // Default to midspan (center of plate)
        
        this.state.point_loads.push({
            id: `pl_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            magnitude: 10.0,
            position: position // mm - absolute position (center of plate)
        });
        
        this.draw();
    }
    
    // ===================================================================
    // FORM SYNCHRONIZATION
    // ===================================================================
    
    syncFormFields() {
        const span = this.getSpan();
        
        const spanInput = document.getElementById('span_input');
        if (spanInput) spanInput.value = span / 1000; // Convert to meters
        
        const spacingInput = document.getElementById('spacing_input');
        if (spacingInput) spacingInput.value = this.state.spacing;
        
        const deadLoadInput = document.getElementById('dead_load_input');
        if (deadLoadInput) deadLoadInput.value = this.state.udl.dead_load;
        
        const liveLoadInput = document.getElementById('live_load_input');
        if (liveLoadInput) liveLoadInput.value = this.state.udl.live_load;
        
        // Point loads - convert positions to meters from left support for backend
        this.state.point_loads.forEach((pl, i) => {
            const posMeters = pl.position / 1000;
            if (i === 0) {
                const pl1Input = document.getElementById('pl1_input');
                const pl1PosInput = document.getElementById('pl1_pos_input');
                if (pl1Input) pl1Input.value = pl.magnitude;
                if (pl1PosInput) pl1PosInput.value = posMeters;
            } else if (i === 1) {
                const pl2Input = document.getElementById('pl2_input');
                const pl2PosInput = document.getElementById('pl2_pos_input');
                if (pl2Input) pl2Input.value = pl.magnitude;
                if (pl2PosInput) pl2PosInput.value = posMeters;
            }
        });
        
        const supportsInput = document.getElementById('supports_input');
        if (supportsInput) supportsInput.value = JSON.stringify(this.state.supports);
    }
    
    // ===================================================================
    // PUBLIC API
    // ===================================================================
    
    getState() {
        return this.state;
    }
    
    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.calculateUDL();
        this.draw();
    }
}

// Export for use in other scripts
// Note: Instantiate as: window.beamCanvas = new BeamCanvas('container-id', options)