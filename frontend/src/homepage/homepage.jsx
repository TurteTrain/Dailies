import { useEffect, useState } from 'react'
import { api } from '../api.js'
import Rewind from '../rewind/Rewind.jsx'
import './homepage.css'

const Homepage = ({ user, onLogout, onUserDeletion }) => {

    const [data, setData] = useState(null);          // {connected, total, listens: [...]}
    const [adminUsers, setAdminUsers] = useState(null);
    const [error, setError] = useState('');

    useEffect(() => {
        api('listens').then(setData).catch((e) => setError(e.message));
        if (user.is_staff) {
            api('admin/users').then(setAdminUsers).catch((e) => setError(e.message));
        }
    }, [user.is_staff]);

    //popup to confirm account deletion
    function deletePopup(){
        const confirm = window.confirm(
            "Are you sure you want to delete your account?\n"
            + "---\n"
            + "This will delete your song history stored by Dailies.\n"
            + "To use Dailies again another account will\n"
            + "have to be created and linked to Spotify.\n"
            + "---"
        )
        if(confirm){
            //call delete function
            onUserDeletion();
        }
    }

    return (
        <div className = "hp-container">
            <div className = "hp-bar">
                <h2>Signed in as {user.username}{user.is_staff ? " (admin)" : ""}</h2>
                <button className = "hp-button gray" onClick = {onLogout}>Log out</button>
            </div>

            {error && <p className = "errorMessage">{error}</p>}

            {/* The rewind only makes sense once Spotify is connected */}
            {data && data.connected && (
                <section className = "hp-section">
                    <Rewind />
                </section>
            )}

            <section className = "hp-section">
                <h2>Your listening history</h2>
                {data === null && !error && <p>Loading...</p>}

                {data && !data.connected && (
                    <>
                        <p>Connect your Spotify account to start collecting your history.</p>
                        {/* A normal link (not fetch): the browser must follow the redirect to Spotify */}
                        <a className = "hp-button" href = "/spotify/login">Connect Spotify</a>
                    </>
                )}

                {data && data.connected && (
                    <>
                        <p>{data.total} plays stored (newest {data.listens.length} shown)</p>
                        <div className = "hp-scroll">
                            <table className = "hp-table">
                                <thead>
                                    <tr><th>Played at</th><th>Track</th><th>Artist</th></tr>
                                </thead>
                                <tbody>
                                    {data.listens.map((l, i) => (
                                        <tr key = {i}>
                                            <td>{new Date(l.played_at).toLocaleString()}</td>
                                            <td>{l.track}</td>
                                            <td>{l.artist}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </>
                )}
            </section>

            {user.is_staff && (
                <section className = "hp-section">
                    <h2>Admin: all users</h2>
                    {adminUsers === null && !error && <p>Loading...</p>}
                    {adminUsers && (
                        <table className = "hp-table">
                            <thead>
                                <tr><th>ID</th><th>Username</th><th>Admin</th><th>Spotify</th><th>Listens</th></tr>
                            </thead>
                            <tbody>
                                {adminUsers.map((u) => (
                                    <tr key = {u.id}>
                                        <td>{u.id}</td>
                                        <td>{u.username}</td>
                                        <td>{u.is_staff ? "yes" : "no"}</td>
                                        <td>{u.spotify_connected ? "connected" : "-"}</td>
                                        <td>{u.listen_count}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </section>
            )}
            <div className = "hp-footer">
                <button className = "hp-button delete" onClick = {deletePopup}>Delete Account</button>
            </div>
        </div>
    );

}

export default Homepage;
