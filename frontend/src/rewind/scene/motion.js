// Small hooks that turn sudden prop changes into smooth motion inside the render loop.
// All the per-frame work happens in useFrame, never during a React render.
import { useEffect, useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { Color, MathUtils } from 'three'

// A THREE.Color that glides toward `hex` instead of jumping when the mood changes.
export function useEasedColor(hex, rate = 2.5) {
    const [color] = useState(() => new Color(hex))
    const [target] = useState(() => new Color())
    useFrame((_, dt) => {
        color.lerp(target.set(hex), 1 - Math.exp(-rate * dt))
    })
    return color
}

// A number (in a ref) that glides toward `value`.
export function useEasedNumber(value, rate = 2) {
    const eased = useRef(value)
    useFrame((_, dt) => {
        eased.current = MathUtils.damp(eased.current, value, rate, dt)
    })
    return eased
}

// Jumps to 1 every time `key` changes, then fades back to 0.
// One key change = one "whoosh" that the camera, orb and effects all react to.
export function useKick(key, decay = 1.4) {
    const kick = useRef(1)
    useEffect(() => {
        kick.current = 1
    }, [key])
    useFrame((_, dt) => {
        kick.current = MathUtils.damp(kick.current, 0, decay, dt)
    })
    return kick
}

// A sharp 0..1 pulse that repeats like a kick drum. Faster with more energy.
export const beat = (time, energy) => Math.pow(Math.sin(time * (1.4 + energy * 3.2)) * 0.5 + 0.5, 8)
