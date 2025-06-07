#!/usr/bin/env python3
"""
PGN Pattern Filter
Filters PGN database games that match specified move patterns.
Handles PGN format with rows of up to 10 plies and no space after move numbers.
"""

import re
import argparse
import sys
from typing import List, Dict, Optional

class PGNGame:
    def __init__(self):
        self.headers = {}
        self.moves = []
        self.raw_moves = ""
    
    def add_header(self, key: str, value: str):
        self.headers[key] = value
    
    def set_moves(self, moves_text: str):
        self.raw_moves = moves_text
        self.moves = self.parse_moves(moves_text)
    
    def parse_moves(self, moves_text: str) -> List[str]:
        """Parse moves from PGN format, handling no space after move numbers."""
        # Remove result indicators
        moves_text = re.sub(r'\s*(1-0|0-1|1/2-1/2|\*)\s*$', '', moves_text)
        
        # Split into tokens
        tokens = moves_text.split()
        moves = []
        
        for token in tokens:
            # Skip move numbers (e.g., "1.", "2.", "10.", etc.)
            if re.match(r'^\d+\.+$', token):
                continue
            
            # Handle move numbers attached to moves (e.g., "1.e4", "2.Nf3")
            match = re.match(r'^\d+\.+(.+)$', token)
            if match:
                moves.append(match.group(1))
            else:
                # Regular move
                moves.append(token)
        
        return moves
    
    def matches_pattern(self, pattern: List[str], start_move: int = 1) -> bool:
        """Check if the game matches the given pattern starting from start_move."""
        if start_move < 1:
            start_move = 1
        
        # Convert to 0-based index
        start_idx = (start_move - 1) * 2
        
        if start_idx >= len(self.moves):
            return False
        
        # Check if we have enough moves to match the pattern
        if start_idx + len(pattern) > len(self.moves):
            return False
        
        # Compare moves
        for i, pattern_move in enumerate(pattern):
            game_move = self.moves[start_idx + i]
            if not self.move_matches(game_move, pattern_move):
                return False
        
        return True
    
    def move_matches(self, game_move: str, pattern_move: str) -> bool:
        """Check if a game move matches a pattern move (supports wildcards)."""
        # Remove check/checkmate indicators for comparison
        game_move_clean = re.sub(r'[+#]$', '', game_move)
        pattern_move_clean = re.sub(r'[+#]$', '', pattern_move)
        
        # Exact match
        if game_move_clean == pattern_move_clean:
            return True
        
        # Wildcard support
        if pattern_move_clean == '*':
            return True
        
        # Regex pattern support (if pattern starts and ends with /)
        if pattern_move_clean.startswith('/') and pattern_move_clean.endswith('/'):
            regex = pattern_move_clean[1:-1]
            return bool(re.match(regex, game_move_clean))
        
        return False
    
    def to_pgn(self) -> str:
        """Convert back to PGN format."""
        result = []
        
        # Add headers
        for key, value in self.headers.items():
            result.append(f'[{key} "{value}"]')
        
        if self.headers:
            result.append('')  # Empty line after headers
        
        # Add moves
        result.append(self.raw_moves)
        result.append('')  # Empty line after game
        
        return '\n'.join(result)

class PGNFilter:
    def __init__(self):
        self.games = []
    
    def load_pgn(self, filename: str):
        """Load PGN file and parse games."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding if utf-8 fails
            with open(filename, 'r', encoding='latin-1') as f:
                content = f.read()
        
        self.games = self.parse_pgn_content(content)
        print(f"Loaded {len(self.games)} games from {filename}")
    
    def parse_pgn_content(self, content: str) -> List[PGNGame]:
        """Parse PGN content into game objects."""
        games = []
        lines = content.strip().split('\n')
        
        current_game = None
        moves_section = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                if current_game and moves_section:
                    # End of game
                    moves_text = ' '.join(moves_section)
                    current_game.set_moves(moves_text)
                    games.append(current_game)
                    current_game = None
                    moves_section = []
                continue
            
            # Header line
            if line.startswith('[') and line.endswith(']'):
                if current_game is None:
                    current_game = PGNGame()
                
                # Parse header
                match = re.match(r'\[(\w+)\s+"([^"]*)"\]', line)
                if match:
                    key, value = match.groups()
                    current_game.add_header(key, value)
            else:
                # Moves line
                moves_section.append(line)
        
        # Handle last game if file doesn't end with empty line
        if current_game and moves_section:
            moves_text = ' '.join(moves_section)
            current_game.set_moves(moves_text)
            games.append(current_game)
        
        return games
    
    def filter_games(self, pattern: List[str], start_move: int = 1) -> List[PGNGame]:
        """Filter games that match the pattern."""
        matching_games = []
        
        for game in self.games:
            if game.matches_pattern(pattern, start_move):
                matching_games.append(game)
        
        return matching_games
    
    def save_filtered_games(self, games: List[PGNGame], output_filename: str):
        """Save filtered games to a new PGN file."""
        with open(output_filename, 'w', encoding='utf-8') as f:
            for game in games:
                f.write(game.to_pgn())
        
        print(f"Saved {len(games)} matching games to {output_filename}")

def parse_pattern(pattern_str: str) -> List[str]:
    """Parse pattern string into list of moves."""
    # Handle different input formats
    moves = []
    
    # Split by spaces and clean up
    tokens = pattern_str.split()
    
    for token in tokens:
        # Skip move numbers
        if re.match(r'^\d+\.+$', token):
            continue
        
        # Handle move numbers attached to moves
        match = re.match(r'^\d+\.+(.+)$', token)
        if match:
            moves.append(match.group(1))
        else:
            moves.append(token)
    
    return moves

def main():
    parser = argparse.ArgumentParser(description='Filter PGN games by move patterns')
    parser.add_argument('input_file', help='Input PGN file')
    parser.add_argument('pattern', help='Move pattern (e.g., "1.e4 e5 2.Nf3" or "e4 e5 Nf3")')
    parser.add_argument('-o', '--output', help='Output PGN file (default: filtered_games.pgn)')
    parser.add_argument('-s', '--start-move', type=int, default=1, 
                       help='Starting move number to match pattern (default: 1)')
    parser.add_argument('--show-stats', action='store_true', 
                       help='Show statistics about matches')
    
    args = parser.parse_args()
    
    # Parse pattern
    pattern = parse_pattern(args.pattern)
    print(f"Looking for pattern: {' '.join(pattern)}")
    print(f"Starting from move: {args.start_move}")
    
    # Load and filter PGN
    pgn_filter = PGNFilter()
    pgn_filter.load_pgn(args.input_file)
    
    matching_games = pgn_filter.filter_games(pattern, args.start_move)
    
    print(f"Found {len(matching_games)} games matching the pattern")
    
    if args.show_stats and matching_games:
        print("\nSample matching games:")
        for i, game in enumerate(matching_games[:3]):  # Show first 3
            white = game.headers.get('White', 'Unknown')
            black = game.headers.get('Black', 'Unknown')
            result = game.headers.get('Result', '*')
            print(f"  {i+1}. {white} vs {black} ({result})")
            print(f"     Moves: {' '.join(game.moves[:10])}...")
    
    # Save results
    output_file = args.output or 'filtered_games.pgn'
    if matching_games:
        pgn_filter.save_filtered_games(matching_games, output_file)
    else:
        print("No matching games found.")

if __name__ == '__main__':
    main()