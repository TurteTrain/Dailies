// Thin wrapper around fetch for the Django API.
// Paths are relative (/api/...), so in development the Vite proxy forwards them to Django.

function getCookie(name) {
    const match = document.cookie.split('; ').find((row) => row.startsWith(name + '='))
    return match ? decodeURIComponent(match.split('=')[1]) : ''
}

export async function api(path, { method = 'GET', body } = {}) {
    // Django needs a CSRF cookie before any POST. Fetch one if we don't have it yet.
    if (method !== 'GET' && !getCookie('csrftoken')) {
        await fetch('/api/csrf', { credentials: 'include' })
    }

    const res = await fetch(`/api/${path}`, {
        method,
        credentials: 'include', // send/receive the Django session cookie
        headers: {
            'Content-Type': 'application/json',
            // Read the cookie on every request: Django rotates the token after login.
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: body ? JSON.stringify(body) : undefined,
    })

    const data = res.status === 204 ? null : await res.json().catch(() => null)
    if (!res.ok) {
        const err = new Error(data?.error ?? data?.detail ?? `Request failed (${res.status})`)
        err.status = res.status
        throw err
    }
    return data
}
