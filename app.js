/**
 * Fantasy NBA Frontend App - Production Version
 */

class FantasyNBAApp {
    constructor() {
        this.data = {
            schedule: null,
            playerStatsseason: null,
            playerStatsL7: null,
            playerStatsL14: null,
            defensiveRatings: null
        };

        this.currentWeek = 0;
        this.currentStatPeriod = 'Season';
        this.currentDisplayMode = 'avg';
        this.selectedTeam = null;
        this.sortColumn = 'gamesThisWeek';
        this.sortDirection = 'desc';

        this.teamNames = {
            'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets',
            'CHA': 'Charlotte Hornets', 'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers',
            'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons',
            'GS': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
            'LAC': 'LA Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies',
            'MIA': 'Miami Heat', 'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves',
            'NO': 'New Orleans Pelicans', 'NY': 'New York Knicks', 'OKC': 'Oklahoma City Thunder',
            'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns',
            'POR': 'Portland Trail Blazers', 'SA': 'San Antonio Spurs', 'SAC': 'Sacramento Kings',
            'TOR': 'Toronto Raptors', 'UTAH': 'Utah Jazz', 'WSH': 'Washington Wizards'
        };
    }

    async init() {
        this.showLoading();
        await this.loadAllData();
        this.render();
    }

