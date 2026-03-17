"""
Database module for storing and retrieving threat reports
Uses in-memory storage with thread-safe operations
"""
import json
import time
from datetime import datetime
from threading import Lock
from typing import List, Dict, Optional

# Ukrainian cities with coordinates [latitude, longitude]
CITY_COORDINATES = {
    "Kyiv": [50.4501, 30.5234],
    "Kharkiv": [49.9935, 36.2304],
    "Odesa": [46.4825, 30.7233],
    "Dnipro": [48.4647, 35.0462],
    "Lviv": [49.8397, 24.0297],
    "Zaporizhzhia": [47.8388, 35.1396],
    "Kryvyi Rih": [47.9088, 33.3426],
    "Mykolaiv": [46.9750, 31.9946],
    "Mariupol": [47.0956, 37.5431],
    "Vinnytsia": [49.2331, 28.4682],
    "Poltava": [49.5883, 34.5514],
    "Chernihiv": [51.4982, 31.2893],
    "Cherkasy": [49.4285, 32.0617],
    "Sumy": [50.9077, 34.7981],
    "Zhytomyr": [50.2547, 28.6587],
    "Khmelnytskyi": [49.4229, 26.9871],
    "Chernivtsi": [48.2921, 25.9358],
    "Rivne": [50.6199, 26.2516],
    "Ivano-Frankivsk": [48.9226, 24.7111],
    "Ternopil": [49.5535, 25.5948],
    "Lutsk": [50.7472, 25.3254],
    "Uzhhorod": [48.6208, 22.2879],
    "Kremenchuk": [49.0676, 33.4161],
    "Bila Tserkva": [49.7990, 30.1174],
    "Kropyvnytskyi": [48.5079, 32.2623],
    "Simferopol": [44.9521, 34.1024],
    "Donetsk": [48.0159, 37.8028],
    "Luhansk": [48.5740, 39.3078],
    "Sevastopol": [44.6167, 33.5254],
    "Melitopol": [46.8483, 35.3656],
    "Kherson": [46.6354, 32.6169],
}

class ThreatDatabase:
    """Thread-safe in-memory database for aerial threats"""
    
    def __init__(self):
        self.threats = []
        self.lock = Lock()
        self.seen_hashes = set()  # For duplicate detection
        self.max_threats = 200  # Keep last 200 threats
        
    def add_threat(self, threat_data: Dict) -> bool:
        """
        Add a new threat to the database
        Returns True if added, False if duplicate
        """
        with self.lock:
            # Create hash for duplicate detection
            threat_hash = self._create_hash(threat_data)
            
            if threat_hash in self.seen_hashes:
                return False
            
            # Add timestamp if not present
            if 'timestamp' not in threat_data:
                threat_data['timestamp'] = time.time()
            
            # Add ISO format datetime for frontend
            threat_data['datetime'] = datetime.fromtimestamp(
                threat_data['timestamp']
            ).strftime('%Y-%m-%d %H:%M:%S')
            
            # Add coordinates if city is known
            city = threat_data.get('city', '')
            if city in CITY_COORDINATES:
                threat_data['coordinates'] = CITY_COORDINATES[city]
            
            self.threats.insert(0, threat_data)  # Add to front
            self.seen_hashes.add(threat_hash)
            
            # Trim old threats
            if len(self.threats) > self.max_threats:
                removed = self.threats[self.max_threats:]
                self.threats = self.threats[:self.max_threats]
                
                # Remove old hashes
                for old_threat in removed:
                    old_hash = self._create_hash(old_threat)
                    self.seen_hashes.discard(old_hash)
            
            return True
    
    def get_threats(self, limit: int = 100) -> List[Dict]:
        """Get the most recent threats"""
        with self.lock:
            return self.threats[:limit]
    
    def get_active_threats(self, max_age_seconds: int = 3600) -> List[Dict]:
        """Get threats from the last N seconds (default 1 hour)"""
        current_time = time.time()
        with self.lock:
            return [
                t for t in self.threats 
                if current_time - t.get('timestamp', 0) <= max_age_seconds
            ]
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        with self.lock:
            threat_types = {}
            for threat in self.threats:
                t_type = threat.get('threat_type', 'unknown')
                threat_types[t_type] = threat_types.get(t_type, 0) + 1
            
            return {
                'total_threats': len(self.threats),
                'active_threats': len(self.get_active_threats()),
                'threat_types': threat_types,
                'cities_tracked': len(CITY_COORDINATES)
            }
    
    def _create_hash(self, threat_data: Dict) -> str:
        """Create a hash for duplicate detection"""
        key = f"{threat_data.get('city', '')}_{threat_data.get('threat_type', '')}_{threat_data.get('raw_message', '')[:50]}"
        return key.lower()
    
    def clear_old_threats(self, max_age_seconds: int = 7200):
        """Clear threats older than specified seconds (default 2 hours)"""
        current_time = time.time()
        with self.lock:
            initial_count = len(self.threats)
            self.threats = [
                t for t in self.threats 
                if current_time - t.get('timestamp', 0) <= max_age_seconds
            ]
            removed = initial_count - len(self.threats)
            
            # Rebuild seen_hashes from remaining threats
            self.seen_hashes = {self._create_hash(t) for t in self.threats}
            
            return removed

# Global database instance
db = ThreatDatabase()

def get_city_coordinates(city_name: str) -> Optional[List[float]]:
    """Get coordinates for a city"""
    return CITY_COORDINATES.get(city_name)

def get_all_cities() -> Dict[str, List[float]]:
    """Get all cities with coordinates"""
    return CITY_COORDINATES.copy()
