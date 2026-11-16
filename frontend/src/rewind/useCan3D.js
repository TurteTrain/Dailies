// Should the rewind show its animated 3D scene?
// No if the browser has no WebGL 2, or the person turned on "reduce motion" in their OS.
// Re-renders if they change that setting while the page is open.
import { useSyncExternalStore } from 'react'

const REDUCE_MOTION = '(prefers-reduced-motion: reduce)'

let webgl = null                   // checked once, on first use
function hasWebGL() {
    if (webgl === null) {
        try {
            webgl = Boolean(window.WebGL2RenderingContext && document.createElement('canvas').getContext('webgl2'))
        } catch {
            webgl = false
        }
    }
    return webgl
}

function subscribe(onChange) {
    const media = window.matchMedia?.(REDUCE_MOTION)
    media?.addEventListener('change', onChange)
    return () => media?.removeEventListener('change', onChange)
}

const motionAllowed = () => !(window.matchMedia?.(REDUCE_MOTION).matches ?? false)

export default function useCan3D() {
    return useSyncExternalStore(subscribe, motionAllowed) && hasWebGL()
}
