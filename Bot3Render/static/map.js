/**
 * Aerial Threat Tracking System - Frontend JavaScript
 * Handles map rendering, real-time updates, and UI interactions
 */

// Configuration
const CONFIG = {
    UPDATE_INTERVAL: 5000, // 5 seconds
    API_BASE: '',
    MAP_CENTER: [49.0, 31.0], // Center of Ukraine
    MAP_ZOOM: 6,
    MAX_THREATS_DISPLAY: 50
};

// State
let map = null;
let markers = [];
let currentThreats = [];
let updateTimer = null;

// Threat type colors and icons
const THREAT_CONFIG = {
    drone: {
        color: '#00d4ff',
        icon: '🛩️',
        label: 'DRONE'
    },
    missile: {
        color: '#ff3366',
        icon: '🚀',
        label: 'MISSILE'
    },
    aircraft: {
        color: '#ffb800',
        icon: '✈️',
        label: 'AIRCRAFT'
    }
};

/**
 * Initialize the application
 */
function init() {
    console.log('Initializing Aerial Threat Tracking System...');
    
    initMap();
    startUpdates();
    updateStatus('ONLINE', true);
    
    console.log('System initialized');
}

/**
 * Initialize Leaflet map
 */
function initMap() {
    // Create map
    map = L.map('map', {
        center: CONFIG.MAP_CENTER,
        zoom: CONFIG.MAP_ZOOM,
        zoomControl: true
    });

    // Add light tile layer (CartoDB Positron - light, readable)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    console.log('Map initialized');
}

/**
 * Start automatic updates
 */
function startUpdates() {
    // Initial update
    fetchThreats();
    
    // Set up periodic updates
    updateTimer = setInterval(fetchThreats, CONFIG.UPDATE_INTERVAL);
    
    console.log(`Auto-update started (every ${CONFIG.UPDATE_INTERVAL / 1000}s)`);
}

/**
 * Fetch threats from API
 */
