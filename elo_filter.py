#!/usr/bin/env python3
"""
Memory-efficient PGN Rating Filter
Filters games where both players have ratings above a specified threshold.
Streams through the file without loading everything into memory.
"""

import re
import argparse
import sys
from typing import TextIO, Optional, Dict

class PGNRatingFilter:
    def __init__(self, min_rating: int = 2450, output_file: Optional[str] = None):
        self.min_rating = min_rating
        self.output_file = output_file
        self.games_processed = 0
        self.games_matched = 0
        self.output_handle = None
        
    def __enter__(self):
        if self.output_file:
            self.output_handle = open(self.output_file, 'w', encoding='utf-8')
        else:
            self.output_handle = sys.stdout
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.output_file and self.output_handle:
            self.output_handle.close()
    
    def extract_rating(self, header_value: str) -> Optional[int]:
        """Extract numeric rating from header value, handling various formats."""
        if not header_value or header_value == '?':
            return None
        
        # Remove quotes if present
        header_value = header_value.strip('"')
        
        # Try to extract number (handle formats like "2450", "2450?", etc.)
        match = re.search(r'(\d{3,4})', header_value)
        if match:
            rating = int(match.group(1))
            # Sanity check for reasonable rating range
            if 1000 <= rating <= 3500:
                return rating
        
        return None
    
    def parse_header(self, line: str) -> Optional[tuple]:
        """Parse a PGN header line and return (key, value) tuple."""
        match = re.match(r'\[(\w+)\s+"([^"]*)"\]', line.strip())
        if match:
            return match.group(1), match.group(2)
        return None
    
    def should_include_game(self, headers: Dict[str, str]) -> bool:
        """Check if game should be included based on rating criteria."""
        white_elo = headers.get('WhiteElo')
        black_elo = headers.get('BlackElo')
        
        if not white_elo or not black_elo:
            return False
        
        white_rating = self.extract_rating(white_elo)
        black_rating = self.extract_rating(black_elo)
        
        if white_rating is None or black_rating is None:
            return False
        
        return white_rating >= self.min_rating and black_rating >= self.min_rating
    
    def process_file(self, input_file: str):
        """Stream through PGN file and filter games by rating."""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                self._stream_process(f)
        except UnicodeDecodeError:
            # Try with latin-1 encoding if utf-8 fails
            with open(input_file, 'r', encoding='latin-1') as f:
                self._stream_process(f)
    
    def _stream_process(self, file_handle: TextIO):
        """Internal method to stream process the file."""
        current_game_lines = []
        current_headers = {}
        in_game = False
        
        for line_num, line in enumerate(file_handle, 1):
            line = line.strip()
            
            # Header line
            if line.startswith('[') and line.endswith(']'):
                if not in_game:
                    # Start of new game
                    in_game = True
                    current_game_lines = []
                    current_headers = {}
                
                # Parse header
                header_info = self.parse_header(line)
                if header_info:
                    key, value = header_info
                    current_headers[key] = value
                
                current_game_lines.append(line)
            
            elif line and in_game:
                # Move lines
                current_game_lines.append(line)
            
            elif not line and in_game:
                # Empty line - end of game
                self.games_processed += 1
                
                # Check if game meets rating criteria
                if self.should_include_game(current_headers):
                    self.games_matched += 1
                    # Write game to output
                    for game_line in current_game_lines:
                        self.output_handle.write(game_line + '\n')
                    self.output_handle.write('\n')  # Empty line after game
                
                # Reset for next game
                in_game = False
                current_game_lines = []
                current_headers = {}
                
                # Progress indicator
                if self.games_processed % 1000 == 0:
                    print(f"Processed {self.games_processed} games, found {self.games_matched} matches", 
                          file=sys.stderr)
        
        # Handle last game if file doesn't end with empty line
        if in_game and current_game_lines:
            self.games_processed += 1
            if self.should_include_game(current_headers):
                self.games_matched += 1
                for game_line in current_game_lines:
                    self.output_handle.write(game_line + '\n')
                self.output_handle.write('\n')
    
    def print_summary(self):
        """Print filtering summary."""
        print(f"\n=== FILTERING SUMMARY ===", file=sys.stderr)
        print(f"Total games processed: {self.games_processed}", file=sys.stderr)
        print(f"Games with both players ≥ {self.min_rating}: {self.games_matched}", file=sys.stderr)
        if self.games_processed > 0:
            percentage = (self.games_matched / self.games_processed) * 100
            print(f"Match percentage: {percentage:.1f}%", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description='Filter PGN games where both players have ratings above threshold',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s database.pgn -o high_rated.pgn
  %(prog)s database.pgn --min-rating 2600
  %(prog)s database.pgn > filtered_games.pgn
  cat database.pgn | %(prog)s - --min-rating 2500
        """
    )
    
    parser.add_argument('input_file', 
                       help='Input PGN file (use "-" for stdin)')
    parser.add_argument('-o', '--output', 
                       help='Output PGN file (default: stdout)')
    parser.add_argument('--min-rating', type=int, default=2450,
                       help='Minimum rating for both players (default: 2450)')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress progress messages')
    parser.add_argument('--no-summary', action='store_true',
                       help='Skip summary statistics')
    
    args = parser.parse_args()
    
    # Handle stdin
    if args.input_file == '-':
        print("Error: stdin processing not implemented in this version", file=sys.stderr)
        sys.exit(1)
    
    # Create filter and process
    with PGNRatingFilter(args.min_rating, args.output) as filter_obj:
        if not args.quiet:
            print(f"Filtering games with both players ≥ {args.min_rating} rating...", 
                  file=sys.stderr)
        
        filter_obj.process_file(args.input_file)
        
        if not args.no_summary:
            filter_obj.print_summary()

if __name__ == '__main__':
    main()