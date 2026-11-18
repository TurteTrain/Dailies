import { render, screen, fireEvent, within, cleanup } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import Groups from './Groups.jsx'
import Homepage from '../homepage/homepage.jsx'

const REWIND = {
  connected: true, group: 'Crew', member_count: 3, date: '2026-11-14', timezone: 'UTC',
  total_plays: 6, approx_minutes: 20,
  top_tracks: [{ track_id: 't1', name: 'Late Library', artist: 'Quiet Hours', plays: 4 }],
  top_artists: [{ artist_id: 'a1', name: 'Quiet Hours', plays: 4 }],
  top_genres: [{ genre: 'lo-fi', plays: 4 }],
  top_moods: [{ mood: 'calm', plays: 4, share: 1 }], mood_of_the_day: 'calm',
}
const detailOf = (over = {}) => ({
  id: 7, name: 'Crew', owner: 'me', is_owner: true, member_count: 2,
  members: [{ user_id: 1, username: 'me', is_owner: true, is_friend: false },
            { user_id: 2, username: 'ann', is_owner: false, is_friend: true }],
  pending: [{ user_id: 3, username: 'ben', is_owner: false, is_friend: false }], ...over,
})

let server, calls
const json = (body, status = 200) => ({ ok: status < 400, status, json: async () => body })

beforeEach(() => {
  document.cookie = 'csrftoken=test'
  calls = []
  server = {
    groups: { groups: [{ id: 7, name: 'Crew', member_count: 2, is_owner: true },
                       { id: 8, name: 'Solo', member_count: 1, is_owner: true }], invites: [] },
    friends: { friends: [{ id: 1, user_id: 2, username: 'ann' }], incoming: [], outgoing: [] },
    detail: detailOf(),
    createError: null,
  }
  globalThis.fetch = vi.fn(async (url, opts = {}) => {
    const u = String(url), method = opts.method || 'GET'
    const body = opts.body ? JSON.parse(opts.body) : null
    calls.push({ url: u, method, body })
    if (u === '/api/friends') return json(server.friends)
    if (u === '/api/groups' && method === 'GET') return json(server.groups)
    if (u === '/api/groups' && method === 'POST')
      return server.createError ? json({ error: server.createError }, 400)
                                : json(detailOf({ id: 9, name: body.name, member_count: 1, pending: [] }), 201)
    if (u === '/api/groups/invites/accept') {
      server.groups = { groups: [...server.groups.groups, { id: 5, name: 'Party', member_count: 2, is_owner: false }], invites: [] }
      return json(server.groups)
    }
    if (u === '/api/groups/invites/decline') { server.groups = { ...server.groups, invites: [] }; return json(server.groups) }
    if (u.startsWith('/api/groups/7/rewind')) return json(REWIND)
    if (u.startsWith('/api/groups/9/rewind')) return json({ ...REWIND, total_plays: 0 })
    if (u === '/api/groups/7/invite')
      return json({ invited: ['cy'], skipped: ['ann'], group: detailOf({ pending: [...server.detail.pending,
        { user_id: 4, username: 'cy', is_owner: false, is_friend: false }] }) })
    if (u === '/api/groups/7/leave' || (u === '/api/groups/7' && method === 'DELETE')) return { ok: true, status: 204, json: async () => null }
    if (u === '/api/groups/7') return json(server.detail)
    return json({ connected: false, total: 0, listens: [] })
  })
})
afterEach(() => { cleanup(); vi.restoreAllMocks() })

const openCrew = async () => {
  render(<Groups onBack = {() => {}} />)
  fireEvent.click(await screen.findByLabelText('Open Crew'))
}

test('lists my groups with name and member count (singular and plural)', async () => {
  render(<Groups onBack = {() => {}} />)
  expect(await screen.findByText('Crew')).toBeTruthy()
  expect(screen.getByText('2 members')).toBeTruthy()
  expect(screen.getByText('Solo')).toBeTruthy()
  expect(screen.getByText('1 member')).toBeTruthy()
})

test('shows an empty state when there are no groups', async () => {
  server.groups = { groups: [], invites: [] }
  render(<Groups onBack = {() => {}} />)
  expect(await screen.findByText(/not in any groups yet/)).toBeTruthy()
})