async function fetchThreats() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/threats?limit=100`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            currentThreats = data.threats;
            updateMap(currentThreats);
            updateFeed(currentThreats);
            updateStatistics(currentThreats);
            updateLastUpdateTime();
            updateStatus('ONLINE', true);
        } else {
            console.error('API returned error:', data.error);
            updateStatus('ERROR', false);
        }
    } catch (error) {
        console.error('Failed to fetch threats:', error);
        updateStatus('OFFLINE', false);
    }
}

/**
 * Update map markers
 */
function updateMap(threats) {
    // Clear existing markers
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];

    // Add new markers
    threats.forEach(threat => {
        if (threat.coordinates && Array.isArray(threat.coordinates)) {
            const marker = createMarker(threat);
            if (marker) {
                markers.push(marker);
                marker.addTo(map);
            }
        }
    });

    console.log(`Map updated with ${markers.length} markers`);
}

/**
 * Create a marker for a threat
 */
function createMarker(threat) {
    const coords = threat.coordinates;
    const type = threat.threat_type || 'unknown';
    const config = THREAT_CONFIG[type] || THREAT_CONFIG.drone;

    // Create custom icon
    const icon = L.divIcon({
        className: 'custom-marker',
        html: `
            <div style="
                background: ${config.color};
                width: 20px;
                height: 20px;
                border-radius: 50%;
                border: 3px solid rgba(0, 0, 0, 0.8);
                box-shadow: 0 0 20px ${config.color};
                animation: pulse-marker 2s ease-in-out infinite;
            "></div>
        `,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });

    // Create marker
    const marker = L.marker(coords, { icon: icon });

    // Create popup content
    const popupContent = `
        <div style="
            font-family: 'Rajdhani', sans-serif;
            min-width: 200px;
            padding: 8px;
        ">
            <div style="
                font-size: 14px;
                font-weight: 700;
                color: ${config.color};
                text-transform: uppercase;
                letter-spacing: 1.5px;
                margin-bottom: 8px;
            ">
                ${config.icon} ${config.label}
            </div>
            
            <div style="
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 4px;
            ">
                📍 ${threat.city || 'Unknown Location'}
            </div>
            
            ${threat.direction ? `
                <div style="
                    font-size: 12px;
                    margin-bottom: 4px;
                    color: #8a95a3;
                ">
                    Direction: ${threat.direction.toUpperCase()}
                </div>
            ` : ''}
            
            <div style="
                font-size: 11px;
                color: #5a6774;
                margin-top: 8px;
                padding-top: 8px;
                border-top: 1px solid #2a3542;
            ">
                ${threat.datetime || formatTimestamp(threat.timestamp)}
            </div>
            
            ${threat.source_channel ? `
                <div style="
                    font-size: 10px;
                    color: #5a6774;
                    font-family: 'JetBrains Mono', monospace;
                    margin-top: 4px;
                ">
                    Source: ${threat.source_channel}
                </div>
            ` : ''}
        </div>
    `;

    marker.bindPopup(popupContent);

    return marker;
}

/**
 * Update threat feed panel
 */
function updateFeed(threats) {
    const feedContainer = document.getElementById('threatList');
    
    if (!threats || threats.length === 0) {
        feedContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📡</div>
                <div>No threats detected</div>
                <div style="font-size: 11px; margin-top: 8px;">System monitoring active</div>
            </div>
        `;
        return;
    }

    // Take only the most recent threats
    const displayThreats = threats.slice(0, CONFIG.MAX_THREATS_DISPLAY);

    feedContainer.innerHTML = displayThreats.map(threat => {
        const type = threat.threat_type || 'unknown';
        const config = THREAT_CONFIG[type] || THREAT_CONFIG.drone;
        
        return `
            <div class="threat-item ${type}">
                <div class="threat-header">
                    <div class="threat-type ${type}">
                        ${config.icon} ${config.label}
                    </div>
                    <div class="threat-time">
                        ${formatTimeAgo(threat.timestamp)}
                    </div>
                </div>
                
                <div class="threat-location">
                    📍 ${threat.city || 'Unknown Location'}
                </div>
                
                <div class="threat-details">
                    ${threat.direction ? `Direction: ${threat.direction.toUpperCase()}` : ''}
                    ${threat.is_movement ? ' • Movement detected' : ''}
                </div>
                
                ${threat.source_channel ? `
                    <div class="threat-source">
                        Source: ${threat.source_channel}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

/**
 * Update statistics in header
 */
function updateStatistics(threats) {
    const total = threats.length;
    
    // Count active threats (last hour)
    const oneHourAgo = Date.now() / 1000 - 3600;
    const active = threats.filter(t => t.timestamp >= oneHourAgo).length;
    
    document.getElementById('totalThreats').textContent = total;
    document.getElementById('activeThreats').textContent = active;
}

/**
 * Update status indicator
 */
function updateStatus(status, isOnline) {
    const statusText = document.getElementById('statusText');
    const statusDot = document.getElementById('statusDot');
    
    statusText.textContent = status;
    
    if (isOnline) {
        statusDot.style.background = '#00ff88';
        statusDot.style.boxShadow = '0 0 10px #00ff88';
    } else {
        statusDot.style.background = '#ff3366';
        statusDot.style.boxShadow = '0 0 10px #ff3366';
    }
}

/**
 * Update last update time
 */
function updateLastUpdateTime() {
    const now = new Date();
    const timeString = now.toTimeString().split(' ')[0];
    document.getElementById('lastUpdate').textContent = `LAST UPDATE: ${timeString}`;
}

/**
 * Format timestamp as time ago
 */
function formatTimeAgo(timestamp) {
    if (!timestamp) return 'Unknown';
    
    const now = Date.now() / 1000;
    const diff = now - timestamp;
    
    if (diff < 60) {
        return 'Just now';
    } else if (diff < 3600) {
        const mins = Math.floor(diff / 60);
        return `${mins}m ago`;
    } else if (diff < 86400) {
        const hours = Math.floor(diff / 3600);
        return `${hours}h ago`;
    } else {
        const days = Math.floor(diff / 86400);
        return `${days}d ago`;
    }
}

/**
 * Format timestamp as readable date
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Unknown';
    
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Add pulse animation style
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse-marker {
        0%, 100% { 
            transform: scale(1);
            opacity: 1;
        }
        50% { 
            transform: scale(1.2);
            opacity: 0.8;
        }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (updateTimer) {
        clearInterval(updateTimer);
    }
});
