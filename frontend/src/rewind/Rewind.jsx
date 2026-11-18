import { useEffect, useState } from 'react'
import { api } from '../api.js'
import './rewind.css'
import { RewindSummary } from './RewindSummary.jsx'

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
const prettyDate = (iso) =>
    fromISO(iso).toLocaleDateString(undefined, {
        weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
    })

// `endpoint` lets the same component show a group's rewind (e.g. 'groups/3/rewind').
const Rewind = ({ endpoint = 'rewind', title = 'Daily rewind' }) => {
    const today = toISO(new Date())
    const [date, setDate] = useState(today)
    const [result, setResult] = useState(null)   // {date, data} or {date, error}

    // Re-fetch whenever the chosen day changes. The "ignore" flag drops answers that arrive
    // after the user has already clicked to another day.
    useEffect(() => {
        let ignore = false
        api(`${endpoint}?date=${date}&tz=${encodeURIComponent(TZ)}`)
            .then((data) => { if (!ignore) setResult({ date, data }) })
            .catch((e) => { if (!ignore) setResult({ date, error: e.message }) })
        return () => { ignore = true }
    }, [date, endpoint])

    const loading = result === null || result.date !== date
    const data = !loading ? result.data : null

    function pickDate(e) {
        const v = e.target.value
        if (v && v <= today) setDate(v)      // ignore cleared input and future days
    }

    return (
        <section className = "rw">
            <h2>{title}</h2>

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

            {data && data.connected && data.total_plays > 0 && <RewindSummary data = {data} />}
        </section>
    )
}

export default Rewind
