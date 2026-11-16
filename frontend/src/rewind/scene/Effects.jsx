// Post-processing ("after effects") applied to the finished frame. Tuned for a white page:
//   Bloom               - only things brighter than white glow (the orb's pulse, the ring),
//                         so the white background itself never smears
//   ChromaticAberration - an RGB-split glitch that flashes only when a new day loads,
//                         and is invisible the rest of the time
import { useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { Bloom, ChromaticAberration, EffectComposer } from '@react-three/postprocessing'
import { Vector2 } from 'three'

export default function Effects({ kick, energy }) {
    const aberration = useRef()
    const [offset] = useState(() => new Vector2())

    useFrame(() => {
        const split = kick.current ** 3 * 0.01
        aberration.current.offset.set(split, split * 0.6)
    })

    return (
        <EffectComposer multisampling={0}>
            <Bloom mipmapBlur intensity={0.6 + energy * 0.5} luminanceThreshold={1} luminanceSmoothing={0.2} />
            <ChromaticAberration ref={aberration} offset={offset} radialModulation modulationOffset={0.2} />
        </EffectComposer>
    )
}
