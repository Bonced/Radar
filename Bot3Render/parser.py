"""
Parser module for extracting threat information from text messages
Handles Ukrainian and English messages about aerial threats
"""
import re
from typing import Dict, Optional
from database import CITY_COORDINATES

# Threat type keywords
THREAT_KEYWORDS = {
    'drone': [
        'drone', 'дрон', 'shahed', 'шахед', 'бпла', 'безпілотник', 'uav',
        'geran', 'герань', 'орлан', 'orlan'
    ],
    'missile': [
        'missile', 'ракета', 'rocket', 'kalibr', 'калібр', 'iskander', 
        'іскандер', 'kinzhal', 'кинжал', 'кінжал', 's-300', 'с-300'
    ],
    'aircraft': [
        'aircraft', 'літак', 'plane', 'jet', 'bomber', 'бомбардувальник',
        'fighter', 'винищувач', 'helicopter', 'гелікоптер', 'вертоліт'
    ]
}

# Direction keywords
DIRECTION_KEYWORDS = {
    'north': ['north', 'північ', 'північ', 'північний', 'пн'],
    'south': ['south', 'південь', 'південний', 'пд'],
    'east': ['east', 'схід', 'східний', 'сх'],
    'west': ['west', 'захід', 'західний', 'зх'],
    'northeast': ['northeast', 'північний схід', 'пн-сх'],
    'northwest': ['northwest', 'північний захід', 'пн-зх'],
    'southeast': ['southeast', 'південний схід', 'пд-сх'],
    'southwest': ['southwest', 'південний захід', 'пд-зх']
}

# Action keywords that indicate movement
MOVEMENT_KEYWORDS = [
    'heading', 'moving', 'detected', 'spotted', 'approaching', 'flying',
    'прямує', 'рухається', 'виявлено', 'помічено', 'наближається', 'летить',
    'курс', 'напрям', 'direction', 'towards', 'до', 'в напрямку'
]


class ThreatParser:
    """Parse threat messages and extract structured information"""
    
    def __init__(self):
        self.cities = list(CITY_COORDINATES.keys())
        # Create case-insensitive city patterns
        self.city_pattern = self._build_city_pattern()
    
    def _build_city_pattern(self) -> re.Pattern:
        """Build regex pattern for city detection"""
        # Sort cities by length (longest first) to match longer names first
        sorted_cities = sorted(self.cities, key=len, reverse=True)
        pattern = '|'.join(re.escape(city) for city in sorted_cities)
        return re.compile(f'\\b({pattern})\\b', re.IGNORECASE)
    
    def parse(self, message: str, source_channel: str = None) -> Optional[Dict]:
        """
        Parse a threat message and extract information
        
        Returns:
            Dictionary with threat information or None if parsing fails
        """
        if not message or len(message.strip()) < 5:
            return None
        
        message_lower = message.lower()
        
        # Extract threat type
        threat_type = self._extract_threat_type(message_lower)
        if not threat_type:
            return None  # Not a threat message
        
        # Extract city
        city = self._extract_city(message)
        
        # Extract direction
        direction = self._extract_direction(message_lower)
        
        # Check if it's a movement report
        has_movement = any(keyword in message_lower for keyword in MOVEMENT_KEYWORDS)
        
        # Build result
        result = {
            'threat_type': threat_type,
            'city': city,
            'direction': direction,
            'raw_message': message,
            'source_channel': source_channel,
            'is_movement': has_movement
        }
        
        return result
    
    def _extract_threat_type(self, message_lower: str) -> Optional[str]:
        """Extract threat type from message"""
        for threat_type, keywords in THREAT_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                return threat_type
        return None
    
    def _extract_city(self, message: str) -> Optional[str]:
        """Extract city name from message"""
        match = self.city_pattern.search(message)
        if match:
            # Find the exact city name from our database (case-sensitive)
            matched_text = match.group(1)
            for city in self.cities:
                if city.lower() == matched_text.lower():
                    return city
        return None
    
    def _extract_direction(self, message_lower: str) -> Optional[str]:
        """Extract direction from message"""
        for direction, keywords in DIRECTION_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                return direction
        return None


# Global parser instance
parser = ThreatParser()


def parse_threat_message(message: str, source_channel: str = None) -> Optional[Dict]:
    """
    Convenience function to parse a threat message
    
    Args:
        message: The text message to parse
        source_channel: Optional source channel name
    
    Returns:
        Parsed threat data or None
    """
    return parser.parse(message, source_channel)


# Test function
def test_parser():
    """Test the parser with sample messages"""
    test_messages = [
        "Drone heading to Kharkiv",
        "Missile detected near Poltava",
        "Shahed moving west towards Lviv",
        "Дрон прямує до Києва",
        "Ракета виявлена біля Одеси",
        "Aircraft spotted over Dnipro heading north",
        "БПЛА в напрямку Харкова",
    ]
    
    print("Testing Parser:")
    print("=" * 60)
    for msg in test_messages:
        result = parse_threat_message(msg, "test_channel")
        if result:
            print(f"\n✓ '{msg}'")
            print(f"  Type: {result['threat_type']}")
            print(f"  City: {result['city']}")
            print(f"  Direction: {result['direction']}")
        else:
            print(f"\n✗ '{msg}' - Not parsed")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_parser()
