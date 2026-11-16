// Moves the camera: a fly-in from far away whenever a new day loads, plus a gentle
// parallax that follows the mouse so the scene feels like it has depth.
import { useFrame } from '@react-three/fiber'
import { MathUtils } from 'three'

const HOME_Z = 12
const FLY_IN_EXTRA = 9    // how much further back the camera starts on a new day

export default function CameraRig({ kick }) {
    useFrame(({ camera, pointer }, dt) => {
        camera.position.x = MathUtils.damp(camera.position.x, pointer.x * 1.2, 2.5, dt)
        camera.position.y = MathUtils.damp(camera.position.y, pointer.y * 0.8, 2.5, dt)
        camera.position.z = HOME_Z + kick.current ** 2 * FLY_IN_EXTRA
        camera.lookAt(0, 0, 0)
        camera.rotateZ(kick.current * 0.25)            // a slight barrel roll on the way in (after lookAt, which resets rotation)
    })
    return null
}
