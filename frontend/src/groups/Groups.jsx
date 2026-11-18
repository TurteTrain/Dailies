import { useEffect, useState } from 'react'
import { api } from '../api.js'
import GroupDashboard from './GroupDashboard.jsx'
import UsernameInvites from './UsernameInvites.jsx'
import '../friends/friends.css'
import './groups.css'

const plural = (n) => `${n} ${n === 1 ? 'member' : 'members'}`

// The list of groups you're in, invitations waiting for you, and the "create a group" form.
const Groups = ({ onBack }) => {
    const [data, setData] = useState(null)          // {groups, invites}
    const [friends, setFriends] = useState([])      // accepted friends, used to mark/suggest invitees
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    const [busy, setBusy] = useState(false)
    const [creating, setCreating] = useState(false)
    const [name, setName] = useState('')
    const [invitees, setInvitees] = useState([])
    const [viewing, setViewing] = useState(null)    // the group whose dashboard is open

    function reload() {
        api('groups').then(setData).catch((e) => setError(e.message))
    }

    useEffect(() => {
        reload()
        api('friends').then((d) => setFriends(d.friends)).catch(() => {})
    }, [])

    async function create(e) {
        e.preventDefault()
        if (!name.trim()) { setError('Give your group a name.'); return }
        setBusy(true); setError(''); setNotice('')
        try {
            const g = await api('groups', { method: 'POST', body: { name: name.trim(), usernames: invitees } })
            setName(''); setInvitees([]); setCreating(false)
            reload()
            setViewing({ id: g.id, name: g.name, member_count: g.member_count, is_owner: true })
        } catch (err) {
            setError(err.message)
        } finally {
            setBusy(false)
        }
    }

    async function answer(invite, action) {
        setBusy(true); setError(''); setNotice('')
        try {
            setData(await api(`groups/invites/${action}`, { method: 'POST', body: { invite_id: invite.id } }))
            setNotice(action === 'accept' ? `You joined ${invite.group_name}.` : `Declined ${invite.group_name}.`)
        } catch (err) {
            setError(err.message)
            reload()
        } finally {
            setBusy(false)
        }
    }

    if (viewing) {
        return <GroupDashboard group = {viewing} friends = {friends} onChanged = {reload}
                               onBack = {() => { setViewing(null); reload() }} />
    }

    return (
        <div className = "hp-container">
            <div className = "hp-bar">
                <h2>Groups</h2>
                <div className = "hp-actions">
                    <button className = "hp-button" onClick = {() => { setCreating(!creating); setError('') }}>
                        {creating ? 'Cancel' : 'Create group'}
                    </button>
                    <button className = "hp-button gray" onClick = {onBack}>&lsaquo; Back to dashboard</button>
                </div>
            </div>

            {creating && (
                <form className = "gr-form fr-card" onSubmit = {create}>
                    <h3>New group</h3>
                    <input type = "text" placeholder = "Group name" aria-label = "Group name" maxLength = {50}
                           value = {name} autoComplete = "off" disabled = {busy}
                           onChange = {(e) => { setName(e.target.value); setError('') }} />
                    <p className = "gr-hint">You join automatically. Everyone you invite has to accept first.</p>
                    <UsernameInvites names = {invitees} onChange = {(n) => { setInvitees(n); setError('') }}
                                     friends = {friends} disabled = {busy} />
                    <button type = "submit" className = "hp-button" disabled = {busy}>Create group</button>
                </form>
            )}

            {error && <p className = "errorMessage" role = "alert">{error}</p>}
            {notice && <p className = "fr-notice" role = "status">{notice}</p>}
            {data === null && !error && <p>Loading...</p>}

            {data && (
                <div className = "fr-grid">
                    {data.invites.length > 0 && (
                        <section className = "fr-card gr-wide">
                            <h3>Invitations <span className = "fr-count">{data.invites.length}</span></h3>
                            <ul className = "fr-list">
                                {data.invites.map((i) => (
                                    <li key = {i.id} className = "gr-row">
                                        <span className = "gr-info">
                                            <span className = "gr-title">{i.group_name}</span>
                                            {i.invited_by && <span className = "gr-meta">Invited by {i.invited_by}</span>}
                                        </span>
                                        <span className = "gr-btns">
                                            <button className = "hp-button fr-small" disabled = {busy}
                                                    aria-label = {`Accept invite to ${i.group_name}`}
                                                    onClick = {() => answer(i, 'accept')}>Accept</button>
                                            <button className = "hp-button gray fr-small" disabled = {busy}
                                                    aria-label = {`Decline invite to ${i.group_name}`}
                                                    onClick = {() => answer(i, 'decline')}>Decline</button>
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </section>
                    )}

                    <section className = "fr-card gr-wide">
                        <h3>Your groups <span className = "fr-count">{data.groups.length}</span></h3>
                        {data.groups.length === 0 ? (
                            <p className = "rw-empty">You're not in any groups yet. Create one above!</p>
                        ) : (
                            <ul className = "fr-list">
                                {data.groups.map((g) => (
                                    <li key = {g.id} className = "gr-row">
                                        <span className = "gr-info">
                                            <span className = "gr-title">{g.name}</span>
                                            <span className = "gr-meta">
                                                {plural(g.member_count)}
                                                {g.is_owner && <span className = "gr-owner">Owner</span>}
                                            </span>
                                        </span>
                                        <button className = "hp-button fr-small" aria-label = {`Open ${g.name}`}
                                                onClick = {() => setViewing(g)}>Open</button>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>
                </div>
            )}
        </div>
    )
}

export default Groups
