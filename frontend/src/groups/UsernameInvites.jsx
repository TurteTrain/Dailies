import { useState } from 'react'

// Friends get a star so the owner can tell at a glance who they already know.
export const FRIEND_ICON = '\u2605'

export function FriendMark({ show }) {
    if (!show) return null
    return <span className = "gr-friend" title = "Your friend" aria-label = "friend">{FRIEND_ICON}</span>
}

// Collects usernames as removable chips. Typing a username and pressing Enter / comma / "Add"
// adds it; the owner's friends are also offered as one-tap suggestions. Friend chips are marked.
// Controlled: the parent owns `names` and gets changes through `onChange`.
const UsernameInvites = ({ names, onChange, friends, disabled = false }) => {
    const [text, setText] = useState('')
    const friendSet = new Set(friends.map((f) => f.username.toLowerCase()))
    const has = (n) => names.some((x) => x.toLowerCase() === n.toLowerCase())

    function add(raw) {
        const toAdd = raw.split(/[,\s]+/).map((n) => n.trim()).filter((n) => n && !has(n))
        if (toAdd.length) onChange([...names, ...toAdd.filter((n, i) => toAdd.findIndex((x) => x.toLowerCase() === n.toLowerCase()) === i)])
        setText('')
    }

    function onKeyDown(e) {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault()
            add(text)
        } else if (e.key === 'Backspace' && !text && names.length) {
            onChange(names.slice(0, -1))
        }
    }

    const suggestions = friends.filter((f) => !has(f.username))

    return (
        <div className = "gr-invites">
            <div className = "gr-chips" aria-label = "People to invite">
                {names.map((n) => (
                    <span key = {n} className = {`gr-chip${friendSet.has(n.toLowerCase()) ? ' friend' : ''}`}>
                        <FriendMark show = {friendSet.has(n.toLowerCase())} />
                        {n}
                        <button type = "button" className = "gr-x" aria-label = {`Remove ${n}`} disabled = {disabled}
                                onClick = {() => onChange(names.filter((x) => x !== n))}>&times;</button>
                    </span>
                ))}
            </div>
            <div className = "gr-add-row">
                <input type = "text" placeholder = "Invite by username" aria-label = "Invite by username"
                       value = {text} autoComplete = "off" disabled = {disabled}
                       onChange = {(e) => setText(e.target.value)} onKeyDown = {onKeyDown} />
                <button type = "button" className = "hp-button gray" disabled = {disabled || !text.trim()}
                        onClick = {() => add(text)}>Add</button>
            </div>
            {suggestions.length > 0 && (
                <div className = "gr-suggest">
                    <span className = "gr-suggest-label">Your friends:</span>
                    {suggestions.map((f) => (
                        <button type = "button" key = {f.user_id} className = "gr-chip friend suggest" disabled = {disabled}
                                aria-label = {`Add friend ${f.username}`}
                                onClick = {() => onChange([...names, f.username])}>
                            <FriendMark show />{f.username}<span className = "gr-plus">+</span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}

export default UsernameInvites