test('create form: friends are offered with an icon, typed friends are marked, group is posted', async () => {
  render(<Groups onBack = {() => {}} />)
  await screen.findByText('Crew')
  fireEvent.click(screen.getByText('Create group', { selector: '.hp-bar button' }))
  fireEvent.change(screen.getByLabelText('Group name'), { target: { value: '  Road trip ' } })

  // friend suggestion with the friend icon, one tap adds it as a (marked) chip
  fireEvent.click(await screen.findByLabelText('Add friend ann'))
  const chips = screen.getByLabelText('People to invite')
  expect(within(chips).getByText('ann').closest('.gr-chip').className).toContain('friend')
  expect(within(chips).getByLabelText('friend')).toBeTruthy()
  expect(screen.queryByLabelText('Add friend ann')).toBeNull()      // no longer suggested

  // a typed non-friend gets a plain chip; Enter adds it; duplicates are ignored case-insensitively
  const box = screen.getByLabelText('Invite by username')
  fireEvent.change(box, { target: { value: 'Zed' } })
  fireEvent.keyDown(box, { key: 'Enter' })
  fireEvent.change(box, { target: { value: 'zed' } })
  fireEvent.keyDown(box, { key: 'Enter' })
  expect(within(chips).getAllByText('Zed')).toHaveLength(1)
  expect(within(chips).getByText('Zed').closest('.gr-chip').className).not.toContain('friend')

  fireEvent.click(screen.getByText('Create group', { selector: 'form button[type="submit"]' }))
  expect(await screen.findByText('Road trip')).toBeTruthy()          // lands on the new group's dashboard
  const post = calls.find((c) => c.url === '/api/groups' && c.method === 'POST')
  expect(post.body).toEqual({ name: 'Road trip', usernames: ['ann', 'Zed'] })
})

test('typing a friends name by hand also gets the friend mark (case-insensitive)', async () => {
  render(<Groups onBack = {() => {}} />)
  await screen.findByText('Crew')
  fireEvent.click(screen.getByText('Create group', { selector: '.hp-bar button' }))
  const box = screen.getByLabelText('Invite by username')
  fireEvent.change(box, { target: { value: 'ANN' } })
  fireEvent.click(screen.getByText('Add'))
  expect(within(screen.getByLabelText('People to invite')).getByLabelText('friend')).toBeTruthy()
})

test('a group of one can be created with no invitees', async () => {
  render(<Groups onBack = {() => {}} />)
  await screen.findByText('Crew')
  fireEvent.click(screen.getByText('Create group', { selector: '.hp-bar button' }))
  fireEvent.change(screen.getByLabelText('Group name'), { target: { value: 'Just me' } })
  fireEvent.click(screen.getByText('Create group', { selector: 'form button[type="submit"]' }))
  expect(await screen.findByText('1 member')).toBeTruthy()
  expect(calls.find((c) => c.method === 'POST').body).toEqual({ name: 'Just me', usernames: [] })
})

test('empty name is rejected locally; unknown usernames show the server error and keep the form', async () => {
  render(<Groups onBack = {() => {}} />)
  await screen.findByText('Crew')
  fireEvent.click(screen.getByText('Create group', { selector: '.hp-bar button' }))
  fireEvent.click(screen.getByText('Create group', { selector: 'form button[type="submit"]' }))
  expect((await screen.findByRole('alert')).textContent).toBe('Give your group a name.')
  expect(calls.some((c) => c.method === 'POST')).toBe(false)

  server.createError = 'No user named ghost.'
  fireEvent.change(screen.getByLabelText('Group name'), { target: { value: 'X' } })
  fireEvent.change(screen.getByLabelText('Invite by username'), { target: { value: 'ghost' } })
  fireEvent.click(screen.getByText('Add'))
  fireEvent.click(screen.getByText('Create group', { selector: 'form button[type="submit"]' }))
  expect((await screen.findByRole('alert')).textContent).toBe('No user named ghost.')
  expect(screen.getByLabelText('Group name').value).toBe('X')       // nothing lost
})

test('invitations can be accepted or declined', async () => {
  server.groups = { groups: [], invites: [{ id: 3, group_name: 'Party', invited_by: 'ann' }] }
  render(<Groups onBack = {() => {}} />)
  expect(await screen.findByText('Party')).toBeTruthy()
  expect(screen.getByText('Invited by ann')).toBeTruthy()
  fireEvent.click(screen.getByLabelText('Accept invite to Party'))
  expect(await screen.findByText('You joined Party.')).toBeTruthy()
  expect(calls.find((c) => c.url === '/api/groups/invites/accept').body).toEqual({ invite_id: 3 })
  expect(screen.getByLabelText('Open Party')).toBeTruthy()
})

test('declining an invitation posts the decline', async () => {
  server.groups = { groups: [], invites: [{ id: 3, group_name: 'Party', invited_by: null }] }
  render(<Groups onBack = {() => {}} />)
  fireEvent.click(await screen.findByLabelText('Decline invite to Party'))
  expect(await screen.findByText('Declined Party.')).toBeTruthy()
  expect(calls.find((c) => c.url === '/api/groups/invites/decline').body).toEqual({ invite_id: 3 })
})

