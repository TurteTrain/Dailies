import { useEffect, useState } from 'react'
import { api } from '../api.js'
import Rewind from '../rewind/Rewind.jsx'
import UsernameInvites, { FriendMark } from './UsernameInvites.jsx'
import './groups.css'

const plural = (n) => `${n} ${n === 1 ? 'member' : 'members'}`

// One group: its combined rewind (with the same day-by-day browsing as a personal dashboard),
// who is in it, and the owner's / members' actions. Owners can invite and delete; everyone else
// can only leave.
const GroupDashboard = ({ group, friends, onBack, onChanged }) => {
    const [detail, setDetail] = useState(null)
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    const [invitees, setInvitees] = useState([])
    const [busy, setBusy] = useState(false)

    useEffect(() => {
        api(`groups/${group.id}`).then(setDetail).catch((e) => setError(e.message))
    }, [group.id])

    async function sendInvites(e) {
        e.preventDefault()
        if (invitees.length === 0) { setError('Add at least one username.'); return }
        setBusy(true); setError(''); setNotice('')
        try {
            const res = await api(`groups/${group.id}/invite`, { method: 'POST', body: { usernames: invitees } })
            setDetail(res.group)
            setInvitees([])
            const parts = []
            if (res.invited.length) parts.push(`Invited ${res.invited.join(', ')}.`)
            if (res.skipped.length) parts.push(`Already in the group or invited: ${res.skipped.join(', ')}.`)
            setNotice(parts.join(' ') || 'Nobody new to invite.')
        } catch (err) {
            setError(err.message)
        } finally {
            setBusy(false)
        }
    }

    async function leave() {
        if (!window.confirm(`Leave "${group.name}"?\n---\nYou'll stop contributing to this group's rewind. You can only rejoin if the owner invites you again.\n---`)) return
        setBusy(true); setError('')
        try {
            await api(`groups/${group.id}/leave`, { method: 'POST' })
            onChanged()
            onBack()
        } catch (err) {
            setError(err.message)
            setBusy(false)
        }
    }

    async function deleteGroup() {
        if (!window.confirm(`Delete "${group.name}"?\n---\nThis removes the group for everyone in it and CANNOT BE UNDONE.\n---`)) return
        setBusy(true); setError('')
        try {
            await api(`groups/${group.id}`, { method: 'DELETE' })
            onChanged()
            onBack()
        } catch (err) {
            setError(err.message)
            setBusy(false)
        }
    }

    // Don't suggest friends who are already in the group or already invited
    const taken = new Set(detail ? [...detail.members, ...(detail.pending || [])].map((m) => m.username.toLowerCase()) : [])
    const inviteFriends = friends.filter((f) => !taken.has(f.username.toLowerCase()))

    const isOwner = detail ? detail.is_owner : group.is_owner
    const count = detail ? detail.member_count : group.member_count

    return (
        <div className = "hp-container">
            <div className = "hp-bar">
                <div className = "gr-head">
                    <h2>{group.name}</h2>
                    <p className = "gr-sub">{plural(count)}</p>
                </div>
                <button className = "hp-button gray gr-back" onClick = {onBack}>&lsaquo; Back to groups</button>
            </div>

            {error && <p className = "errorMessage" role = "alert">{error}</p>}
            {notice && <p className = "fr-notice" role = "status">{notice}</p>}

            <section className = "hp-section">
                <Rewind endpoint = {`groups/${group.id}/rewind`} title = "Group rewind" />
            </section>

            {detail && (
                <section className = "hp-section">
                    <h2>Members</h2>
                    <ul className = "fr-list gr-members">
                        {detail.members.map((m) => (
                            <li key = {m.user_id}>
                                <span className = "fr-name"><FriendMark show = {m.is_friend} />{m.username}</span>
                                {m.is_owner && <span className = "gr-owner">Owner</span>}
                            </li>
                        ))}
                        {(detail.pending || []).map((m) => (
                            <li key = {`p${m.user_id}`} className = "gr-pending">
                                <span className = "fr-name"><FriendMark show = {m.is_friend} />{m.username}</span>
                                <span className = "fr-wait">Invited</span>
                            </li>
                        ))}
                    </ul>

                    {isOwner && (
                        <form onSubmit = {sendInvites} className = "gr-form">
                            <h3>Invite more people</h3>
                            <UsernameInvites names = {invitees} onChange = {(n) => { setInvitees(n); setError('') }}
                                             friends = {inviteFriends} disabled = {busy} />
                            <button type = "submit" className = "hp-button" disabled = {busy}>Send invites</button>
                        </form>
                    )}
                </section>
            )}

            <div className = "hp-footer">
                {isOwner ? (
                    <button className = "hp-button delete" disabled = {busy} onClick = {deleteGroup}>Delete group</button>
                ) : (
                    <button className = "hp-button delete" disabled = {busy} onClick = {leave}>Leave group</button>
                )}
            </div>
        </div>
    )
}

export default GroupDashboard
