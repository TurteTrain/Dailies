// Each of the day's top songs is a comet orbiting the orb, leaving a glowing trail.
// The #1 song orbits closest and is the biggest; size follows plays.
import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Trail } from '@react-three/drei'

function Comet({ index, size, color, energy }) {
    const comet = useRef()
    const radius = 2.3 + index * 0.45
    const tilt = 0.5 + index * 0.55            // each orbit is tilted differently
    const phase = index * 2.4                  // and starts at a different spot
    const speed = (0.9 - index * 0.1) * (0.6 + energy)

    useFrame((state) => {
        const a = state.clock.elapsedTime * speed + phase
        const x = Math.cos(a) * radius
        const z = Math.sin(a) * radius
        comet.current.position.set(x, z * Math.sin(tilt), z * Math.cos(tilt))
    })

    return (
        <Trail width={size * 14} length={5} color={color} attenuation={(w) => w * w} decay={1}>
            <mesh ref={comet}>
                <sphereGeometry args={[size, 16, 16]} />
                <meshBasicMaterial color={color} toneMapped={false} />
            </mesh>
        </Trail>
    )
}

export default function TrackComets({ tracks, colors, energy }) {
    const most = Math.max(1, ...tracks.map((t) => t.plays))
    return tracks.map((track, i) => (
        <Comet key={track.track_id} index={i} energy={energy}
               size={0.05 + 0.07 * (track.plays / most)}
               color={i === 0 ? colors[0] : colors[1]} />
    ))
}
