/**
 * Interactive SVG Beam Canvas
 * 
 * Provides visual, interactive beam design interface
 * User can click elements to edit values, drag point loads, etc.
 */

class BeamCanvas {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.svg = null;
        this.scale = 100; // pixels per meter
        this.padding = { top: 60, right: 40, bottom: 60, left: 40 };
        
        // Beam state - single source of truth
        this.state = {
            name: options.name || "Beam-1",
            member_type: options.member_type || null,
            spacing: options.spacing || 0.4, // meters
            
            supports: options.supports || [
                { position: 0.0, type: "pinned" },
                { position: 6.0, type: "pinned" }
            ],
            
            udl: options.udl || {
                dead_load: 0.5,  // kPa
                live_load: 1.5,  // kPa
                total: 0         // Calculated
            },
            
            point_loads: options.point_loads || [],
            
            results: options.results || null
        };
        
        this.calculateUDL();
        this.initialize();
    }
    
    initialize() {
        // Create SVG element
        // Use offsetWidth if available, otherwise use a default width
        let width = this.container.offsetWidth;
        
        // If container is hidden (display: none), offsetWidth will be 0
        // Use a sensible default instead
        if (width === 0) {
            width = 800; // Default width
            console.log('Container not visible yet, using default width:', width);
        }
        
        const height = 400;
        
        console.log('Container width:', width, 'SVG height:', height);
        
        this.svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        this.svg.setAttribute("width", "100%");  // Use 100% to be responsive
        this.svg.setAttribute("height", height);
        this.svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        this.svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
        this.svg.style.border = "1px solid #e5e7eb";
        this.svg.style.borderRadius = "8px";
        this.svg.style.backgroundColor = "#fafafa";
        this.svg.style.display = "block";
        this.svg.style.maxWidth = "100%";
        
        this.container.innerHTML = '';
        this.container.appendChild(this.svg);
        
        console.log('SVG created, dimensions:', this.svg.getAttribute('width'), 'x', this.svg.getAttribute('height'));
        
        this.draw();
    }
    
    // Calculate total UDL from components
    calculateUDL() {
        const total_kPa = this.state.udl.dead_load + this.state.udl.live_load;
        this.state.udl.total = total_kPa * this.state.spacing;
    }
    
    // Get total beam length
    getTotalLength() {
        if (this.state.supports.length === 0) return 6.0;
        const positions = this.state.supports.map(s => s.position);
        return Math.max(...positions);
    }
    
    // Convert real coordinates to SVG coordinates
    toSVGX(meters) {
        return this.padding.left + (meters * this.scale);
    }
    
    toSVGY(baseY) {
        return baseY;
    }
    
    // Main draw function - redraws entire SVG from state
    draw() {
        console.log('Drawing beam canvas...', this.state);
        
        // Clear SVG
        while (this.svg.firstChild) {
            this.svg.removeChild(this.svg.firstChild);
        }
        
        const totalLength = this.getTotalLength();
        const beamY = 150; // Base Y position for beam line
        
        console.log('Total length:', totalLength, 'Beam Y:', beamY);
        
        // Draw beam line
        this.drawBeamLine(totalLength, beamY);
        
        // Draw supports
        this.state.supports.forEach(support => {
            this.drawSupport(support, beamY);
        });
        
        // Draw span dimensions
        this.drawSpanDimensions(beamY);
        
        // Draw UDL
        if (this.state.udl.total > 0) {
            this.drawUDL(totalLength, beamY);
        }
        
        // Draw point loads
        this.state.point_loads.forEach((pl, index) => {
            this.drawPointLoad(pl, index, beamY);
        });
        
        // Draw toolbar
        this.drawToolbar();
        
        // Sync hidden form fields
        this.syncFormFields();
        
        console.log('SVG elements:', this.svg.childNodes.length);
    }
    
    drawBeamLine(length, y) {
        const x1 = this.toSVGX(0);
        const x2 = this.toSVGX(length);
        const beamDepth = 30; // Visual depth of beam (not to scale)
        
        console.log('Drawing beam from', x1, y, 'to', x2, y);
        
        // Draw beam as a rectangle (timber color)
        const beam = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        beam.setAttribute("x", x1);
        beam.setAttribute("y", y - beamDepth/2);
        beam.setAttribute("width", x2 - x1);
        beam.setAttribute("height", beamDepth);
        beam.setAttribute("fill", "#D4A574"); // Timber color
        beam.setAttribute("stroke", "#8B6F47"); // Darker timber outline
        beam.setAttribute("stroke-width", "2");
        beam.setAttribute("rx", "2"); // Slight rounded corners
        this.svg.appendChild(beam);
        
        // Add wood grain effect (optional detail)
        const grain1 = document.createElementNS("http://www.w3.org/2000/svg", "line");
        grain1.setAttribute("x1", x1 + 20);
        grain1.setAttribute("y1", y - beamDepth/2 + 5);
        grain1.setAttribute("x2", x1 + 20);
        grain1.setAttribute("y2", y + beamDepth/2 - 5);
        grain1.setAttribute("stroke", "#C89F6C");
        grain1.setAttribute("stroke-width", "1");
        grain1.setAttribute("opacity", "0.3");
        this.svg.appendChild(grain1);
    }
    
    drawSupport(support, beamY) {
        const x = this.toSVGX(support.position);
        const beamDepth = 30;
        const plateWidth = 40;
        const plateHeight = 15;
        const wallHeight = 60;
        
        if (support.type === "pinned") {
            // Draw wall (concrete/brick)
            const wall = document.createElementNS("http://www.w3.org/2000/svg", "rect");
            wall.setAttribute("x", x - plateWidth/2);
            wall.setAttribute("y", beamY + beamDepth/2);
            wall.setAttribute("width", plateWidth);
            wall.setAttribute("height", wallHeight);
            wall.setAttribute("fill", "#CCCCCC"); // Concrete gray
            wall.setAttribute("stroke", "#999999");
            wall.setAttribute("stroke-width", "1");
            this.svg.appendChild(wall);
            
            // Add brick pattern
            for (let i = 0; i < 3; i++) {
                const brickLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
                brickLine.setAttribute("x1", x - plateWidth/2);
                brickLine.setAttribute("y1", beamY + beamDepth/2 + (i * 20));
                brickLine.setAttribute("x2", x + plateWidth/2);
                brickLine.setAttribute("y2", beamY + beamDepth/2 + (i * 20));
                brickLine.setAttribute("stroke", "#999999");
                brickLine.setAttribute("stroke-width", "1");
                this.svg.appendChild(brickLine);
            }
            
            // Draw timber bearing plate on top of wall
            const plate = document.createElementNS("http://www.w3.org/2000/svg", "rect");
            plate.setAttribute("x", x - plateWidth/2);
            plate.setAttribute("y", beamY + beamDepth/2 - plateHeight);
            plate.setAttribute("width", plateWidth);
            plate.setAttribute("height", plateHeight);
            plate.setAttribute("fill", "#D4A574"); // Timber color
            plate.setAttribute("stroke", "#8B6F47");
            plate.setAttribute("stroke-width", "2");
            this.svg.appendChild(plate);
            
            // Clickable area for editing support
            const clickArea = document.createElementNS("http://www.w3.org/2000/svg", "rect");
            clickArea.setAttribute("x", x - plateWidth/2);
            clickArea.setAttribute("y", beamY - beamDepth/2);
            clickArea.setAttribute("width", plateWidth);
            clickArea.setAttribute("height", beamDepth + plateHeight + wallHeight);
            clickArea.setAttribute("fill", "transparent");
            clickArea.style.cursor = "pointer";
            clickArea.addEventListener('click', () => this.editSupport(support));
            this.svg.appendChild(clickArea);
        }
        // TODO: Add roller, fixed support types with different visuals
    }
    
    drawSpanDimensions(beamY) {
        const supports = [...this.state.supports].sort((a, b) => a.position - b.position);
        
        // Draw total length
        const totalLength = this.getTotalLength();
        this.drawDimensionLine(
            0, totalLength, beamY - 40,
            `Span: ${totalLength.toFixed(2)}m`,
            () => this.editSpan()
        );
    }
    
    drawDimensionLine(start, end, y, label, clickHandler) {
        const x1 = this.toSVGX(start);
        const x2 = this.toSVGX(end);
        const midX = (x1 + x2) / 2;
        
        // Dimension line with witness lines
        const witnessHeight = 8;
        
        // Left witness line
        const leftWitness = document.createElementNS("http://www.w3.org/2000/svg", "line");
        leftWitness.setAttribute("x1", x1);
        leftWitness.setAttribute("y1", y - witnessHeight);
        leftWitness.setAttribute("x2", x1);
        leftWitness.setAttribute("y2", y + witnessHeight);
        leftWitness.setAttribute("stroke", "#374151");
        leftWitness.setAttribute("stroke-width", "1.5");
        this.svg.appendChild(leftWitness);
        
        // Right witness line
        const rightWitness = document.createElementNS("http://www.w3.org/2000/svg", "line");
        rightWitness.setAttribute("x1", x2);
        rightWitness.setAttribute("y1", y - witnessHeight);
        rightWitness.setAttribute("x2", x2);
        rightWitness.setAttribute("y2", y + witnessHeight);
        rightWitness.setAttribute("stroke", "#374151");
        rightWitness.setAttribute("stroke-width", "1.5");
        this.svg.appendChild(rightWitness);
        
        // Main dimension line
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", x1);
        line.setAttribute("y1", y);
        line.setAttribute("x2", x2);
        line.setAttribute("y2", y);
        line.setAttribute("stroke", "#374151");
        line.setAttribute("stroke-width", "1.5");
        this.svg.appendChild(line);
        
        // Arrow heads at ends
        const arrowSize = 5;
        
        // Left arrow
        const leftArrow = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        const leftPoints = `${x1},${y} ${x1+arrowSize},${y-arrowSize/2} ${x1+arrowSize},${y+arrowSize/2}`;
        leftArrow.setAttribute("points", leftPoints);
        leftArrow.setAttribute("fill", "#374151");
        this.svg.appendChild(leftArrow);
        
        // Right arrow
        const rightArrow = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        const rightPoints = `${x2},${y} ${x2-arrowSize},${y-arrowSize/2} ${x2-arrowSize},${y+arrowSize/2}`;
        rightArrow.setAttribute("points", rightPoints);
        rightArrow.setAttribute("fill", "#374151");
        this.svg.appendChild(rightArrow);
        
        // Label background
        const labelWidth = 80;
        const labelHeight = 22;
        const labelBg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        labelBg.setAttribute("x", midX - labelWidth/2);
        labelBg.setAttribute("y", y - labelHeight/2);
        labelBg.setAttribute("width", labelWidth);
        labelBg.setAttribute("height", labelHeight);
        labelBg.setAttribute("fill", "white");
        labelBg.setAttribute("stroke", "#8B6F47");
        labelBg.setAttribute("stroke-width", "1.5");
        labelBg.setAttribute("rx", "4");
        labelBg.style.cursor = "pointer";
        labelBg.addEventListener('click', clickHandler);
        this.svg.appendChild(labelBg);
        
        // Label text (clickable)
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", midX);
        text.setAttribute("y", y + 5);
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("fill", "#8B6F47");
        text.setAttribute("font-weight", "600");
        text.setAttribute("font-size", "13");
        text.style.cursor = "pointer";
        text.textContent = label;
        text.addEventListener('click', clickHandler);
        
        // Hover effect
        const hoverIn = () => {
            text.setAttribute("fill", "#F69321");
            labelBg.setAttribute("stroke", "#F69321");
            labelBg.setAttribute("fill", "#fffbf0");
        };
        const hoverOut = () => {
            text.setAttribute("fill", "#8B6F47");
            labelBg.setAttribute("stroke", "#8B6F47");
            labelBg.setAttribute("fill", "white");
        };
        
        text.addEventListener('mouseenter', hoverIn);
        text.addEventListener('mouseleave', hoverOut);
        labelBg.addEventListener('mouseenter', hoverIn);
        labelBg.addEventListener('mouseleave', hoverOut);
        
        this.svg.appendChild(text);
    }
    
    drawUDL(length, beamY) {
        const arrowSpacing = 0.6; // meters between arrows (slightly wider)
        const numArrows = Math.floor(length / arrowSpacing);
        const beamDepth = 30;
        const arrowStartY = beamY - beamDepth/2 - 45; // Start arrows above beam
        const arrowLength = 35;
        
        // Draw load distribution line
        const loadLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
        loadLine.setAttribute("x1", this.toSVGX(0));
        loadLine.setAttribute("y1", arrowStartY);
        loadLine.setAttribute("x2", this.toSVGX(length));
        loadLine.setAttribute("y2", arrowStartY);
        loadLine.setAttribute("stroke", "#ef4444");
        loadLine.setAttribute("stroke-width", "2");
        loadLine.setAttribute("stroke-dasharray", "5,5");
        this.svg.appendChild(loadLine);
        
        // Draw load arrows
        for (let i = 0; i <= numArrows; i++) {
            const x = this.toSVGX(i * arrowSpacing);
            this.drawLoadArrow(x, arrowStartY, arrowLength);
        }
        
        // Load label (clickable) - position at top
        const midX = this.toSVGX(length / 2);
        const label = `${this.state.udl.total.toFixed(2)} kN/m`;
        
        // Background box for label
        const labelBg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        labelBg.setAttribute("x", midX - 50);
        labelBg.setAttribute("y", arrowStartY - 25);
        labelBg.setAttribute("width", 100);
        labelBg.setAttribute("height", 20);
        labelBg.setAttribute("fill", "white");
        labelBg.setAttribute("stroke", "#ef4444");
        labelBg.setAttribute("stroke-width", "1");
        labelBg.setAttribute("rx", "3");
        this.svg.appendChild(labelBg);
        
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", midX);
        text.setAttribute("y", arrowStartY - 11);
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("fill", "#ef4444");
        text.setAttribute("font-weight", "600");
        text.setAttribute("font-size", "13");
        text.style.cursor = "pointer";
        text.textContent = label;
        text.addEventListener('click', () => this.editUDL());
        
        // Hover effect
        text.addEventListener('mouseenter', () => {
            text.setAttribute("fill", "#F69321");
            labelBg.setAttribute("stroke", "#F69321");
        });
        text.addEventListener('mouseleave', () => {
            text.setAttribute("fill", "#ef4444");
            labelBg.setAttribute("stroke", "#ef4444");
        });
        
        this.svg.appendChild(text);
        
        // Component breakdown (small text below main label)
        const breakdown = `DL:${this.state.udl.dead_load} + LL:${this.state.udl.live_load} @ ${this.state.spacing}m`;
        const breakdownText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        breakdownText.setAttribute("x", midX);
        breakdownText.setAttribute("y", arrowStartY - 30);
        breakdownText.setAttribute("text-anchor", "middle");
        breakdownText.setAttribute("fill", "#666");
        breakdownText.setAttribute("font-size", "10");
        breakdownText.textContent = breakdown;
        this.svg.appendChild(breakdownText);
    }
    
    drawLoadArrow(x, y, length) {
        // Arrow line
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", x);
        line.setAttribute("y1", y);
        line.setAttribute("x2", x);
        line.setAttribute("y2", y + length);
        line.setAttribute("stroke", "#ef4444");
        line.setAttribute("stroke-width", "2");
        this.svg.appendChild(line);
        
        // Arrow head
        const arrowSize = 6;
        const arrow = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        const points = `${x},${y+length} ${x-arrowSize},${y+length-arrowSize} ${x+arrowSize},${y+length-arrowSize}`;
        arrow.setAttribute("points", points);
        arrow.setAttribute("fill", "#ef4444");
        this.svg.appendChild(arrow);
    }
    
    drawPointLoad(pl, index, beamY) {
        const x = this.toSVGX(pl.position);
        const arrowLength = 50;
        
        // Make it draggable
        const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
        group.style.cursor = "move";
        group.dataset.index = index;
        
        // Arrow
        this.drawLoadArrow(x, beamY - arrowLength - 10, arrowLength);
        
        // Magnitude label (clickable)
        const magText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        magText.setAttribute("x", x);
        magText.setAttribute("y", beamY - arrowLength - 20);
        magText.setAttribute("text-anchor", "middle");
        magText.setAttribute("fill", "#8B6F47");
        magText.setAttribute("font-weight", "600");
        magText.setAttribute("font-size", "14");
        magText.style.cursor = "pointer";
        magText.textContent = `${pl.magnitude.toFixed(1)} kN`;
        magText.addEventListener('click', (e) => {
            e.stopPropagation();
            this.editPointLoadMagnitude(index);
        });
        this.svg.appendChild(magText);
        
        // Position label (clickable)
        const posText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        posText.setAttribute("x", x);
        posText.setAttribute("y", beamY + 25);
        posText.setAttribute("text-anchor", "middle");
        posText.setAttribute("fill", "#666");
        posText.setAttribute("font-size", "12");
        posText.style.cursor = "pointer";
        posText.textContent = `${pl.position.toFixed(2)}m`;
        posText.addEventListener('click', (e) => {
            e.stopPropagation();
            this.editPointLoadPosition(index);
        });
        this.svg.appendChild(posText);
        
        // Delete button
        const deleteBtn = document.createElementNS("http://www.w3.org/2000/svg", "text");
        deleteBtn.setAttribute("x", x + 20);
        deleteBtn.setAttribute("y", beamY - arrowLength - 15);
        deleteBtn.setAttribute("fill", "#ef4444");
        deleteBtn.setAttribute("font-size", "16");
        deleteBtn.setAttribute("font-weight", "bold");
        deleteBtn.style.cursor = "pointer";
        deleteBtn.textContent = "×";
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.deletePointLoad(index);
        });
        this.svg.appendChild(deleteBtn);
        
        // TODO: Add drag functionality
    }
    
    drawToolbar() {
        // Check if toolbar already exists, remove it
        const existingToolbar = this.container.querySelector('.beam-toolbar');
        if (existingToolbar) {
            existingToolbar.remove();
        }
        
        // Toolbar at top of SVG
        const toolbar = document.createElement('div');
        toolbar.className = 'beam-toolbar';
        toolbar.style.cssText = `
            display: flex;
            gap: 1rem;
            padding: 1rem;
            background: white;
            border-bottom: 1px solid #e5e7eb;
            margin-bottom: 1rem;
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
                      id="spacing-label-${Date.now()}">
                    ${(this.state.spacing * 1000).toFixed(0)}mm crs
                </span>
            `;
            toolbar.appendChild(spacingLabel);
            
            // Add click handler to spacing label
            setTimeout(() => {
                const label = spacingLabel.querySelector('span');
                if (label) {
                    label.onclick = () => this.editSpacing();
                }
            }, 0);
        }
        
        this.container.insertBefore(toolbar, this.svg);
    }
    
    // ========================================================================
    // EDIT HANDLERS - Open inline editors
    // ========================================================================
    
    editSpan() {
        const currentSpan = this.getTotalLength();
        const newSpan = prompt(`Enter span (meters):`, currentSpan.toFixed(2));
        
        if (newSpan && !isNaN(newSpan)) {
            const value = parseFloat(newSpan);
            
            if (value < 0.5 || value > 20.0) {
                alert("⚠ Span must be between 0.5m and 20m");
                return;
            }
            
            // Update rightmost support position
            this.state.supports[this.state.supports.length - 1].position = value;
            this.draw();
        }
    }
    
    editSpacing() {
        const currentSpacing = (this.state.spacing * 1000).toFixed(0);
        const newSpacing = prompt(`Enter joist spacing (mm):`, currentSpacing);
        
        if (newSpacing && !isNaN(newSpacing)) {
            const value = parseFloat(newSpacing) / 1000; // Convert to meters
            
            if (value < 0.3 || value > 1.2) {
                alert("⚠ Spacing must be between 300mm and 1200mm");
                return;
            }
            
            this.state.spacing = value;
            this.calculateUDL();
            this.draw();
        }
    }
    
    editUDL() {
        // Show popup with dead/live load inputs
        const deadLoad = prompt(`Dead load (kPa):`, this.state.udl.dead_load);
        if (deadLoad === null) return;
        
        const liveLoad = prompt(`Live load (kPa):`, this.state.udl.live_load);
        if (liveLoad === null) return;
        
        this.state.udl.dead_load = parseFloat(deadLoad);
        this.state.udl.live_load = parseFloat(liveLoad);
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
        const newPos = prompt(`Point load position (m from left):`, pl.position.toFixed(2));
        
        if (newPos && !isNaN(newPos)) {
            const value = parseFloat(newPos);
            const maxPos = this.getTotalLength();
            
            if (value < 0 || value > maxPos) {
                alert(`⚠ Position must be between 0 and ${maxPos.toFixed(2)}m`);
                return;
            }
            
            pl.position = value;
            this.draw();
        }
    }
    
    addPointLoad() {
        const totalLength = this.getTotalLength();
        const position = totalLength / 2; // Default to midspan
        
        this.state.point_loads.push({
            magnitude: 10.0,
            position: position
        });
        
        this.draw();
    }
    
    deletePointLoad(index) {
        if (confirm('Remove this point load?')) {
            this.state.point_loads.splice(index, 1);
            this.draw();
        }
    }
    
    editSupport(support) {
        // TODO: Support type editor
        console.log('Edit support:', support);
    }
    
    // ========================================================================
    // FORM SYNCHRONIZATION
    // ========================================================================
    
    syncFormFields() {
        // Update hidden form fields with current state
        // Check if elements exist first (may not exist in demo mode)
        
        const spanInput = document.getElementById('span_input');
        if (spanInput) spanInput.value = this.getTotalLength();
        
        const spacingInput = document.getElementById('spacing_input');
        if (spacingInput) spacingInput.value = this.state.spacing;
        
        const deadLoadInput = document.getElementById('dead_load_input');
        if (deadLoadInput) deadLoadInput.value = this.state.udl.dead_load;
        
        const liveLoadInput = document.getElementById('live_load_input');
        if (liveLoadInput) liveLoadInput.value = this.state.udl.live_load;
        
        // Point loads
        this.state.point_loads.forEach((pl, i) => {
            if (i === 0) {
                const pl1Input = document.getElementById('pl1_input');
                const pl1PosInput = document.getElementById('pl1_pos_input');
                if (pl1Input) pl1Input.value = pl.magnitude;
                if (pl1PosInput) pl1PosInput.value = pl.position;
            } else if (i === 1) {
                const pl2Input = document.getElementById('pl2_input');
                const pl2PosInput = document.getElementById('pl2_pos_input');
                if (pl2Input) pl2Input.value = pl.magnitude;
                if (pl2PosInput) pl2PosInput.value = pl.position;
            }
            // TODO: Handle more than 2 point loads
        });
        
        // Supports (as JSON)
        const supportsInput = document.getElementById('supports_input');
        if (supportsInput) supportsInput.value = JSON.stringify(this.state.supports);
    }
    
    // ========================================================================
    // PUBLIC API
    // ========================================================================
    
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
