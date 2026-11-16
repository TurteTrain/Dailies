import './rewind.css'

const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1)

// One ranked card (top songs / artists / genres) with a bar showing each row's share of the leader
function RankCard({ title, rows, emptyText }) {
    const max = Math.max(1, ...rows.map((r) => r.plays))
    return (
        <div className = "rw-card">
            <h3>{title}</h3>
            {rows.length === 0 ? (
                <p className = "rw-empty">{emptyText}</p>
            ) : (
                <ol className = "rw-list">
                    {rows.map((r) => (
                        <li key = {r.key}>
                            <div className = "rw-bar" style = {{ width: `${(r.plays / max) * 100}%` }} />
                            <div className = "rw-row">
                                <span className = "rw-name">
                                    {r.primary}
                                    {r.secondary && <span className = "rw-sub"> {r.secondary}</span>}
                                </span>
                                <span className = "rw-plays">{r.plays}x</span>
                            </div>
                        </li>
                    ))}
                </ol>
            )}
        </div>
    )
}

// The stats row and ranked cards for one day's rewind. Purely presentational (no fetching, no
// controls), so the owner's dashboard and a friend's read-only view render identically.
// `showMoodBreakdown` adds the per-mood card; the friend view only shows the mood of the day.
export function RewindSummary({ data, showMoodBreakdown = true }) {
    return (
        <>
            <div className = "rw-stats">
                <div><strong>{data.total_plays}</strong><span>plays</span></div>
                <div><strong>~{data.approx_minutes}</strong><span>minutes</span></div>
                {data.mood_of_the_day && (
                    <div><strong>{capitalize(data.mood_of_the_day)}</strong><span>mood of the day</span></div>
                )}
            </div>
            <div className = "rw-grid">
                <RankCard title = "Top songs" emptyText = "No songs."
                    rows = {data.top_tracks.map((t) => ({
                        key: t.track_id, primary: t.name, secondary: t.artist, plays: t.plays }))} />
                <RankCard title = "Top artists" emptyText = "No artist data for this day yet."
                    rows = {data.top_artists.map((a) => ({
                        key: a.artist_id, primary: a.name, plays: a.plays }))} />
                <RankCard title = "Top genres" emptyText = "No genre data yet."
                    rows = {data.top_genres.map((g) => ({
                        key: g.genre, primary: g.genre, plays: g.plays }))} />
                {showMoodBreakdown && (
                    <RankCard title = "Moods" emptyText = "No mood data yet."
                        rows = {(data.top_moods || []).map((m) => ({
                            key: m.mood, primary: capitalize(m.mood),
                            secondary: `${Math.round(m.share * 100)}%`, plays: m.plays }))} />
                )}
            </div>
        </>
    )
}
