// A ring of glowing bars around the orb, moving like an audio visualizer.
// It is not real audio (we never hear the songs): the bars are layered sine waves whose
// height follows the mood's energy and how much was played that day.
import { useLayoutEffect, useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { Color, Object3D } from 'three'
import { useEasedColor, useEasedNumber } from './motion.js'

const BARS = 120
const RADIUS = 3.1

export default function SpectrumRing({ colors, energy, intensity, kick }) {
    const bars = useRef()
    const main = useEasedColor(colors[0])
    const accent = useEasedColor(colors[1])
    const e = useEasedNumber(energy)
    const loud = useEasedNumber(intensity)
    const [dummy] = useState(() => new Object3D())
    const [tint] = useState(() => new Color())

    // Instance colors must exist before the first frame, or three.js ignores them.
    useLayoutEffect(() => {
        for (let i = 0; i < BARS; i++) bars.current.setColorAt(i, tint)
    }, [tint])

    useFrame((state) => {
        const t = state.clock.elapsedTime
        const speed = 1 + e.current * 4
        for (let i = 0; i < BARS; i++) {
            const angle = (i / BARS) * Math.PI * 2
            const wave = Math.sin(angle * 3 + t * speed) * Math.sin(angle * 7 - t * speed * 0.7)
            // The ripple: a bump that races around the ring after a new day loads
            const ripple = kick.current * Math.max(0, Math.cos(angle - t * 6)) ** 12
            const height = 0.08 + Math.abs(wave) * (0.25 + loud.current * 0.9) * (0.4 + e.current) + ripple * 1.5

            // Each bar sits on the ring and points straight out from the center
            const r = RADIUS + height / 2
            dummy.position.set(Math.cos(angle) * r, Math.sin(angle) * r, 0)
            dummy.rotation.set(0, 0, angle - Math.PI / 2)
            dummy.scale.set(1, height, 1)
            dummy.updateMatrix()
            bars.current.setMatrixAt(i, dummy.matrix)

            // Fade from the main color to the accent around the ring; the ripple goes past 1 so it blooms
            tint.copy(main).lerp(accent, (Math.sin(angle * 2 + t) + 1) / 2).multiplyScalar(1 + ripple * 2)
            bars.current.setColorAt(i, tint)
        }
        bars.current.instanceMatrix.needsUpdate = true
        bars.current.instanceColor.needsUpdate = true
    })

    return (
        <instancedMesh ref={bars} args={[undefined, undefined, BARS]}>
            <boxGeometry args={[0.05, 1, 0.05]} />
            <meshBasicMaterial toneMapped={false} />
        </instancedMesh>
    )
}
