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
