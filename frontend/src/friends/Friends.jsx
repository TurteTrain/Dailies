import { useEffect, useState } from 'react'
import { api } from '../api.js'
import './friends.css'

// One list of people. `action` (optional) renders a button for each row.
function PeopleList({ title, people, emptyText, action }) {
    return (
        <section className = "fr-card">
            <h3>{title} <span className = "fr-count">{people.length}</span></h3>
            {people.length === 0 ? (
                <p className = "rw-empty">{emptyText}</p>
            ) : (
                <ul className = "fr-list">
                    {people.map((p) => (
                        <li key = {p.id}>
                            <span className = "fr-name">{p.username}</span>
                            {action && action(p)}
                        </li>
                    ))}
                </ul>
            )}
        </section>
    )
}

const Friends = ({ onBack }) => {
    const [data, setData] = useState(null)        // {friends, incoming, outgoing}
    const [error, setError] = useState('')
    const [username, setUsername] = useState('')
    const [notice, setNotice] = useState('')
    const [busy, setBusy] = useState(false)

    useEffect(() => {
        api('friends').then(setData).catch((e) => setError(e.message))
    }, [])

    async function sendRequest(e) {
        e.preventDefault()
        const name = username.trim()
        if (!name) { setError('Enter a username.'); return }
        setBusy(true); setError(''); setNotice('')
        try {
            const res = await api('friends/request', { method: 'POST', body: { username: name } })
            setData(res)
            setUsername('')
            setNotice(res.status === 'accepted'
                ? `You and ${name} are now friends!`
                : `Friend request sent to ${name}.`)
        } catch (err) {
            setError(err.message)
        } finally {
            setBusy(false)
        }
    }

    async function accept(p) {
        setBusy(true); setError(''); setNotice('')
        try {
            setData(await api('friends/accept', { method: 'POST', body: { request_id: p.id } }))
            setNotice(`You and ${p.username} are now friends!`)
        } catch (err) {
            setError(err.message)
            api('friends').then(setData).catch(() => {})      // the request may be gone: resync
        } finally {
            setBusy(false)
        }
    }

    return (
        <div className = "hp-container">
            <div className = "hp-bar">
                <h2>Friends</h2>
                <button className = "hp-button gray" onClick = {onBack}>&lsaquo; Back to dashboard</button>
            </div>

            <form className = "fr-add" onSubmit = {sendRequest}>
                <input type = "text" placeholder = "Add a friend by username" aria-label = "Friend's username"
                       value = {username} autoComplete = "off"
                       onChange = {(e) => { setUsername(e.target.value); setError(''); setNotice('') }} />
                <button type = "submit" className = "hp-button" disabled = {busy}>Send request</button>
            </form>

            {error && <p className = "errorMessage" role = "alert">{error}</p>}
            {notice && <p className = "fr-notice" role = "status">{notice}</p>}
            {data === null && !error && <p>Loading...</p>}

            {data && (
                <div className = "fr-grid">
                    <PeopleList title = "Friend requests" people = {data.incoming}
                        emptyText = "No pending requests."
                        action = {(p) => (
                            <button className = "hp-button fr-small" disabled = {busy}
                                    aria-label = {`Accept ${p.username}`}
                                    onClick = {() => accept(p)}>Accept</button>
                        )} />
                    <PeopleList title = "Your friends" people = {data.friends}
                        emptyText = "No friends yet. Send a request above!" />
                    <PeopleList title = "Sent requests" people = {data.outgoing}
                        emptyText = "No requests waiting on a reply."
                        action = {() => <span className = "fr-wait">Waiting</span>} />
                </div>
            )}
        </div>
    )
}

export default Friends
