import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import Friends from './Friends.jsx'
import Homepage from '../homepage/homepage.jsx'

const EMPTY = { friends: [], incoming: [], outgoing: [] }
const person = (id, username) => ({ id, user_id: id + 100, username })

let state, calls
beforeEach(() => {
  state = { ...EMPTY }
  calls = []
  document.cookie = 'csrftoken=test'
  globalThis.fetch = vi.fn(async (url, opts = {}) => {
    const method = opts.method || 'GET'
    const body = opts.body ? JSON.parse(opts.body) : null
    calls.push({ url: String(url), method, body })
    if (String(url) === '/api/friends/request') {
      if (body.username === 'nobody') return { ok: false, status: 404, json: async () => ({ error: 'No user named nobody.' }) }
      state = { ...state, outgoing: [person(1, body.username)] }
      return { ok: true, status: 201, json: async () => ({ status: 'pending', ...state }) }
    }
    if (String(url) === '/api/friends/accept') {
      state = { friends: [...state.friends, ...state.incoming], incoming: [], outgoing: state.outgoing }
      return { ok: true, status: 200, json: async () => state }
    }
    if (String(url) === '/api/friends') return { ok: true, status: 200, json: async () => state }
    return { ok: true, status: 200, json: async () => ({ connected: false }) }
  })
})
afterEach(cleanup)

test('shows friends, incoming and sent requests', async () => {
  state = { friends: [person(1, 'alice')], incoming: [person(2, 'bob')], outgoing: [person(3, 'cara')] }
  render(<Friends onBack = {() => {}} />)
  expect(await screen.findByText('alice')).toBeTruthy()
  expect(screen.getByText('bob')).toBeTruthy()
  expect(screen.getByText('cara')).toBeTruthy()
  expect(screen.getByText('Waiting')).toBeTruthy()
})

test('shows empty states', async () => {
  render(<Friends onBack = {() => {}} />)
  expect(await screen.findByText(/No friends yet/)).toBeTruthy()
  expect(screen.getByText('No pending requests.')).toBeTruthy()
})

test('sending a request posts the username and lists it as sent', async () => {
  render(<Friends onBack = {() => {}} />)
  await screen.findByText(/No friends yet/)
  fireEvent.change(screen.getByLabelText("Friend's username"), { target: { value: '  dana ' } })
  fireEvent.click(screen.getByText('Send request'))
  expect(await screen.findByText('Friend request sent to dana.')).toBeTruthy()
  const post = calls.find((c) => c.url === '/api/friends/request')
  expect(post.method).toBe('POST')
  expect(post.body).toEqual({ username: 'dana' })
  expect(screen.getByText('dana')).toBeTruthy()
  expect(screen.getByLabelText("Friend's username").value).toBe('')
})

test('an unknown username shows the server error', async () => {
  render(<Friends onBack = {() => {}} />)
  await screen.findByText(/No friends yet/)
  fireEvent.change(screen.getByLabelText("Friend's username"), { target: { value: 'nobody' } })
  fireEvent.click(screen.getByText('Send request'))
  expect((await screen.findByRole('alert')).textContent).toBe('No user named nobody.')
})

test('an empty username is rejected without calling the server', async () => {
  render(<Friends onBack = {() => {}} />)
  await screen.findByText(/No friends yet/)
  fireEvent.click(screen.getByText('Send request'))
  expect((await screen.findByRole('alert')).textContent).toBe('Enter a username.')
  expect(calls.some((c) => c.url === '/api/friends/request')).toBe(false)
})

test('accepting a request moves that person into Your friends', async () => {
  state = { friends: [], incoming: [person(7, 'bob')], outgoing: [] }
  render(<Friends onBack = {() => {}} />)
  fireEvent.click(await screen.findByLabelText('Accept bob'))
  expect(await screen.findByText('You and bob are now friends!')).toBeTruthy()
  expect(calls.find((c) => c.url === '/api/friends/accept').body).toEqual({ request_id: 7 })
  expect(screen.queryByLabelText('Accept bob')).toBeNull()
  expect(screen.getByText('No pending requests.')).toBeTruthy()
})

test('back button calls onBack', async () => {
  const onBack = vi.fn()
  render(<Friends onBack = {onBack} />)
  await screen.findByText(/No friends yet/)
  fireEvent.click(screen.getByText(/Back to dashboard/))
  expect(onBack).toHaveBeenCalled()
})

