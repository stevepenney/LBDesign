/**
 * 3D Model Selector Drawer (Placeholder)
 * 
 * Simulates the 3D model interaction until actual model is ready
 * Provides buttons to select member types
 */

class ModelSelector {
    constructor() {
        this.drawer = null;
        this.memberTypes = {
            floor_joist: {
                name: "Floor Joist",
                description: "Horizontal members supporting floor loads",
                typical_spacing: 0.4,
                typical_dead_load: 0.5,
                typical_live_load: 1.5,
                id_prefix: "FJ"
            },
            rafter: {
                name: "Rafter",
                description: "Sloped roof members",
                typical_spacing: 0.6,
                typical_dead_load: 0.4,
                typical_live_load: 0.25,
                id_prefix: "R"
            },
            ridge_beam: {
                name: "Ridge Beam",
                description: "Horizontal beam at roof peak",
                typical_spacing: null,
                typical_dead_load: 0,
                typical_live_load: 0,
                id_prefix: "RB"
            },
            floor_beam: {
                name: "Floor Beam",
                description: "Primary floor support beam",
                typical_spacing: null,
                typical_dead_load: 0,
                typical_live_load: 0,
                id_prefix: "FB"
            }
        };
        
        this.createDrawer();
    }
    
    createDrawer() {
        // Create drawer overlay
        this.drawer = document.createElement('div');
        this.drawer.id = 'model-selector-drawer';
        this.drawer.style.cssText = `
            position: fixed;
            top: 0;
            right: -600px;
            width: 600px;
            height: 100vh;
            background: white;
            box-shadow: -4px 0 8px rgba(0,0,0,0.1);
            transition: right 0.3s ease;
            z-index: 1000;
            overflow-y: auto;
        `;
        
        this.drawer.innerHTML = `
            <div style="padding: 2rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                    <h2 style="margin: 0;">Select Member Type</h2>
                    <button onclick="modelSelector.close()" class="btn btn-secondary">Close</button>
                </div>
                
                <div style="background: #f9fafb; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; border: 2px dashed #d1d5db;">
                    <p style="text-align: center; color: #666; margin: 0;">
                        <strong>3D Model Placeholder</strong><br>
                        Interactive 3D house model will appear here<br>
                        <span style="font-size: 0.9rem;">For now, use the buttons below to select a member type</span>
                    </p>
                    <div style="margin-top: 1rem; padding: 3rem; background: white; border-radius: 4px; text-align: center;">
                        <svg width="200" height="200" style="margin: 0 auto;">
                            <!-- Simple house outline as placeholder -->
                            <rect x="50" y="100" width="100" height="80" fill="none" stroke="#8B6F47" stroke-width="2"/>
                            <polygon points="100,50 50,100 150,100" fill="none" stroke="#8B6F47" stroke-width="2"/>
                            <text x="100" y="140" text-anchor="middle" fill="#666" font-size="12">3D Model</text>
                            <text x="100" y="155" text-anchor="middle" fill="#666" font-size="12">Coming Soon</text>
                        </svg>
                    </div>
                </div>
                
                <h3 style="margin-bottom: 1rem;">Member Types:</h3>
                <div id="member-type-buttons" style="display: grid; gap: 1rem;">
                    <!-- Buttons populated by JavaScript -->
                </div>
            </div>
        `;
        
        document.body.appendChild(this.drawer);
        
        // Create overlay background
        this.overlay = document.createElement('div');
        this.overlay.id = 'model-selector-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0,0,0,0.3);
            display: none;
            z-index: 999;
        `;
        this.overlay.onclick = () => this.close();
        document.body.appendChild(this.overlay);
        
        // Populate member type buttons
        this.createMemberTypeButtons();
    }
    
    createMemberTypeButtons() {
        const container = document.getElementById('member-type-buttons');
        
        Object.keys(this.memberTypes).forEach(typeKey => {
            const member = this.memberTypes[typeKey];
            
            const button = document.createElement('button');
            button.className = 'member-type-card';
            button.style.cssText = `
                padding: 1.5rem;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                background: white;
                text-align: left;
                cursor: pointer;
                transition: all 0.2s;
            `;
            
            button.innerHTML = `
                <h4 style="margin: 0 0 0.5rem 0; color: #1a1a1a;">${member.name}</h4>
                <p style="margin: 0; color: #666; font-size: 0.9rem;">${member.description}</p>
                ${member.typical_spacing ? `
                    <p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #8B6F47;">
                        Typical: ${(member.typical_spacing * 1000).toFixed(0)}mm spacing
                    </p>
                ` : ''}
            `;
            
            // Hover effect
            button.addEventListener('mouseenter', () => {
                button.style.borderColor = '#F69321';
                button.style.backgroundColor = '#fffbf0';
                button.style.transform = 'translateY(-2px)';
                button.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
            });
            
            button.addEventListener('mouseleave', () => {
                button.style.borderColor = '#e5e7eb';
                button.style.backgroundColor = 'white';
                button.style.transform = 'translateY(0)';
                button.style.boxShadow = 'none';
            });
            
            button.onclick = () => this.selectMemberType(typeKey);
            
            container.appendChild(button);
        });
    }
    
    open() {
        // Slide drawer in
        this.drawer.style.right = '0';
        this.overlay.style.display = 'block';
    }
    
    close() {
        // Slide drawer out
        this.drawer.style.right = '-600px';
        this.overlay.style.display = 'none';
    }
    
    selectMemberType(typeKey) {
        const member = this.memberTypes[typeKey];
        
        // Show confirmation popup
        this.showConfirmationPopup(typeKey, member);
    }
    
    showConfirmationPopup(typeKey, member) {
        // Create modal
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.2);
            z-index: 1001;
            max-width: 500px;
            width: 90%;
        `;
        
        modal.innerHTML = `
            <h3 style="margin: 0 0 1rem 0; color: #1a1a1a;">Design ${member.name}?</h3>
            <p style="color: #666; margin-bottom: 1.5rem;">${member.description}</p>
            
            ${member.typical_spacing ? `
                <div style="background: #f9fafb; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem;">
                    <p style="margin: 0; font-size: 0.9rem;"><strong>Typical values:</strong></p>
                    <ul style="margin: 0.5rem 0 0 1.5rem; font-size: 0.9rem; color: #666;">
                        <li>Spacing: ${(member.typical_spacing * 1000).toFixed(0)}mm</li>
                        <li>Dead load: ${member.typical_dead_load} kPa</li>
                        <li>Live load: ${member.typical_live_load} kPa</li>
                    </ul>
                </div>
            ` : ''}
            
            <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                <button onclick="this.parentElement.parentElement.parentElement.removeChild(this.parentElement.parentElement)" 
                        class="btn btn-secondary">Cancel</button>
                <button onclick="modelSelector.confirmSelection('${typeKey}')" 
                        class="btn btn-primary">Yes, Design This</button>
            </div>
        `;
        
        // Add darker overlay
        const confirmOverlay = document.createElement('div');
        confirmOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
        `;
        confirmOverlay.onclick = () => {
            document.body.removeChild(confirmOverlay);
            document.body.removeChild(modal);
        };
        
        document.body.appendChild(confirmOverlay);
        document.body.appendChild(modal);
        
        // Store reference for confirmation
        this.currentConfirmOverlay = confirmOverlay;
        this.currentConfirmModal = modal;
    }
    
    confirmSelection(typeKey) {
        const member = this.memberTypes[typeKey];
        
        // Close confirmation popup
        if (this.currentConfirmOverlay) {
            document.body.removeChild(this.currentConfirmOverlay);
            document.body.removeChild(this.currentConfirmModal);
        }
        
        // Close 3D model drawer
        this.close();
        
        // Get next available ID
        const nextId = this.getNextId(member.id_prefix);
        
        // Initialize beam canvas with member type data
        const canvasContainer = document.getElementById('beam-canvas-container');
        canvasContainer.style.display = 'block';
        
        // Create or update beam canvas
        if (window.beamCanvas) {
            window.beamCanvas.setState({
                name: nextId,
                member_type: typeKey,
                spacing: member.typical_spacing || 0.4,
                udl: {
                    dead_load: member.typical_dead_load || 0,
                    live_load: member.typical_live_load || 0,
                    total: 0
                }
            });
        } else {
            window.beamCanvas = new BeamCanvas('beam-canvas-container', {
                name: nextId,
                member_type: typeKey,
                spacing: member.typical_spacing || 0.4,
                udl: {
                    dead_load: member.typical_dead_load || 0,
                    live_load: member.typical_live_load || 0,
                    total: 0
                }
            });
        }
        
        // Update beam name field
        document.getElementById('beam_name').value = nextId;
        
        // Show design section
        document.getElementById('design-section').style.display = 'block';
    }
    
    getNextId(prefix) {
        // TODO: Query existing beams to get next number
        // For now, just return prefix + 1
        return `${prefix}-1`;
    }
}

// Initialize when DOM is ready
let modelSelector;
document.addEventListener('DOMContentLoaded', () => {
    modelSelector = new ModelSelector();
});
