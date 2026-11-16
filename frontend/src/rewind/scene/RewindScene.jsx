// The 3D backdrop of the daily rewind. It only shows the day's data; the numbers and lists
// a person reads stay in normal HTML on top (Rewind.jsx), so they stay accessible.
//
// Props:
//   mood     - mood of the day ("calm", ...) or null
//   tracks   - the day's top tracks [{track_id, plays}, ...]
//   plays    - total plays that day
//   dayKey   - changes when a new day loads; triggers the fly-in animation
// Rewind.jsx skips this scene (and its ~1 MB of three.js) for reduced motion or no WebGL.
import { Canvas } from '@react-three/fiber'
import { Sparkles } from '@react-three/drei'
import CameraRig from './CameraRig.jsx'
import Effects from './Effects.jsx'
import MoodOrb from './MoodOrb.jsx'
import SpectrumRing from './SpectrumRing.jsx'
import TrackComets from './TrackComets.jsx'
import { moodStyle, playIntensity } from './moods.js'
import { useKick } from './motion.js'

const BACKGROUND = '#ffffff'    // same white as the page card (.hp-container), so the scene has no visible edge

function Stage({ mood, tracks, plays, dayKey }) {
    const { colors, energy } = moodStyle(mood)
    const kick = useKick(dayKey)

    return (
        <>
            <color attach="background" args={[BACKGROUND]} />
            <fog attach="fog" args={[BACKGROUND, 12, 24]} />
            <ambientLight intensity={1.2} />
            <pointLight position={[5, 4, 6]} intensity={80} color={colors[0]} />
            <pointLight position={[-6, -3, -2]} intensity={60} color={colors[1]} />

            <MoodOrb colors={colors} energy={energy} kick={kick} />
            <SpectrumRing colors={colors} energy={energy} intensity={playIntensity(plays)} kick={kick} />
            <TrackComets tracks={tracks} colors={colors} energy={energy} />

            {/* Two layers of drifting specks in the mood's colors (white stars would vanish on white) */}
            <Sparkles count={90} scale={[16, 8, 8]} size={4} speed={0.2 + energy * 0.8} color={colors[0]} />
            <Sparkles count={60} scale={[18, 9, 10]} size={6} speed={0.15 + energy * 0.5} color={colors[1]} opacity={0.6} />

            <CameraRig kick={kick} />
            <Effects kick={kick} energy={energy} />
        </>
    )
}

export default function RewindScene(props) {
    return (
        <Canvas className="rw-canvas" aria-hidden="true" dpr={[1, 1.75]} flat
                camera={{ position: [0, 0, 12], fov: 45 }}
                gl={{ antialias: false, powerPreference: 'high-performance' }}>
            <Stage {...props} />
        </Canvas>
    )
}
