// The centerpiece: a liquid-metal blob in the mood's colors that wobbles and pulses to a beat.
// A faint wireframe shell spins around it in the opposite direction.
import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Float, MeshDistortMaterial } from '@react-three/drei'
import { beat, useEasedColor, useEasedNumber } from './motion.js'

export default function MoodOrb({ colors, energy, kick }) {
    const orb = useRef()
    const material = useRef()
    const shell = useRef()
    const main = useEasedColor(colors[0])
    const accent = useEasedColor(colors[1])
    const e = useEasedNumber(energy)

    useFrame((state, dt) => {
        const pulse = beat(state.clock.elapsedTime, e.current)
        // A new day "pops" the orb (kick), then it settles into the beat.
        orb.current.scale.setScalar(1.5 + pulse * 0.1 * (0.4 + e.current) + kick.current * 0.5)
        orb.current.rotation.y += dt * (0.15 + e.current * 0.5)
        orb.current.rotation.x += dt * 0.07

        material.current.color.copy(main)
        material.current.emissive.copy(accent)
        material.current.emissiveIntensity = 0.35 + pulse * 0.9 + kick.current * 1.5
        material.current.distort = 0.22 + e.current * 0.38 + kick.current * 0.4

        shell.current.rotation.y -= dt * (0.1 + e.current * 0.3)
        shell.current.rotation.z += dt * 0.05
        shell.current.material.color.copy(accent)
    })

    return (
        <Float speed={1.4} floatIntensity={0.5} rotationIntensity={0.3}>
            <mesh ref={orb}>
                <icosahedronGeometry args={[1, 64]} />
                <MeshDistortMaterial ref={material} speed={2} roughness={0.25} metalness={0.35} />
            </mesh>
            <mesh ref={shell} scale={2.25}>
                <icosahedronGeometry args={[1, 2]} />
                <meshBasicMaterial wireframe transparent opacity={0.35} />
            </mesh>
        </Float>
    )
}