    showLoading() {
        document.getElementById('app').innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>Loading NBA data...</p>
            </div>
        `;
    }

    async loadJSON(filename) {
        try {
            const response = await fetch(`data/${filename}`);
            if (!response.ok) throw new Error(`Failed to load ${filename}`);
            return await response.json();
        } catch (error) {
            console.error(`Error loading ${filename}:`, error);
            return null;
        }
    }

    async loadAllData() {
        const season = this.getCurrentSeason();
        const [schedule, statsseason, statsL7, statsL14, defensiveRatings] = await Promise.all([
            this.loadJSON(`schedule_${season}.json`),
            this.loadJSON('player_stats_season.json'),
            this.loadJSON('player_stats_l7.json'),
            this.loadJSON('player_stats_l14.json'),
            this.loadJSON('defensive_ratings.json')
        ]);

        this.data.schedule = schedule;
        this.data.playerStatsseason = statsseason;
        this.data.playerStatsL7 = statsL7;
        this.data.playerStatsL14 = statsL14;
        this.data.defensiveRatings = defensiveRatings;
    }

    getCurrentSeason() {
        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth() + 1;
        return month >= 10 ? `${year}-${String(year + 1).slice(-2)}` : `${year - 1}-${String(year).slice(-2)}`;
    }

    render() {
        const app = document.getElementById('app');
        if (!this.data.playerStatsseason || !this.data.schedule) {
            app.innerHTML = `<div class="error"><h2>⚠️ Unable to load data</h2></div>`;
            return;
        }

        const weeks = this.generateWeeks();
        app.innerHTML = `
            <div class="container">
                <header>
                    <h1>🏀 Fantasy NBA Streaming Assistant</h1>
                    <div class="update-info">Last updated: ${this.getLastUpdate()}</div>
                </header>
                <div class="legend">
                    <b>Matchup Strength (DvP):</b>
                    <span class="dot" style="background-color:#ccffcc"></span>Easy
                    <span class="dot" style="background-color:#ffffcc"></span>Average
                    <span class="dot" style="background-color:#ffcccc"></span>Hard
                </div>
                <div class="tabs">
                    ${weeks.map((w, i) => `<button class="tab-btn ${i === 0 ? 'active' : ''}" onclick="app.switchWeek(${i})">${w.label}</button>`).join('')}
                </div>
                <div id="week-content">${this.renderWeek(weeks[0])}</div>
            </div>
        `;
    }

    generateWeeks() {
        const weeks = [];
        const today = new Date();

        // Adjust to Monday of current week
        const day = today.getDay();
        const monday = new Date(today);
        monday.setDate(today.getDate() - day + (day === 0 ? -6 : 1));

        for (let i = 0; i < 4; i++) {
            const start = new Date(monday);
            start.setDate(monday.getDate() + (i * 7));
            const end = new Date(start);
            end.setDate(start.getDate() + 6);
            weeks.push({
                label: `Week ${i + 1} (${this.formatDate(start)} - ${this.formatDate(end)})`,
                start, end
            });
        }
        return weeks;
    }

    renderWeek(week) {
        const games = this.getGamesForWeek(week.start, week.end);
        const teamSchedule = this.buildTeamSchedule(games);
        const players = this.mergePlayerData(teamSchedule);
        return `
            <div class="week-content">
                ${this.renderTeamTable(teamSchedule, week)}
                <hr/>
                ${this.renderPlayerTable(players, week)}
            </div>
        `;
    }

    renderTeamTable(teamSchedule, week) {
        const days = this.getDaysInRange(week.start, week.end);
        return `
            <div class="team-section">
                <h3>Team Schedule (Click to Filter)</h3>
                <table class="team-table">
                    <thead><tr>
                        <th>Team</th><th>Games</th>
                        ${days.map(d => `<th>${this.formatDayHeader(d)}</th>`).join('')}
                    </tr></thead>
                    <tbody>
                        ${teamSchedule.map(team => `
                            <tr class="team-row ${this.selectedTeam === team.abbr ? 'selected' : ''}" onclick="app.filterTeam('${team.abbr}')">
                                <td><b>${this.teamNames[team.abbr] || team.abbr}</b></td>
                                <td>${team.games}</td>
                                ${days.map(d => `<td>${this.renderMatchup(team, d)}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderPlayerTable(players, week) {
        const days = this.getDaysInRange(week.start, week.end);
        const stats = ['MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FG%', 'FT%', '3PM'];
        const filtered = this.selectedTeam ? players.filter(p => p.team === this.selectedTeam) : players;

        return `
            <div class="player-section">
                <div class="controls">
                    <button class="btn-stat ${this.currentStatPeriod === 'Season' ? 'active' : ''}" onclick="app.switchStats('Season')">Season</button>
                    <button class="btn-stat ${this.currentStatPeriod === 'L7' ? 'active' : ''}" onclick="app.switchStats('L7')">Last 7</button>
                    <button class="btn-stat ${this.currentStatPeriod === 'L14' ? 'active' : ''}" onclick="app.switchStats('L14')">Last 14</button>
                    <span style="margin-left:20px">Show:</span>
                    <button class="btn-stat ${this.currentDisplayMode === 'avg' ? 'active' : ''}" onclick="app.switchDisplayMode('avg')">AVG</button>
                    <button class="btn-stat ${this.currentDisplayMode === 'tot' ? 'active' : ''}" onclick="app.switchDisplayMode('tot')">TOT</button>
                    ${this.selectedTeam ? '<button class="btn-reset" onclick="app.filterTeam(null)">Show All</button>' : ''}
                </div>
                <table class="player-table">
                    <thead><tr>
                        <th onclick="app.sortBy('name')" style="cursor:pointer">Player${this.getSortInd('name')}</th>
                        <th onclick="app.sortBy('team')" style="cursor:pointer">Team${this.getSortInd('team')}</th>
                        <th onclick="app.sortBy('gamesThisWeek')" style="cursor:pointer">Games${this.getSortInd('gamesThisWeek')}</th>
                        ${days.map(d => `<th>${this.formatDayHeader(d)}</th>`).join('')}
                        ${stats.map(s => `<th onclick="app.sortBy('${this.getStatKey(s)}')" style="cursor:pointer">${s}${this.getSortInd(this.getStatKey(s))}</th>`).join('')}
                    </tr></thead>
                    <tbody>
                        ${filtered.map(p => this.renderPlayerRow(p, days, stats)).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderPlayerRow(player, days, stats) {
        const currentStats = this.getPlayerStats(player, this.currentStatPeriod);
        return `
            <tr>
                <td><b>${player.name}</b><br><span style="color:#888">${player.team}</span></td>
                <td>${player.team}</td>
                <td>${player.gamesThisWeek || 0}</td>
                ${days.map(d => `<td>${this.renderPlayerMatchup(player, d)}</td>`).join('')}
                ${stats.map(s => `<td>${this.formatStat(currentStats, s)}</td>`).join('')}
            </tr>
        `;
    }

    getPlayerStats(player, period) {
        if (period === 'L7') return this.data.playerStatsL7?.players.find(p => p.player_id === player.player_id) || {};
        if (period === 'L14') return this.data.playerStatsL14?.players.find(p => p.player_id === player.player_id) || {};
        return player;
    }

    formatStat(stats, statName) {
        const key = this.getStatKey(statName);
        const val = stats[key];
        if (val === undefined || val === null) return '-';
        return statName.includes('%') ? `${(val * 100).toFixed(1)}%` : val.toFixed(1);
    }

    getStatKey(stat) {
        const mode = this.currentDisplayMode;
        const map = {
            'MIN': 'min_avg', 'PTS': mode === 'avg' ? 'pts_avg' : 'pts_tot',
            'REB': mode === 'avg' ? 'reb_avg' : 'reb_tot', 'AST': mode === 'avg' ? 'ast_avg' : 'ast_tot',
            'STL': mode === 'avg' ? 'stl_avg' : 'stl_tot', 'BLK': mode === 'avg' ? 'blk_avg' : 'blk_tot',
            'TO': mode === 'avg' ? 'tov_avg' : 'tov_tot', 'FG%': 'fg_pct', 'FT%': 'ft_pct',
            '3PM': mode === 'avg' ? 'fg3m_avg' : 'fg3m_tot'
        };
        return map[stat] || stat;
    }

    getSortInd(col) {
        return this.sortColumn === col ? (this.sortDirection === 'asc' ? ' ▲' : ' ▼') : '';
    }

    sortBy(col) {
        if (this.sortColumn === col) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = col;
            this.sortDirection = 'desc';
        }
        const weeks = this.generateWeeks();
        document.getElementById('week-content').innerHTML = this.renderWeek(weeks[this.currentWeek]);
    }

    sortPlayers(players) {
        return players.sort((a, b) => {
            let aVal, bVal;

            // For string columns (name, team)
            if (this.sortColumn === 'name' || this.sortColumn === 'team') {
                aVal = a[this.sortColumn] || '';
                bVal = b[this.sortColumn] || '';
                return this.sortDirection === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }

            // For numeric columns - get values from current stat period
            const aStats = this.getPlayerStats(a, this.currentStatPeriod);
            const bStats = this.getPlayerStats(b, this.currentStatPeriod);

            if (this.sortColumn === 'gamesThisWeek') {
                aVal = a.gamesThisWeek || 0;
                bVal = b.gamesThisWeek || 0;
            } else {
                // Get stat value from current period data
                aVal = aStats[this.sortColumn] !== undefined ? aStats[this.sortColumn] : -999;
                bVal = bStats[this.sortColumn] !== undefined ? bStats[this.sortColumn] : -999;
            }

            return this.sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
        });
    }

    mergePlayerData(teamSchedule) {
        if (!this.data.playerStatsseason) return [];
        let players = this.data.playerStatsseason.players.map(p => ({
            ...p,
            gamesThisWeek: teamSchedule.find(t => t.abbr === p.team)?.games || 0
        }));
        return this.sortPlayers(players);
    }

    getGamesForWeek(start, end) {
        const startStr = start.toISOString().split('T')[0];
        const endStr = end.toISOString().split('T')[0];
        return this.data.schedule?.games.filter(g => g.date >= startStr && g.date <= endStr) || [];
    }

    buildTeamSchedule(games) {
        const map = {};
        games.forEach(g => {
            if (!map[g.team_abbr]) map[g.team_abbr] = { abbr: g.team_abbr, games: 0, schedule: {} };
            map[g.team_abbr].games++;
            map[g.team_abbr].schedule[g.date] = g;
        });
        return Object.values(map).sort((a, b) => a.abbr.localeCompare(b.abbr));
    }

    renderMatchup(team, date) {
        const game = team.schedule[date.toISOString().split('T')[0]];
        if (!game) return '';
        const opp = game.matchup.split(' ').pop();
        const rank = this.getDefensiveRank(opp);
        const color = this.getColorForRank(rank);
        return `<div style="background-color:${color};padding:4px;border-radius:4px;text-align:center;font-weight:bold" title="Def Rank: ${rank}">${game.is_home ? 'vs' : '@'} ${opp}</div>`;
    }

    renderPlayerMatchup(player, date) {
        const key = date.toISOString().split('T')[0];
        const game = this.data.schedule?.games.find(g => g.team_abbr === player.team && g.date === key);
        if (!game) return '';
        const opp = game.matchup.split(' ').pop();
        const color = this.getColorForRank(this.getDefensiveRank(opp));
        return `<div style="background-color:${color};padding:2px 4px;border-radius:3px;text-align:center;font-size:0.85em;font-weight:bold">${game.is_home ? 'vs' : '@'} ${opp}</div>`;
    }

    getDefensiveRank(team) {
        return this.data.defensiveRatings?.teams.find(t => t.team_abbr === team)?.rank || 15;
    }

    getColorForRank(r) {
        if (r <= 6) return '#ffcccc';
        if (r <= 12) return '#ffe5cc';
        if (r <= 18) return '#ffffcc';
        if (r <= 24) return '#e5ffcc';
        return '#ccffcc';
    }

    getDaysInRange(start, end) {
        const days = [];
        const cur = new Date(start);
        while (cur <= end) {
            days.push(new Date(cur));
            cur.setDate(cur.getDate() + 1);
        }
        return days;
    }

    formatDate(d) {
        return `${d.getMonth() + 1}/${d.getDate()}`;
    }

    formatDayHeader(d) {
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        return `${days[d.getDay()]} (${this.formatDate(d)})`;
    }

    getLastUpdate() {
        const updates = [this.data.schedule?.updated_at, this.data.playerStatsseason?.updated_at].filter(Boolean);
        if (!updates.length) return 'Unknown';
        return new Date(Math.max(...updates.map(d => new Date(d)))).toLocaleString();
    }

    switchWeek(i) {
        this.currentWeek = i;
        const weeks = this.generateWeeks();
        document.getElementById('week-content').innerHTML = this.renderWeek(weeks[i]);
        document.querySelectorAll('.tab-btn').forEach((btn, idx) => btn.classList.toggle('active', idx === i));
    }

    switchStats(period) {
        this.currentStatPeriod = period;
        const weeks = this.generateWeeks();
        document.getElementById('week-content').innerHTML = this.renderWeek(weeks[this.currentWeek]);
    }

    switchDisplayMode(mode) {
        this.currentDisplayMode = mode;
        const weeks = this.generateWeeks();
        document.getElementById('week-content').innerHTML = this.renderWeek(weeks[this.currentWeek]);
    }

    filterTeam(team) {
        this.selectedTeam = team;
        const weeks = this.generateWeeks();
        document.getElementById('week-content').innerHTML = this.renderWeek(weeks[this.currentWeek]);
    }
}

let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new FantasyNBAApp();
    app.init();
});
