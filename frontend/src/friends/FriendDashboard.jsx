import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { RewindSummary } from '../rewind/RewindSummary.jsx'
import '../rewind/rewind.css'

const TZ = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

// Read-only look at a friend's day. There is intentionally nothing to click here except "back":
// no date picker (the server only ever returns today), no listening history, no account actions.
const FriendDashboard = ({ friend, onBack }) => {
    const [result, setResult] = useState(null)      // {data} or {error}

    useEffect(() => {
        let ignore = false
        api(`friends/${friend.user_id}/rewind?tz=${encodeURIComponent(TZ)}`)
            .then((data) => { if (!ignore) setResult({ data }) })
            .catch((e) => { if (!ignore) setResult({ error: e.message }) })
        return () => { ignore = true }
    }, [friend.user_id])

    const data = result && result.data
    const today = new Date().toLocaleDateString(undefined, {
        weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })

    return (
        <div className = "hp-container">
            <div className = "hp-bar">
                <h2>{friend.username}&rsquo;s dashboard</h2>
                <button className = "hp-button gray" onClick = {onBack}>&lsaquo; Back to friends</button>
            </div>

            <section className = "rw">
                <h2>Today&rsquo;s rewind</h2>
                <p className = "rw-date">{today} <span className = "rw-tz">({TZ})</span></p>

                {result === null && <p>Loading...</p>}
                {result && result.error && <p className = "errorMessage" role = "alert">{result.error}</p>}
                {data && data.connected === false && (
                    <p className = "rw-empty">{friend.username} hasn&rsquo;t connected Spotify yet.</p>
                )}
                {data && data.connected && data.total_plays === 0 && (
                    <p className = "rw-empty">{friend.username} hasn&rsquo;t listened to anything today.</p>
                )}
                {data && data.connected && data.total_plays > 0 && (
                    <RewindSummary data = {data} showMoodBreakdown = {false} />
                )}
            </section>
        </div>
    )
}

export default FriendDashboard
