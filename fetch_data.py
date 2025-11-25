"""
Fantasy NBA Data Fetcher
Fetches data from NBA API and saves to JSON files with graceful degradation
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import requests
from nba_api.stats.endpoints import leaguegamefinder, leaguedashplayerstats, leaguedashteamstats
from nba_api.stats.static import teams
from requests.exceptions import ReadTimeout, ConnectionError, RequestException
import time

# Configuration
DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)

TIMEOUT = 60  # Increased from 30s for better reliability
MAX_RETRIES = 3
RETRY_DELAY = 5  # Increased from 3s to give API more recovery time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.nba.com/'
}

def retry_api_call(func, retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Wrapper for API calls with retry logic"""
    for i in range(retries):
        try:
            return func()
        except (ReadTimeout, ConnectionError, RequestException) as e:
            print(f"  ⚠️  API Error (Attempt {i+1}/{retries}): {type(e).__name__}")
            if i < retries - 1:
                sleep_time = delay * (i + 1)
                print(f"  ⏳ Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
            else:
                print(f"  ❌ Max retries reached for {func.__name__}")
                raise


def fetch_schedule_espn(start_date, end_date):
    """
    Fetch NBA schedule from ESPN API (includes future games)
    Handles long date ranges by fetching in chunks
    """
    print(f"\n📅 Fetching schedule from ESPN API...")
    print(f"  Date range: {start_date} to {end_date}")
    
    base_url = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    all_games = []
    
    # ESPN API returns max ~100 games per request
    # Use smaller chunks (7 days) to avoid hitting the limit
    current_date = start_date
    chunk_size = 7  # Days per request (1 week)
    
    while current_date <= end_date:
        chunk_end = min(current_date + timedelta(days=chunk_size - 1), end_date)
        
        # Format dates as YYYYMMDD
        start_str = current_date.strftime('%Y%m%d')
        end_str = chunk_end.strftime('%Y%m%d')
        
        url = f"{base_url}?dates={start_str}-{end_str}"
        
        def api_call():
            return requests.get(url, headers=headers, timeout=TIMEOUT)
        
        try:
            response = retry_api_call(api_call)
            data = response.json()
            
            if 'events' in data:
                print(f"  📥 Fetched {len(data['events'])} games for {current_date} to {chunk_end}")
                
                for event in data['events']:
                    # Extract game info
                    game_date = event.get('date', '')
                    competitions = event.get('competitions', [])
                    
                    if not competitions:
                        continue
                    
                    competition = competitions[0]
                    competitors = competition.get('competitors', [])
                    
                    if len(competitors) < 2:
                        continue
                    
                    # Find home and away teams
                    home_team = None
                    away_team = None
                    
                    for competitor in competitors:
                        if competitor.get('homeAway') == 'home':
                            home_team = competitor.get('team', {})
                        else:
                            away_team = competitor.get('team', {})
                    
                    if not home_team or not away_team:
                        continue
                    
                    # Only include NBA teams (filter out preseason opponents)
                    nba_teams = {
                        'ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GS',
                        'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NO', 'NY',
                        'OKC', 'ORL', 'PHI', 'PHX', 'POR', 'SA', 'SAC', 'TOR', 'UTAH', 'WSH'
                    }
                    
                    home_abbr = home_team.get('abbreviation', '')
                    away_abbr = away_team.get('abbreviation', '')
                    
                    # Skip if either team is not an NBA team
                    if home_abbr not in nba_teams or away_abbr not in nba_teams:
                        continue
                    
                    # Parse date and convert to ET timezone
                    try:
                        # ESPN returns UTC time, convert to ET
                        from datetime import timezone
                        game_datetime_utc = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                        
                        # Convert to ET (UTC-5 or UTC-4 depending on DST, simplify to UTC-5)
                        et_offset = timedelta(hours=-5)
                        game_datetime_et = game_datetime_utc + et_offset
                        game_date_only = game_datetime_et.date()
                    except:
                        continue
                    
                    # Add games for both teams
                    # Home team game
                    all_games.append({
                        'date': str(game_date_only),
                        'team_id': int(home_team.get('id', 0)),
                        'team_abbr': home_abbr,
                        'matchup': f"{home_abbr} vs. {away_abbr}",
                        'is_home': True
                    })
                    
                    # Away team game
                    all_games.append({
                        'date': str(game_date_only),
                        'team_id': int(away_team.get('id', 0)),
                        'team_abbr': away_abbr,
                        'matchup': f"{away_abbr} @ {home_abbr}",
                        'is_home': False
                    })
            
            # Small delay between chunks to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ⚠️  Failed to fetch chunk {current_date} to {chunk_end}: {e}")
        
        # Move to next chunk
        current_date = chunk_end + timedelta(days=1)
    
    result = {
        'season': '2025-26',
        'source': 'ESPN API',
        'updated_at': datetime.now().isoformat(),
        'games': all_games
    }
    
    print(f"  ✅ Total fetched: {len(all_games)} game entries ({len(all_games)//2} games)")
    return result if all_games else None


def fetch_player_stats(season='2025-26', date_from=None, label='Season'):
    """Fetch player stats for a given period (both averages and totals)"""
    print(f"\n👥 Fetching player stats ({label})...")
    
    # Fetch averages (PerGame)
    def api_call_avg():
        date_from_str = date_from.strftime('%m/%d/%Y') if date_from else ''
        return leaguedashplayerstats.LeagueDashPlayerStats(
            per_mode_detailed='PerGame',
            season=season,
            season_type_all_star='Regular Season',
            date_from_nullable=date_from_str,
            timeout=TIMEOUT,
            headers=HEADERS
        )
    
    # Fetch totals
    def api_call_tot():
        date_from_str = date_from.strftime('%m/%d/%Y') if date_from else ''
        return leaguedashplayerstats.LeagueDashPlayerStats(
            per_mode_detailed='Totals',
            season=season,
            season_type_all_star='Regular Season',
            date_from_nullable=date_from_str,
            timeout=TIMEOUT,
            headers=HEADERS
        )
    
    try:
        # Fetch averages
        stats_obj_avg = retry_api_call(api_call_avg)
        df_avg = stats_obj_avg.get_data_frames()[0]
        
        # Fetch totals
        stats_obj_tot = retry_api_call(api_call_tot)
        df_tot = stats_obj_tot.get_data_frames()[0]
        
        if df_avg.empty:
            print(f"  ⚠️  No player stats found")
            return None
        
        # Filter active players only
        df_avg = df_avg[df_avg['GP'] > 0]
        df_tot = df_tot[df_tot['GP'] > 0]
        
        # Extract relevant fields from averages
        players_data = []
        for _, player_avg in df_avg.iterrows():
            player_id = int(player_avg['PLAYER_ID'])
            
            # Find matching totals row
            player_tot_row = df_tot[df_tot['PLAYER_ID'] == player_id]
            
            if player_tot_row.empty:
                # Skip if no totals data
                continue
            
            player_tot = player_tot_row.iloc[0]
            
            # Map NBA Stats API abbreviations to ESPN abbreviations
            team_abbr_map = {
                'GSW': 'GS',    # Golden State Warriors
                'NOP': 'NO',    # New Orleans Pelicans
                'NYK': 'NY',    # New York Knicks
                'SAS': 'SA',    # San Antonio Spurs
                'UTA': 'UTAH',  # Utah Jazz
                'WAS': 'WSH'    # Washington Wizards
            }
            
            original_team = player_avg['TEAM_ABBREVIATION']
            mapped_team = team_abbr_map.get(original_team, original_team)
            
            players_data.append({
                'player_id': player_id,
                'name': player_avg['PLAYER_NAME'],
                'team': mapped_team,
                'gp': int(player_avg['GP']),
                # Averages
                'min_avg': float(player_avg['MIN']),
                'pts_avg': float(player_avg['PTS']),
                'reb_avg': float(player_avg['REB']),
                'ast_avg': float(player_avg['AST']),
                'stl_avg': float(player_avg['STL']),
                'blk_avg': float(player_avg['BLK']),
                'tov_avg': float(player_avg['TOV']),
                'fg_pct': float(player_avg['FG_PCT']),
                'ft_pct': float(player_avg['FT_PCT']),
                'fg3m_avg': float(player_avg['FG3M']),
                # Totals
                'pts_tot': float(player_tot['PTS']),
                'reb_tot': float(player_tot['REB']),
                'ast_tot': float(player_tot['AST']),
                'stl_tot': float(player_tot['STL']),
                'blk_tot': float(player_tot['BLK']),
                'tov_tot': float(player_tot['TOV']),
                'fg3m_tot': float(player_tot['FG3M'])
            })
        
        result = {
            'season': season,
            'period': label,
            'date_from': date_from.isoformat() if date_from else None,
            'updated_at': datetime.now().isoformat(),
            'players': players_data
        }
        
        print(f"  ✅ Fetched {len(players_data)} players (avg + tot)")
        return result
        
    except Exception as e:
        print(f"  ❌ Failed to fetch player stats: {e}")
        return None


def fetch_defensive_ratings(season='2025-26'):
    """Fetch team defensive ratings"""
    print(f"\n🛡️  Fetching defensive ratings for {season}...")
    
    def api_call():
        return leaguedashteamstats.LeagueDashTeamStats(
            per_mode_detailed='PerGame',
            season=season,
            season_type_all_star='Regular Season',
            measure_type_detailed_defense='Advanced',
            timeout=TIMEOUT,
            headers=HEADERS
        )
    
    try:
        stats_obj = retry_api_call(api_call)
        df = stats_obj.get_data_frames()[0]
        
        # Get team abbreviations
        nba_teams = teams.get_teams()
        id_to_abbr = {team['id']: team['abbreviation'] for team in nba_teams}
        
        # Sort by defensive rating
        if 'DEF_RATING' in df.columns:
            df = df.sort_values('DEF_RATING', ascending=True)
        else:
            df = df.sort_values('W_PCT', ascending=False)
        
        df['DEF_RANK'] = range(1, len(df) + 1)
        
        # Extract data
        ratings_data = []
        for _, team in df.iterrows():
            abbr = id_to_abbr.get(team['TEAM_ID'], 'UNK')
            ratings_data.append({
                'team_abbr': abbr,
                'rank': int(team['DEF_RANK']),
                'def_rating': float(team.get('DEF_RATING', 0))
            })
        
        result = {
            'season': season,
            'updated_at': datetime.now().isoformat(),
            'teams': ratings_data
        }
        
        print(f"  ✅ Fetched ratings for {len(ratings_data)} teams")
        return result
        
    except Exception as e:
        print(f"  ❌ Failed to fetch defensive ratings: {e}")
        return None


def save_json(data, filename):
    """Save data to JSON file"""
    if data is None:
        print(f"  ⚠️  Skipping save for {filename} (no data)")
        return False
    
    filepath = DATA_DIR / filename
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  💾 Saved to {filename}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to save {filename}: {e}")
        return False


def main():
    """Main execution"""
    print("=" * 60)
    print("🏀 Fantasy NBA Data Fetcher")
    print("=" * 60)
    
    current_season = '2025-26'
    today = datetime.now().date()
    
    # Force 2025 for GitHub Actions (same logic as before)
    if today.year == 2024:
        print("⚠️  Server is in 2024, using 2025 for season detection")
        try:
            today = today.replace(year=2025)
        except ValueError:
            today = today + timedelta(days=365)
    
    # Determine season
    curr_year = today.year
    if today.month >= 10:
        current_season = f"{curr_year}-{str(curr_year+1)[-2:]}"
    else:
        current_season = f"{curr_year-1}-{str(curr_year)[-2:]}"
    
    print(f"📆 Current Season: {current_season}")
    print(f"📆 Today: {today}")
    
    results = {
        'schedule': False,
        'player_stats_season': False,
        'player_stats_l7': False,
        'player_stats_l14': False,
        'defensive_ratings': False
    }
    
    
    # Fetch full season schedule (2025-26 regular season)
    # NBA regular season typically runs from October to mid-April
    # 2025-26 season: Oct 2025 to April 13-15, 2026
    
    # Determine season start and end dates
    if today.month >= 10:  # Currently in Oct-Dec
        season_start = datetime(today.year, 10, 1).date()
        season_end = datetime(today.year + 1, 4, 15).date()  # Playoffs usually start around April 15
    elif today.month <= 4:  # Currently in Jan-Apr
        season_start = datetime(today.year - 1, 10, 1).date()
        season_end = datetime(today.year, 4, 15).date()
    else:  # May-Sep (offseason)
        season_start = datetime(today.year, 10, 1).date()
        season_end = datetime(today.year + 1, 4, 15).date()
    
    print(f"📅 Fetching FULL season schedule: {season_start} to {season_end}")
    schedule_data = fetch_schedule_espn(season_start, season_end)
    results['schedule'] = save_json(schedule_data, f'schedule_{current_season}.json')
    
    # Fetch current season player stats
    player_stats = fetch_player_stats(current_season, label='Season')
    results['player_stats_season'] = save_json(player_stats, 'player_stats_season.json')
    
    # Fetch L7 stats
    d7 = today - timedelta(days=7)
    player_stats_l7 = fetch_player_stats(current_season, date_from=d7, label='Last 7 Days')
    results['player_stats_l7'] = save_json(player_stats_l7, 'player_stats_l7.json')
    
    # Fetch L14 stats
    d14 = today - timedelta(days=14)
    player_stats_l14 = fetch_player_stats(current_season, date_from=d14, label='Last 14 Days')
    results['player_stats_l14'] = save_json(player_stats_l14, 'player_stats_l14.json')
    
    # Fetch defensive ratings
    def_ratings = fetch_defensive_ratings(current_season)
    results['defensive_ratings'] = save_json(def_ratings, 'defensive_ratings.json')
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print("=" * 60)
    success_count = sum(results.values())
    total_count = len(results)
    
    for key, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {key}")
    
    print(f"\n✨ Successfully fetched {success_count}/{total_count} data sources")
    
    # Exit code: 0 if at least half succeeded, 1 otherwise
    if success_count >= total_count / 2:
        print("✅ Data fetch completed successfully")
        sys.exit(0)
    else:
        print("⚠️  Data fetch completed with failures")
        sys.exit(1)


if __name__ == '__main__':
    main()
