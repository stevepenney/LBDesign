/**
 * Interactive SVG Beam Canvas - NZ Style Elevation
 * 
 * Provides visual, interactive beam design interface
 * User can click elements to edit values, drag point loads, etc.
 */

class BeamCanvas {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.svg = null;
        this.scale = 0.15; // pixels per mm (150px per meter = 0.15px per mm)
        this.padding = { top: 100, right: 100, bottom: 80, left: 100 };
        
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
        // Create SVG element
        let width = this.container.offsetWidth;
        
        if (width === 0) {
            width = 800;
            console.log('Container not visible yet, using default width:', width);
        }
        
        const height = 500;
        
        console.log('Container width:', width, 'SVG height:', height);
        
        this.svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        this.svg.setAttribute("width", "100%");
        this.svg.setAttribute("height", height);
        this.svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        this.svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
        this.svg.style.border = "1px solid #e5e7eb";
        this.svg.style.borderRadius = "8px";
        this.svg.style.backgroundColor = "white";
        this.svg.style.display = "block";
        this.svg.style.maxWidth = "100%";
        
        this.container.innerHTML = '';
        this.container.appendChild(this.svg);
        
        this.draw();
    }
    
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
        return this.padding.left + (mm * this.scale);
    }
    
    toSVGY(y) {
        return y;
    }
    
    // Convert SVG coordinates back to mm
    fromSVGX(svgX) {
        return (svgX - this.padding.left) / this.scale;
    }
    
    // Main draw function
    draw() {
        console.log('Drawing NZ-style beam elevation...', this.state);
        
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
    
    drawPlate(centerX, centerY, isCrossHatched = true) {
        // Draw a 90x45mm plate centered at the given position
        const plateW = this.VISUAL.plateWidth * this.scale;
        const plateH = this.VISUAL.plateHeight * this.scale;
        
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
        beam.setAttribute("y", beamY - (beamDepth * this.scale) / 2);
        beam.setAttribute("width", x2 - x1);
        beam.setAttribute("height", beamDepth * this.scale);
        beam.setAttribute("fill", "white");
        beam.setAttribute("stroke", "black");
        beam.setAttribute("stroke-width", "2");
        this.svg.appendChild(beam);
        
        // Draw flooring layer on top
        const flooring = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        flooring.setAttribute("x", x1);
        flooring.setAttribute("y", beamY - (beamDepth * this.scale) / 2 - (flooringDepth * this.scale));
        flooring.setAttribute("width", x2 - x1);
        flooring.setAttribute("height", flooringDepth * this.scale);
        flooring.setAttribute("fill", "#D2B48C"); // Light tan color
        flooring.setAttribute("stroke", "black");
        flooring.setAttribute("stroke-width", "1");
        this.svg.appendChild(flooring);
    }
    
    drawSupports(beamY) {
        const leftInsideFace = this.getLeftInsideFace();
        const rightInsideFace = this.getRightInsideFace();
        
        // Left wall plate - centered at x=45mm (inside face at x=90mm)
        const leftWallCenter = leftInsideFace - 45;
        const wallCenterY = beamY + (this.VISUAL.beamDepth * this.scale) / 2 + (this.VISUAL.plateHeight * this.scale) / 2;
        this.drawPlate(leftWallCenter, wallCenterY, true);
        
        // Right wall plate - centered at right inside face + 45mm
        const rightWallCenter = rightInsideFace + 45;
        this.drawPlate(rightWallCenter, wallCenterY, true);
    }
    
    drawPointLoads(beamY) {
        const leftInsideFace = this.getLeftInsideFace();
        const span = this.getSpan();
        
        // Sort point loads left to right for display
        const sortedLoads = [...this.state.point_loads].sort((a, b) => a.position - b.position);
        
        sortedLoads.forEach((pl, visualIndex) => {
            // pl.position is absolute position (center of plate)
            const plateCenter = pl.position;
            
            // Calculate dimension from left inside face
            const dimFromSupport = plateCenter - leftInsideFace;
            
            // Check if excluded from calculation (within 100mm of either support)
            const isExcluded = dimFromSupport < 100 || dimFromSupport > (span - 100);
            
            // Draw plate above beam (on top of flooring)
            const plateCenterY = beamY - (this.VISUAL.beamDepth * this.scale) / 2 - (this.VISUAL.flooringDepth * this.scale) - (this.VISUAL.plateHeight * this.scale) / 2;
            const plate = this.drawPlate(plateCenter, plateCenterY, true);
            
            // Make plate draggable
            plate.style.cursor = "move";
            plate.dataset.loadId = pl.id;
            this.addDragHandlers(plate, pl.id);
            
            // Magnitude label above plate
            const x = this.toSVGX(plateCenter);
            const magText = document.createElementNS("http://www.w3.org/2000/svg", "text");
            magText.setAttribute("x", x);
            magText.setAttribute("y", plateCenterY - (this.VISUAL.plateHeight * this.scale) / 2 - 5);
            magText.setAttribute("text-anchor", "middle");
            magText.setAttribute("fill", "black");
            magText.setAttribute("font-size", "12");
            magText.setAttribute("font-weight", "bold");
            magText.style.cursor = "pointer";
            magText.textContent = `${pl.magnitude.toFixed(1)} kN`;
            magText.addEventListener('click', () => this.editPointLoadMagnitude(pl.id));
            this.svg.appendChild(magText);
            
            // Add tooltip if excluded
            if (isExcluded) {
                const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
                title.textContent = "Within 100mm of support - excluded from calculation";
                magText.appendChild(title);
            }
            
            // Dimension line to this point load (stacked vertically)
            this.drawPointLoadDimension(dimFromSupport, visualIndex, sortedLoads.length, beamY, isExcluded, pl.id);
        });
    }
    
    drawPointLoadDimension(dimFromSupport, visualIndex, totalLoads, beamY, isExcluded, loadId) {
        const leftInsideFace = this.getLeftInsideFace();
        const span = this.getSpan();
        
        // REVERSED Vertical stacking: longest dimension at top
        // If 3 loads: index 0 (shortest) at bottom, index 2 (longest) at top
        const baseOffset = -60;  // Start from bottom
        const stackIncrement = -40;  // Go upward (more negative)
        const reverseIndex = totalLoads - 1 - visualIndex;  // Reverse the index
        const dimY = beamY + baseOffset + (reverseIndex * stackIncrement);
        
        const x1 = this.toSVGX(leftInsideFace);
        const x2 = this.toSVGX(leftInsideFace + dimFromSupport);
        
        const dimColor = isExcluded ? "#999" : "black";
        
        // Vertical leader lines (thin grey, longer - closer to beam)
        const leaderStart = beamY - 120; // Closer to beam
        
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
        const label = `PL${visualIndex + 1}`;
        const midX = (x1 + x2) / 2;
        
        // Background box
        const labelBg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        labelBg.setAttribute("x", midX - 20);
        labelBg.setAttribute("y", dimY - 22);
        labelBg.setAttribute("width", 40);
        labelBg.setAttribute("height", 16);
        labelBg.setAttribute("fill", "white");
        this.svg.appendChild(labelBg);
        
        // Label text (clickable for editing position)
        const labelText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        labelText.setAttribute("x", midX);
        labelText.setAttribute("y", dimY - 10);
        labelText.setAttribute("text-anchor", "middle");
        labelText.setAttribute("fill", dimColor);
        labelText.setAttribute("font-size", "11");
        labelText.setAttribute("font-weight", "bold");
        labelText.style.cursor = "pointer";
        labelText.textContent = label;
        labelText.addEventListener('click', () => this.editPointLoadPosition(loadId));
        
        // Add tooltip if excluded
        if (isExcluded) {
            const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
            title.textContent = "Within 100mm of support - excluded from calculation";
            labelText.appendChild(title);
        }
        
        this.svg.appendChild(labelText);
        
        // Dimension value (also clickable for editing position)
        const dimValue = document.createElementNS("http://www.w3.org/2000/svg", "text");
        dimValue.setAttribute("x", midX);
        dimValue.setAttribute("y", dimY + 15);
        dimValue.setAttribute("text-anchor", "middle");
        dimValue.setAttribute("fill", dimColor);
        dimValue.setAttribute("font-size", "11");
        dimValue.style.cursor = "pointer";
        dimValue.textContent = `${Math.round(dimFromSupport)}`;
        dimValue.addEventListener('click', () => this.editPointLoadPosition(loadId));
        
        if (isExcluded) {
            const title2 = document.createElementNS("http://www.w3.org/2000/svg", "title");
            title2.textContent = "Within 100mm of support - excluded from calculation";
            dimValue.appendChild(title2);
        }
        
        this.svg.appendChild(dimValue);
    }
    
    drawSpanDimension(beamY) {
        const leftInsideFace = this.getLeftInsideFace();
        const rightInsideFace = this.getRightInsideFace();
        const span = this.getSpan();
        
        const x1 = this.toSVGX(leftInsideFace);
        const x2 = this.toSVGX(rightInsideFace);
        const dimY = beamY + 220; // Below beam
        
        // Vertical leader lines (thin grey)
        const leaderLine1 = document.createElementNS("http://www.w3.org/2000/svg", "line");
        leaderLine1.setAttribute("x1", x1);
        leaderLine1.setAttribute("y1", beamY + 100);
        leaderLine1.setAttribute("x2", x1);
        leaderLine1.setAttribute("y2", dimY);
        leaderLine1.setAttribute("stroke", "#999");
        leaderLine1.setAttribute("stroke-width", "0.5");
        leaderLine1.setAttribute("stroke-dasharray", "2,2");
        this.svg.appendChild(leaderLine1);
        
        const leaderLine2 = document.createElementNS("http://www.w3.org/2000/svg", "line");
        leaderLine2.setAttribute("x1", x2);
        leaderLine2.setAttribute("y1", beamY + 100);
        leaderLine2.setAttribute("x2", x2);
        leaderLine2.setAttribute("y2", dimY);
        leaderLine2.setAttribute("stroke", "#999");
        leaderLine2.setAttribute("stroke-width", "0.5");
        leaderLine2.setAttribute("stroke-dasharray", "2,2");
        this.svg.appendChild(leaderLine2);
        
        // Witness lines (forward slash style: /)
        const witnessLen = 12;
        
        // Left witness line (/)
        const leftWitness = document.createElementNS("http://www.w3.org/2000/svg", "line");
        leftWitness.setAttribute("x1", x1 - witnessLen/2);
        leftWitness.setAttribute("y1", dimY + witnessLen/2);
        leftWitness.setAttribute("x2", x1 + witnessLen/2);
        leftWitness.setAttribute("y2", dimY - witnessLen/2);
        leftWitness.setAttribute("stroke", "black");
        leftWitness.setAttribute("stroke-width", "2");
        this.svg.appendChild(leftWitness);
        
        // Right witness line (/)
        const rightWitness = document.createElementNS("http://www.w3.org/2000/svg", "line");
        rightWitness.setAttribute("x1", x2 - witnessLen/2);
        rightWitness.setAttribute("y1", dimY + witnessLen/2);
        rightWitness.setAttribute("x2", x2 + witnessLen/2);
        rightWitness.setAttribute("y2", dimY - witnessLen/2);
        rightWitness.setAttribute("stroke", "black");
        rightWitness.setAttribute("stroke-width", "2");
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
        dimValue.setAttribute("y", dimY + 20);
        dimValue.setAttribute("text-anchor", "middle");
        dimValue.setAttribute("fill", "black");
        dimValue.setAttribute("font-size", "13");
        dimValue.setAttribute("font-weight", "bold");
        dimValue.style.cursor = "pointer";
        dimValue.textContent = `${Math.round(span)}`;
        dimValue.addEventListener('click', () => this.editSpan());
        this.svg.appendChild(dimValue);
    }
    
    drawLoadInfo(beamY) {
        // Show just total UDL in brown color (clickable for editing all loads)
        const leftInsideFace = this.getLeftInsideFace();
        const span = this.getSpan();
        const midX = this.toSVGX(leftInsideFace + span/2);
        
        const loadY = beamY - 50;
        
        // Total UDL text (clickable)
        const totalText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        totalText.setAttribute("x", midX);
        totalText.setAttribute("y", loadY);
        totalText.setAttribute("text-anchor", "middle");
        totalText.setAttribute("fill", "#8B6F47");
        totalText.setAttribute("font-size", "14");
        totalText.setAttribute("font-weight", "bold");
        totalText.style.cursor = "pointer";
        totalText.textContent = `${this.state.udl.total.toFixed(2)} kN/m`;
        totalText.addEventListener('click', () => this.editLoads());
        
        // Hover effect
        totalText.addEventListener('mouseenter', () => {
            totalText.setAttribute("fill", "#F69321");
        });
        totalText.addEventListener('mouseleave', () => {
            totalText.setAttribute("fill", "#8B6F47");
        });
        
        this.svg.appendChild(totalText);
    }
    
    drawToolbar() {
        const existingToolbar = this.container.querySelector('.beam-toolbar');
        if (existingToolbar) {
            existingToolbar.remove();
        }
        
        const toolbar = document.createElement('div');
        toolbar.className = 'beam-toolbar';
        toolbar.style.cssText = `
            display: flex;
            gap: 1rem;
            padding: 1rem;
            background: white;
            border-bottom: 1px solid #e5e7eb;
            margin-bottom: 1rem;
            align-items: center;
        `;
        
        // Add Point Load button
        const addPLBtn = document.createElement('button');
        addPLBtn.className = 'btn btn-secondary';
        addPLBtn.textContent = '+ Add Point Load';
        addPLBtn.onclick = () => this.addPointLoad();
        toolbar.appendChild(addPLBtn);
        
        // Spacing input (for joists/rafters)
        if (this.state.member_type === 'floor_joist' || this.state.member_type === 'rafter') {
            const spacingLabel = document.createElement('span');
            spacingLabel.style.cssText = 'display: flex; align-items: center; gap: 0.5rem;';
            spacingLabel.innerHTML = `
                <strong>Spacing:</strong>
                <span style="color: #8B6F47; cursor: pointer; text-decoration: underline;" 
                      id="spacing-label">
                    ${(this.state.spacing * 1000).toFixed(0)}mm crs
                </span>
            `;
            toolbar.appendChild(spacingLabel);
            
            setTimeout(() => {
                const label = document.getElementById('spacing-label');
                if (label) {
                    label.onclick = () => this.editSpacing();
                }
            }, 0);
        }
        
        this.container.insertBefore(toolbar, this.svg);
    }
    
    // ===================================================================
    // DRAG AND DROP FOR POINT LOADS
    // ===================================================================
    
    addDragHandlers(element, loadId) {
        const self = this;
        let startX = 0;
        let startPosition = 0;
        
        element.addEventListener('mousedown', function(e) {
            e.preventDefault();
            self.isDragging = true;
            self.draggedLoadId = loadId;
            startX = e.clientX;
            
            const pl = self.state.point_loads.find(pl => pl.id === loadId);
            if (!pl) return;
            
            startPosition = pl.position;
            
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
        
        function onMouseMove(e) {
            if (!self.isDragging) return;
            
            const pl = self.state.point_loads.find(pl => pl.id === loadId);
            if (!pl) return;
            
            const deltaX = e.clientX - startX;
            const deltaMM = deltaX / self.scale;
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
        const popup = this.createLoadEditPopup();
        document.body.appendChild(popup);
    }
    
    createLoadEditPopup() {
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        // Create popup form
        const popup = document.createElement('div');
        popup.style.cssText = `
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.2);
            max-width: 400px;
            width: 90%;
        `;
        
        popup.innerHTML = `
            <h3 style="margin: 0 0 1rem 0;">Edit Floor Loading</h3>
            
            <div style="margin-bottom: 1rem;">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Live Load (LL) - kPa</label>
                <input type="number" id="ll-input" value="${this.state.udl.live_load}" step="0.1" 
                       style="width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 4px;">
            </div>
            
            <div style="margin-bottom: 1rem;">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Dead Load (DL) - kPa</label>
                <input type="number" id="dl-input" value="${this.state.udl.dead_load}" step="0.1"
                       style="width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 4px;">
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Superimposed DL (SDL) - kPa</label>
                <input type="number" id="sdl-input" value="${this.state.udl.sdl}" step="0.1"
                       style="width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 4px;">
            </div>
            
            ${this.state.member_type === 'floor_joist' || this.state.member_type === 'rafter' ? `
            <div style="margin-bottom: 1.5rem;">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Spacing - mm</label>
                <input type="number" id="spacing-popup-input" value="${(this.state.spacing * 1000).toFixed(0)}" step="10"
                       style="width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 4px;">
            </div>
            ` : ''}
            
            <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                <button id="cancel-btn" style="padding: 0.5rem 1rem; border: 1px solid #d1d5db; background: white; border-radius: 4px; cursor: pointer;">
                    Cancel
                </button>
                <button id="save-btn" style="padding: 0.5rem 1rem; background: #8B6F47; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">
                    Save
                </button>
            </div>
        `;
        
        overlay.appendChild(popup);
        
        // Event handlers
        const saveBtn = popup.querySelector('#save-btn');
        const cancelBtn = popup.querySelector('#cancel-btn');
        
        saveBtn.onclick = () => {
            this.state.udl.live_load = parseFloat(popup.querySelector('#ll-input').value);
            this.state.udl.dead_load = parseFloat(popup.querySelector('#dl-input').value);
            this.state.udl.sdl = parseFloat(popup.querySelector('#sdl-input').value);
            
            if (this.state.member_type === 'floor_joist' || this.state.member_type === 'rafter') {
                const spacingInput = popup.querySelector('#spacing-popup-input');
                if (spacingInput) {
                    this.state.spacing = parseFloat(spacingInput.value) / 1000;
                }
            }
            
            this.calculateUDL();
            this.draw();
            document.body.removeChild(overlay);
        };
        
        cancelBtn.onclick = () => {
            document.body.removeChild(overlay);
        };
        
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
            }
        };
        
        return overlay;
    }
    
    editPointLoadMagnitude(loadId) {
        const pl = this.state.point_loads.find(pl => pl.id === loadId);
        if (!pl) return;
        
        const newMag = prompt(`Point load magnitude (kN):`, pl.magnitude.toFixed(1));
        
        if (newMag && !isNaN(newMag)) {
            pl.magnitude = parseFloat(newMag);
            this.draw();
        }
    }
    
    editPointLoadPosition(loadId) {
        const pl = this.state.point_loads.find(pl => pl.id === loadId);
        if (!pl) return;
        
        const leftInsideFace = this.getLeftInsideFace();
        const dimFromSupport = pl.position - leftInsideFace;
        
        const newPos = prompt(`Point load position from left support inside face (mm):`, Math.round(dimFromSupport));
        
        if (newPos && !isNaN(newPos)) {
            let value = parseFloat(newPos);
            
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