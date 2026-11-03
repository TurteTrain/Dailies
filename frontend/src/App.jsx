import { useEffect, useState } from 'react'

import Login from './loginPage/login.jsx'
import Homepage from './homepage/homepage.jsx'
import { api } from './api.js'
import './App.css'

function App() {
    // user is the object returned by Django: {id, username, is_staff, spotify_connected}
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)

    // On page load, ask Django whether a session already exists (keeps you logged in on refresh,
    // and after returning from the Spotify login redirect).
    useEffect(() => {
        async function restoreSession() {
            try {
                await api('csrf')
                setUser(await api('me'))
            } catch {
                setUser(null) // 401/403 just means "not logged in"
            } finally {
                setLoading(false)
            }
        }
        restoreSession()
    }, [])

    async function logout() {
        try {
            await api('logout', { method: 'POST' })
        } finally {
            setUser(null)
        }
    }

    async function userDeletion(){
        try{
            await api('delete_user', { method: 'DELETE' })
            setUser(null)
        } catch(e){
            window.alert("Account Deletion Failed: " + e.message)
        }
    }

    async function adminDeletion(u){
        try{
            await api('delete_admin', {method: 'DELETE', body: {user_id: u.id}})
        } catch(e){
            window.alert("Account Deletion Failed: " + e.message)
        }
    }

    if (loading) {
        return <div className="container"><p>Loading...</p></div>
    }

    return (
        <div>
            {user ? <Homepage user={user} onLogout={logout} onUserDeletion={userDeletion} onAdminDeletion={adminDeletion} /> : <Login onSuccess={setUser} />}
        </div>
    )
}

export default App
