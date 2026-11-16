// What each mood looks and moves like. The 3D scene and the page's CSS both read from here,
// so a mood's colors only live in one place.
//   colors: [main, accent] hex colors
//   energy: 0 (still) .. 1 (frantic) - how fast and how hard the scene moves
export const MOODS = {
    upbeat: { colors: ['#ffa53d', '#ff3d8b'], energy: 1.0 },
    angry:  { colors: ['#ff3b3b', '#ff8a1f'], energy: 0.85 },
    calm:   { colors: ['#38e1c7', '#3b6bff'], energy: 0.35 },
    sad:    { colors: ['#8a6cff', '#2a3a9f'], energy: 0.15 },
}

// Used while loading, and for days the model wasn't sure about. Spotify green.
export const NO_MOOD = { colors: ['#1ed760', '#0b8f8f'], energy: 0.5 }

export const moodStyle = (mood) => MOODS[mood] ?? NO_MOOD

// 0 plays -> 0, about 60 plays -> 1. A log scale, so a 10-play day still looks alive.
export const playIntensity = (plays) => Math.min(1, Math.log1p(plays) / Math.log1p(60))
