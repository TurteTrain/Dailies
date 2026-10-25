import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import Rewind from './Rewind.jsx'

const pad = (n) => String(n).padStart(2, '0')
const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const today = iso(new Date())
const yesterday = (() => { const d = new Date(); d.setDate(d.getDate() - 1); return iso(d) })()

const FULL = {
  connected: true, date: today, timezone: 'UTC', total_plays: 6, approx_minutes: 18,
  top_tracks: [{ track_id: 't1', name: 'Late Library', artist: 'Quiet Hours', plays: 3 },
               { track_id: 't2', name: 'Cold Brew', artist: 'Morning Shift', plays: 2 }],
  top_artists: [{ artist_id: 'a1', name: 'Quiet Hours', plays: 3 }],
  top_genres: [{ genre: 'lo-fi', plays: 5 }],
}
const EMPTY = { connected: true, total_plays: 0, approx_minutes: 0, top_tracks: [], top_artists: [], top_genres: [] }

let responder
beforeEach(() => {
  responder = vi.fn(() => ({ status: 200, body: FULL }))
  globalThis.fetch = vi.fn(async (url) => {
    const { status, body } = responder(String(url))
    return { ok: status < 400, status, json: async () => body }
  })
})
afterEach(cleanup)

test('loads today by default and shows stats and all three lists', async () => {
  render(<Rewind />)
  expect(screen.getByText('Loading...')).toBeTruthy()
  expect(await screen.findByText('Late Library')).toBeTruthy()
  const url = globalThis.fetch.mock.calls[0][0]
  expect(url).toContain(`/api/rewind?date=${today}&tz=`)
  expect(screen.getByText('6')).toBeTruthy()
  expect(screen.getByText('~18')).toBeTruthy()
  expect(screen.getByText('lo-fi')).toBeTruthy()
  expect(screen.getByText('Top artists')).toBeTruthy()
})

test('Previous requests the day before; Next is disabled on today; Today button appears', async () => {
  render(<Rewind />)
  await screen.findByText('Late Library')
  expect(screen.getByText(/Next/).closest('button').disabled).toBe(true)
  expect(screen.queryByText('Today')).toBeNull()
  fireEvent.click(screen.getByText(/Previous/))
  await waitFor(() => expect(globalThis.fetch.mock.calls.at(-1)[0]).toContain(`date=${yesterday}`))
  await screen.findByText('Late Library')
  expect(screen.getByText(/Next/).closest('button').disabled).toBe(false)
  fireEvent.click(screen.getByText('Today'))
  await waitFor(() => expect(globalThis.fetch.mock.calls.at(-1)[0]).toContain(`date=${today}`))
})

test('picking a date in the input fetches that date; future dates are ignored', async () => {
  render(<Rewind />)
  await screen.findByText('Late Library')
  const input = screen.getByLabelText('Rewind date')
  fireEvent.change(input, { target: { value: '2026-01-05' } })
  await waitFor(() => expect(globalThis.fetch.mock.calls.at(-1)[0]).toContain('date=2026-01-05'))
  const calls = globalThis.fetch.mock.calls.length
  fireEvent.change(input, { target: { value: '2999-01-01' } })
  expect(globalThis.fetch.mock.calls.length).toBe(calls)
})

test('shows a friendly message for a day with no plays', async () => {
  responder.mockReturnValue({ status: 200, body: EMPTY })
  render(<Rewind />)
  expect(await screen.findByText('No listening recorded for this day.')).toBeTruthy()
  expect(screen.queryByText('Top songs')).toBeNull()
})

test('shows empty-genre and empty-artist messages when that data is missing', async () => {
  responder.mockReturnValue({ status: 200, body: { ...FULL, top_artists: [], top_genres: [] } })
  render(<Rewind />)
  expect(await screen.findByText('No genre data yet.')).toBeTruthy()
  expect(screen.getByText('No artist data for this day yet.')).toBeTruthy()
})

test('shows the server error message on a 400', async () => {
  responder.mockReturnValue({ status: 400, body: { error: 'date must be a real date in YYYY-MM-DD format.' } })
  render(<Rewind />)
  expect(await screen.findByText(/date must be a real date/)).toBeTruthy()
})

test('prompts to connect Spotify when the account is not linked', async () => {
  responder.mockReturnValue({ status: 200, body: { connected: false } })
  render(<Rewind />)
  expect(await screen.findByText(/Connect your Spotify account/)).toBeTruthy()
})

test('a slow response for an old day never overwrites the newer day', async () => {
  const resolvers = {}
  globalThis.fetch = vi.fn((url) => new Promise((resolve) => { resolvers[String(url)] = resolve }))
  render(<Rewind />)
  fireEvent.click(screen.getByText(/Previous/))
  const urls = globalThis.fetch.mock.calls.map((c) => String(c[0]))
  const todayUrl = urls.find((u) => u.includes(`date=${today}`))
  const yestUrl = urls.find((u) => u.includes(`date=${yesterday}`))
  const reply = (body) => ({ ok: true, status: 200, json: async () => body })
  resolvers[yestUrl](reply({ ...FULL, top_tracks: [{ track_id: 'y', name: 'Yesterday Song', artist: 'X', plays: 1 }] }))
  expect(await screen.findByText('Yesterday Song')).toBeTruthy()
  resolvers[todayUrl](reply(FULL))                     // stale answer arrives late
  await new Promise((r) => setTimeout(r, 20))
  expect(screen.queryByText('Late Library')).toBeNull()
  expect(screen.getByText('Yesterday Song')).toBeTruthy()
})
