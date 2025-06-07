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
    
    def analyze_branching_point(self, games: List[PGNGame], pattern: List[str], start_move: int = 1) -> Dict:
        """Analyze the first branching point after the pattern and calculate performance."""
        if not games:
            return {}
        
        pattern_length = len(pattern)
        start_idx = (start_move - 1) * 2
        branching_ply = start_idx + pattern_length
        
        # Collect all possible moves at the branching point
        move_stats = {}
        
        for game in games:
            if branching_ply >= len(game.moves):
                continue  # Game too short
            
            next_move = game.moves[branching_ply]
            # Clean move notation
            clean_move = re.sub(r'[+#]$', '', next_move)
            
            if clean_move not in move_stats:
                move_stats[clean_move] = {
                    'count': 0,
                    'points': 0.0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0
                }
            
            move_stats[clean_move]['count'] += 1
            
            # Calculate points based on result and whose turn it is
            result = game.headers.get('Result', '*')
            is_white_move = (branching_ply % 2 == 0)  # Even index = white's turn
            
            if result == '1-0':  # White wins
                points = 1.0 if is_white_move else 0.0
                if is_white_move:
                    move_stats[clean_move]['wins'] += 1
                else:
                    move_stats[clean_move]['losses'] += 1
            elif result == '0-1':  # Black wins
                points = 0.0 if is_white_move else 1.0
                if is_white_move:
                    move_stats[clean_move]['losses'] += 1
                else:
                    move_stats[clean_move]['wins'] += 1
            elif result == '1/2-1/2':  # Draw
                points = 0.5
                move_stats[clean_move]['draws'] += 1
            else:  # Unfinished game or other result
                continue  # Skip unfinished games for scoring
            
            move_stats[clean_move]['points'] += points
        
        # Filter out moves with only one occurrence (no real branching)
        branching_moves = {move: stats for move, stats in move_stats.items() 
                          if stats['count'] > 1}
        
        # Calculate percentages and sort by frequency
        for move, stats in branching_moves.items():
            if stats['count'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['count']) * 100
                stats['draw_rate'] = (stats['draws'] / stats['count']) * 100
                stats['loss_rate'] = (stats['losses'] / stats['count']) * 100
                stats['score_percentage'] = (stats['points'] / stats['count']) * 100
        
        return {
            'ply_number': branching_ply + 1,  # Convert to 1-based
            'move_number': (branching_ply // 2) + 1,
            'is_white_move': branching_ply % 2 == 0,
            'total_games_analyzed': len([g for g in games if branching_ply < len(g.moves)]),
            'branching_moves': dict(sorted(branching_moves.items(), 
                                         key=lambda x: x[1]['count'], reverse=True))
        }
    
    def print_branching_analysis(self, analysis: Dict):
        """Print detailed branching point analysis."""
        if not analysis or not analysis['branching_moves']:
            print("No branching point found (all games follow the same continuation).")
            return
        
        ply = analysis['ply_number']
        move_num = analysis['move_number']
        player = "White" if analysis['is_white_move'] else "Black"
        total_games = analysis['total_games_analyzed']
        
        print(f"\n=== BRANCHING POINT ANALYSIS ===")
        print(f"First branching occurs at ply {ply} (move {move_num} for {player})")
        print(f"Total games analyzed: {total_games}")
        print(f"\nPossible moves and their performance:")
        print(f"{'Move':<12} {'Count':<6} {'Score%':<8} {'W-D-L':<12} {'Points':<8}")
        print("-" * 55)
        
        for move, stats in analysis['branching_moves'].items():
            count = stats['count']
            score_pct = stats['score_percentage']
            wdl = f"{stats['wins']}-{stats['draws']}-{stats['losses']}"
            points = stats['points']
            
            print(f"{move:<12} {count:<6} {score_pct:<7.1f}% {wdl:<12} {points:<7.1f}")
        
        # Find best and worst performing moves
        if len(analysis['branching_moves']) > 1:
            best_move = max(analysis['branching_moves'].items(), 
                           key=lambda x: x[1]['score_percentage'])
            worst_move = min(analysis['branching_moves'].items(), 
                            key=lambda x: x[1]['score_percentage'])
            
            print(f"\nBest performing move: {best_move[0]} ({best_move[1]['score_percentage']:.1f}%)")
            print(f"Worst performing move: {worst_move[0]} ({worst_move[1]['score_percentage']:.1f}%)")
            
            # Most popular move
            most_popular = max(analysis['branching_moves'].items(), 
                             key=lambda x: x[1]['count'])
            print(f"Most popular move: {most_popular[0]} ({most_popular[1]['count']} games)")
    
    def find_first_branching_point(self, games: List[PGNGame], start_move: int = 1) -> int:
        """Find the first ply where games diverge from a common path."""
        if not games:
            return -1
        
        start_idx = (start_move - 1) * 2
        max_length = min(len(game.moves) for game in games if game.moves)
        
        if max_length <= start_idx:
            return -1
        
        for ply_idx in range(start_idx, max_length):
            moves_at_ply = set()
            for game in games:
                if ply_idx < len(game.moves):
                    clean_move = re.sub(r'[+#]$', '', game.moves[ply_idx])
                    moves_at_ply.add(clean_move)
            
            if len(moves_at_ply) > 1:
                return ply_idx
        
        return -1

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
                       help='Show additional statistics about matches')
    parser.add_argument('--no-branching', action='store_true',
                       help='Skip branching point analysis')
    
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
    
    if matching_games:
        # Analyze branching point (unless disabled)
        if not args.no_branching:
            analysis = pgn_filter.analyze_branching_point(matching_games, pattern, args.start_move)
            pgn_filter.print_branching_analysis(analysis)
        
        if args.show_stats:
            print("\nSample matching games:")
            for i, game in enumerate(matching_games[:3]):  # Show first 3
                white = game.headers.get('White', 'Unknown')
                black = game.headers.get('Black', 'Unknown')
                result = game.headers.get('Result', '*')
                print(f"  {i+1}. {white} vs {black} ({result})")
                print(f"     Moves: {' '.join(game.moves[:10])}...")
    
        # Save results
        output_file = args.output or 'filtered_games.pgn'
        pgn_filter.save_filtered_games(matching_games, output_file)
    else:
        print("No matching games found.")

if __name__ == '__main__':
    main()