test('group dashboard shows the combined rewind with day-by-day browsing', async () => {
  await openCrew()
  expect(await screen.findByText('Late Library')).toBeTruthy()
  expect(screen.getByText('Group rewind')).toBeTruthy()
  expect(screen.getByText('2 members')).toBeTruthy()
  for (const t of ['Top songs', 'Top artists', 'Top genres', 'Moods']) expect(screen.getByText(t)).toBeTruthy()
  expect(screen.getByText('mood of the day')).toBeTruthy()
  expect(calls.find((c) => c.url.startsWith('/api/groups/7/rewind?date=')).url).toContain('&tz=')
  // unlike a friend's view, past days can be browsed
  expect(screen.getByLabelText('Rewind date')).toBeTruthy()
  fireEvent.click(screen.getByText(/Previous/))
  await screen.findByText('Late Library')
  const rewindCalls = calls.filter((c) => c.url.startsWith('/api/groups/7/rewind'))
  expect(rewindCalls.length).toBe(2)
  expect(rewindCalls[0].url).not.toBe(rewindCalls[1].url)
})

test('owner sees members (friend marked, pending listed), invite form and Delete, not Leave', async () => {
  await openCrew()
  const members = await screen.findByText('Members')
  const list = members.parentElement
  expect(within(list).getByText('ann')).toBeTruthy()
  expect(within(list).getAllByLabelText('friend')).toHaveLength(1)
  expect(within(list).getByText('Owner')).toBeTruthy()
  expect(within(list).getByText('ben')).toBeTruthy()
  expect(within(list).getByText('Invited')).toBeTruthy()
  expect(screen.getByText('Delete group')).toBeTruthy()
  expect(screen.queryByText('Leave group')).toBeNull()
  expect(screen.getByText('Invite more people')).toBeTruthy()
})

test('owner can invite more people later and sees who was skipped', async () => {
  await openCrew()
  await screen.findByText('Invite more people')
  const form = screen.getByText('Invite more people').closest('form')
  fireEvent.change(within(form).getByLabelText('Invite by username'), { target: { value: 'cy' } })
  fireEvent.click(within(form).getByText('Add'))
  fireEvent.click(within(form).getByText('Send invites'))
  expect(await screen.findByText(/Invited cy\. Already in the group or invited: ann\./)).toBeTruthy()
  expect(calls.find((c) => c.url === '/api/groups/7/invite').body).toEqual({ usernames: ['cy'] })
  expect(screen.getByText('cy')).toBeTruthy()
})

test('a regular member can leave but not delete or invite', async () => {
  server.detail = detailOf({ is_owner: false, pending: undefined })
  server.groups.groups[0].is_owner = false
  await openCrew()
  await screen.findByText('Members')
  expect(screen.getByText('Leave group')).toBeTruthy()
  expect(screen.queryByText('Delete group')).toBeNull()
  expect(screen.queryByText('Invite more people')).toBeNull()
  expect(screen.queryByText('Invited')).toBeNull()
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  fireEvent.click(screen.getByText('Leave group'))
  expect(await screen.findByText('Your groups')).toBeTruthy()       // back on the list
  expect(calls.find((c) => c.url === '/api/groups/7/leave').method).toBe('POST')
})

test('delete asks for confirmation first and only deletes when confirmed', async () => {
  await openCrew()
  await screen.findByText('Delete group')
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
  fireEvent.click(screen.getByText('Delete group'))
  expect(confirm).toHaveBeenCalled()
  expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
  confirm.mockReturnValue(true)
  fireEvent.click(screen.getByText('Delete group'))
  expect(await screen.findByText('Your groups')).toBeTruthy()
  expect(calls.find((c) => c.method === 'DELETE').url).toBe('/api/groups/7')
})

test('dashboard has a Groups button with an invitation badge that opens the groups view', async () => {
  server.groups = { groups: [], invites: [{ id: 1, group_name: 'Party', invited_by: 'ann' }] }
  const user = { id: 1, username: 'me', is_staff: false, spotify_connected: false }
  render(<Homepage user = {user} onLogout = {() => {}} onUserDeletion = {() => {}} onAdminDeletion = {() => {}} />)
  expect((await screen.findByLabelText('1 group invitations')).textContent).toBe('1')
  fireEvent.click(screen.getByText(/^Groups/))
  expect(await screen.findByText('Invitations')).toBeTruthy()
  fireEvent.click(screen.getByText(/Back to dashboard/))
  expect(await screen.findByText('Your listening history')).toBeTruthy()
})

test('long group names stay whole and readable in invitations and in the groups list', async () => {
  const long = 'The Absolutely Unreasonably Long Group Name For Everyone Who Loves Music ' + 'x'.repeat(10)
  server.groups = { groups: [{ id: 7, name: long, member_count: 12, is_owner: false }],
                    invites: [{ id: 3, group_name: long, invited_by: 'a_really_long_username_here' }] }
  render(<Groups onBack = {() => {}} />)
  const titles = await screen.findAllByText(long)
  expect(titles).toHaveLength(2)                                         // one per list, as a single text node
  titles.forEach((t) => expect(t.className).toContain('gr-title'))
  expect(screen.getByText('Invited by a_really_long_username_here')).toBeTruthy()
  expect(screen.getByText('12 members')).toBeTruthy()
  // the invitation card spans the full width instead of being squeezed into one grid column
  expect(screen.getByText('Invitations').closest('section').className).toContain('gr-wide')
})