test('dashboard has a Friends button with a pending badge that opens the friends view', async () => {
  state = { friends: [], incoming: [person(2, 'bob'), person(3, 'cara')], outgoing: [] }
  const user = { id: 1, username: 'me', is_staff: false, spotify_connected: false }
  render(<Homepage user = {user} onLogout = {() => {}} onUserDeletion = {() => {}} onAdminDeletion = {() => {}} />)
  const badge = await screen.findByLabelText('2 pending requests')
  expect(badge.textContent).toBe('2')
  fireEvent.click(screen.getByText(/^Friends/))
  expect(await screen.findByText('Your friends')).toBeTruthy()
  fireEvent.click(screen.getByText(/Back to dashboard/))
  expect(await screen.findByText('Your listening history')).toBeTruthy()
})

const DAY = {
  connected: true, username: 'alice', date: '2026-11-14', timezone: 'UTC', total_plays: 4, approx_minutes: 12,
  top_tracks: [{ track_id: 't1', name: 'Late Library', artist: 'Quiet Hours', plays: 3 }],
  top_artists: [{ artist_id: 'a1', name: 'Quiet Hours', plays: 3 }],
  top_genres: [{ genre: 'lo-fi', plays: 3 }],
  mood_of_the_day: 'calm',
}

async function openAlice(dayBody = DAY, status = 200) {
  state = { friends: [person(1, 'alice')], incoming: [], outgoing: [] }
  const base = globalThis.fetch
  globalThis.fetch = vi.fn(async (url, opts) => {
    if (String(url).startsWith('/api/friends/101/rewind'))
      { calls.push({ url: String(url), method: 'GET' }); return { ok: status < 400, status, json: async () => dayBody } }
    return base(url, opts)
  })
  render(<Friends onBack = {() => {}} />)
  fireEvent.click(await screen.findByLabelText("View alice's dashboard"))
}

test("viewing a friend shows today's top songs, artists, genres and mood", async () => {
  await openAlice()
  expect(await screen.findByText('Late Library')).toBeTruthy()
  expect(screen.getByText("alice\u2019s dashboard")).toBeTruthy()
  expect(screen.getByText('Top songs')).toBeTruthy()
  expect(screen.getByText('Top artists')).toBeTruthy()
  expect(screen.getByText('Top genres')).toBeTruthy()
  expect(screen.getByText('Calm')).toBeTruthy()
  expect(screen.getByText('mood of the day')).toBeTruthy()
  const url = calls.find((c) => c.url.startsWith('/api/friends/101/rewind')).url
  expect(url).toContain('tz=')
  expect(url).not.toContain('date=')
})

test("a friend's dashboard is read-only: no date controls, history or account actions", async () => {
  await openAlice()
  await screen.findByText('Late Library')
  expect(screen.queryByLabelText('Rewind date')).toBeNull()
  expect(screen.queryByText(/Previous/)).toBeNull()
  expect(screen.queryByText(/Next/)).toBeNull()
  expect(screen.queryByText(/Delete/i)).toBeNull()
  expect(screen.queryByText(/Log out/i)).toBeNull()
  expect(screen.queryByText('Send request')).toBeNull()
  expect(screen.queryByText('Accept')).toBeNull()
  expect(screen.queryByText(/Remove|Unfriend/i)).toBeNull()
  expect(screen.queryByRole('table')).toBeNull()
  expect(screen.queryByText('Moods')).toBeNull()
  // the only buttons are the way back
  expect(screen.getAllByRole('button').map((b) => b.textContent)).toEqual(['\u2039 Back to friends'])
})

test('friend with no listening today and friend without Spotify show friendly messages', async () => {
  await openAlice({ ...DAY, total_plays: 0, top_tracks: [], top_artists: [], top_genres: [] })
  expect(await screen.findByText(/hasn.t listened to anything today/)).toBeTruthy()
  cleanup()
  await openAlice({ connected: false, username: 'alice' })
  expect(await screen.findByText(/hasn.t connected Spotify yet/)).toBeTruthy()
})

test('server errors are shown and back returns to the friends list', async () => {
  await openAlice({ error: 'Friend not found.' }, 404)
  expect((await screen.findByRole('alert')).textContent).toBe('Friend not found.')
  fireEvent.click(screen.getByText(/Back to friends/))
  expect(await screen.findByText('Your friends')).toBeTruthy()
})
