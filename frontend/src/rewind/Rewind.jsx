import { useEffect, useState } from 'react'
import { api } from '../api.js'
import './rewind.css'

// The browser's timezone decides which calendar day a play belongs to.
const TZ = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

const pad = (n) => String(n).padStart(2, '0')
// "YYYY-MM-DD" for a Date, using the browser's local calendar day
const toISO = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const fromISO = (iso) => {
    const [y, m, d] = iso.split('-').map(Number)
    return new Date(y, m - 1, d)
}
const shiftDay = (iso, delta) => {
    const d = fromISO(iso)
    d.setDate(d.getDate() + delta)
    return toISO(d)
}
const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1)
const prettyDate = (iso) =>
    fromISO(iso).toLocaleDateString(undefined, {
        weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
    })

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

const Rewind = () => {
    const today = toISO(new Date())
    const [date, setDate] = useState(today)
    const [result, setResult] = useState(null)   // {date, data} or {date, error}

    // Re-fetch whenever the chosen day changes. The "ignore" flag drops answers that arrive
    // after the user has already clicked to another day.
    useEffect(() => {
        let ignore = false
        api(`rewind?date=${date}&tz=${encodeURIComponent(TZ)}`)
            .then((data) => { if (!ignore) setResult({ date, data }) })
            .catch((e) => { if (!ignore) setResult({ date, error: e.message }) })
        return () => { ignore = true }
    }, [date])

    const loading = result === null || result.date !== date
    const data = !loading ? result.data : null

    function pickDate(e) {
        const v = e.target.value
        if (v && v <= today) setDate(v)      // ignore cleared input and future days
    }

    return (
        <section className = "rw">
            <h2>Daily rewind</h2>

            <div className = "rw-controls">
                <button className = "hp-button gray" onClick = {() => setDate(shiftDay(date, -1))}>
                    &lsaquo; Previous
                </button>
                <input type = "date" value = {date} max = {today} onChange = {pickDate}
                       aria-label = "Rewind date" />
                <button className = "hp-button gray" disabled = {date >= today}
                        onClick = {() => setDate(shiftDay(date, 1))}>
                    Next &rsaquo;
                </button>
                {date !== today && (
                    <button className = "hp-button" onClick = {() => setDate(today)}>Today</button>
                )}
            </div>

            <p className = "rw-date">{prettyDate(date)} <span className = "rw-tz">({TZ})</span></p>

            {loading && <p>Loading...</p>}
            {!loading && result.error && <p className = "errorMessage">{result.error}</p>}

            {data && data.connected === false && (
                <p>Connect your Spotify account to see your rewind.</p>
            )}

            {data && data.connected && data.total_plays === 0 && (
                <p className = "rw-empty">No listening recorded for this day.</p>
            )}

            {data && data.connected && data.total_plays > 0 && (
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
                        <RankCard title = "Moods" emptyText = "No mood data yet."
                            rows = {(data.top_moods || []).map((m) => ({
                                key: m.mood, primary: capitalize(m.mood),
                                secondary: `${Math.round(m.share * 100)}%`, plays: m.plays }))} />
                    </div>
                </>
            )}
        </section>
    )
}

export default Rewind
