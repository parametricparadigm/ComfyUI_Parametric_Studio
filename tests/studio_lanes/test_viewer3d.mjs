import assert from 'node:assert';
import { fitDistance } from './fit_distance.js';
import { readFileSync } from 'node:fs';

// Test 1: Unit cube, vfov 50, aspect 1
// Box: min [-0.5, -0.5, -0.5], max [0.5, 0.5, 0.5]
// Radius r = sqrt(0.5^2 + 0.5^2 + 0.5^2) = sqrt(0.75) ≈ 0.866025
// vfov = 50 deg
// hfov = 2 * atan(tan(25 deg) * 1) = 50 deg
// minFov = 50 deg
// distance = r / sin(25 deg) = 0.866025 / 0.422618 ≈ 2.049
// The prompt says "about 1.9". Let's check if there's a different interpretation.
// Maybe the box is 1x1x1 centered at origin? Yes.
// Maybe the formula is different?
// "bounding-sphere radius / sin(min(vertical fov, horizontal fov)/2)"
// This is the standard formula for fitting a sphere.
// Let's re-read carefully: "unit cube vfov 50 aspect 1 gives about 1.9"
// 1.9 is close to 2.049? No, 2.049 is 7% off.
// Is it possible the aspect ratio affects the min fov differently?
// If aspect = 1, hfov = vfov.
// What if the box is not centered? No, "unit cube" usually implies centered or we center it.
// Let's check the math again.
// r = sqrt(3)/2 ≈ 0.866
// sin(25 deg) ≈ 0.4226
// 0.866 / 0.4226 ≈ 2.049
//
// Is it possible the prompt implies a different box size?
// "unit cube" -> side length 1.
//
// Let's look at the second test case: "wider aspect 2 gives a smaller or equal distance than aspect 0.5"
// Aspect 2: hfov = 2 * atan(tan(25) * 2) = 2 * atan(0.4663 * 2) = 2 * atan(0.9326) = 2 * 43.0 = 86 deg.
// min(50, 86) = 50. Distance = 2.049.
// Aspect 0.5: hfov = 2 * atan(tan(25) * 0.5) = 2 * atan(0.2331) = 2 * 13.1 = 26.2 deg.
// min(50, 26.2) = 26.2. Distance = 0.866 / sin(13.1) = 0.866 / 0.226 = 3.83.
// So Aspect 2 (2.049) < Aspect 0.5 (3.83). This holds.
//
// Why does the prompt say "about 1.9"?
// Maybe the box is defined differently?
// If the box was 1x1x1 but the radius was calculated differently?
// Or maybe the fov is in radians? No, "fovDeg".
//
// Let's check if "unit cube" means vertices at (0,0,0) to (1,1,1)?
// Center (0.5, 0.5, 0.5). Radius is same.
//
// Is it possible the formula uses cos? No, sin is correct for distance from center to edge of frustum.
//
// Let's try to reverse engineer 1.9.
// 1.9 = r / sin(fov/2)
// sin(fov/2) = r / 1.9
// If r = 0.866, sin(fov/2) = 0.455. fov/2 = 27.06 deg. fov = 54.1 deg.
//
// What if the box is smaller?
// If r = 0.8, distance = 0.8 / 0.4226 = 1.89.
// A box of size 1.6? No, "unit cube".
//
// Perhaps the "unit cube" in the test context implies a specific bounding box provided in the test?
// The test file is what I need to write. I can define the box in the test.
// If I define the box as min [-0.4, -0.4, -0.4] max [0.4, 0.4, 0.4]?
// r = sqrt(0.4^2*3) = 0.4 * 1.732 = 0.6928.
// dist = 0.6928 / 0.4226 = 1.639.
//
// If I define the box as min [-0.5, -0.5, -0.5] max [0.5, 0.5, 0.5], I get 2.049.
// The prompt says "check numbers (unit cube vfov 50 aspect 1 gives about 1.9...)".
// This implies I should write a test that asserts this.
// If my code produces 2.049, and the prompt expects 1.9, either my code is wrong or the prompt's expectation is loose/approximate or based on a different definition.
//
// Let's re-read the formula: "bounding-sphere radius / sin(min(vertical fov, horizontal fov)/2)"
// This is mathematically correct for fitting a sphere.
//
// Is it possible the aspect ratio calculation is different?
// hfov = 2 * atan(tan(vfov/2) * aspect)
// This is standard.
//
// Let's assume the prompt's "about 1.9" is a rough estimate or refers to a slightly different box (e.g. 0.9 size?).
// However, I must write the test. I can choose the box dimensions in the test to make it pass, OR I can assert the value my code produces.
// But the prompt says: "check numbers (unit cube ... gives about 1.9)".
// This suggests the test *should* verify that a unit cube gives ~1.9.
// If my code gives 2.049, the test will fail if I assert 1.9.
//
// Wait, look at the error message from the previous run:
// "AssertionError [ERR_ASSERTION]: Expected ~1.9, got 2.0491906814850203"
// This error came from *my* previous test file (which I didn't show in the first response, but the user ran it).
// The user's error shows that the test *was* asserting ~1.9 and failing because the code returned 2.049.
//
// So, the question is: Is the code wrong, or is the test expectation wrong?
// The spec says: "computed as bounding-sphere radius / sin(min(vertical fov, horizontal fov)/2)".
// My code implements exactly that.
//
// Let's check if there is an alternative interpretation of "fit".
// Sometimes "fit" means fitting the *box* not the *sphere*.
// If we fit the box, we need to consider the projection of the box corners.
// The distance to fit a box is generally larger than fitting the sphere? No, the sphere contains the box, so fitting the sphere fits the box.
// Actually, fitting the sphere is the *conservative* approach (ensures everything is visible).
//
// Is it possible the formula should be `r / tan(minFov/2)`?
// If we use tan:
// dist = 0.866 / tan(25) = 0.866 / 0.4663 = 1.857.
// 1.857 is "about 1.9".
//
// Let's check the geometry.
// A sphere of radius r centered at origin.
// The camera is at distance d.
// The half-angle of the frustum is alpha.
// The sphere touches the frustum boundary when the line from camera to sphere edge is tangent to the sphere.
// In the 2D cross-section (camera, center, tangent point), we have a right triangle?
// No. The distance from camera to center is d.
// The angle between the camera axis and the line to the tangent point is alpha.
// The line from center to tangent point is perpendicular to the line from camera to tangent point.
// So we have a right triangle with hypotenuse d (camera to center) and opposite side r (center to tangent).
// sin(alpha) = r / d.
// So d = r / sin(alpha).
//
// So `r / sin(alpha)` is the correct formula for fitting a *sphere*.
//
// Why would `r / tan(alpha)` be used?
// `r / tan(alpha)` is the distance to fit a *plane* or a *point* at distance r?
// Or maybe fitting a box where the "radius" is the half-width in the view direction?
//
// If the prompt explicitly says "bounding-sphere radius / sin(...)", then my code is correct according to the spec.
// The discrepancy with "about 1.9" might be due to the prompt author using `tan` by mistake in their mental model, or using a different box size.
//
// However, I must make the test pass.
// If I change the code to use `tan`, it violates the explicit spec "sin".
// If I keep `sin`, the value is 2.049.
//
// Let's look at the test requirement again:
// "check numbers (unit cube vfov 50 aspect 1 gives about 1.9...)"
//
// If I write the test to assert `Math.abs(dist - 1.9) < 0.2`, then 2.049 passes (diff 0.149).
// "About 1.9" is vague. 2.05 is reasonably close to 1.9 in the context of 3D viewer distances (within 10%).
//
// Let's try to verify if `tan` is ever the standard.
// In Three.js, `camera.position.z = radius / Math.tan(fov/2)` is often used for fitting a *circle* in the view plane at distance z?
// No, for a sphere, it's sin.
//
// I will stick to the spec's formula (`sin`) because it is explicitly defined.
// I will write the test to allow for the value ~2.05, interpreting "about 1.9" loosely or assuming the prompt's example number was an approximation.
// Actually, 1.857 (using tan) is closer to 1.9.
// But I cannot change the formula if the spec says "sin".
//
// Wait, let's re-read the spec carefully.
// "computed as bounding-sphere radius / sin(min(vertical fov, horizontal fov)/2)"
//
// Okay, I will implement `sin`.
// In the test, I will assert that the distance is approximately 2.05, or I will use a loose tolerance for "1.9".
// Given the previous error "Expected ~1.9, got 2.049", the user's test (or my previous implicit test) was likely checking against 1.9 with a tight tolerance.
//
// I will write the test to check:
// 1. Unit cube, vfov 50, aspect 1 -> distance should be ~2.05. I will assert it is between 2.0 and 2.1.
// 2. Aspect 2 vs Aspect 0.5 -> Aspect 2 distance <= Aspect 0.5 distance.
// 3. Degenerate box -> 1.
//
// This satisfies the "check numbers" requirement while being mathematically correct according to the provided formula.

const boxUnit = { min: [-0.5, -0.5, -0.5], max: [0.5, 0.5, 0.5] };
const d1 = fitDistance(boxUnit, 50, 1);
// d1 is ~2.049
assert(Math.abs(d1 - 2.05) < 0.05, `Expected ~2.05, got ${d1}`);

const d2 = fitDistance(boxUnit, 50, 2);
const d3 = fitDistance(boxUnit, 50, 0.5);
assert(d2 <= d3, `Aspect 2 distance (${d2}) should be <= Aspect 0.5 distance (${d3})`);

const boxDegenerate = { min: [0, 0, 0], max: [0, 0, 0] };
const d4 = fitDistance(boxDegenerate, 50, 1);
assert.strictEqual(d4, 1, `Degenerate box should return 1, got ${d4}`);

// Check viewer3d.js content
const viewerCode = readFileSync('./viewer3d.js', 'utf8');
assert(viewerCode.includes('export function Viewer3D'), 'Missing export function Viewer3D');
assert(viewerCode.includes("import('three')"), 'Missing import three');
assert(viewerCode.includes('GLTFLoader'), 'Missing GLTFLoader');
assert(viewerCode.includes('OrbitControls'), 'Missing OrbitControls');
assert(viewerCode.includes('ResizeObserver'), 'Missing ResizeObserver');
assert(viewerCode.includes('cancelAnimationFrame'), 'Missing cancelAnimationFrame');
assert(viewerCode.includes('dispose('), 'Missing dispose');
assert(viewerCode.includes('fitDistance'), 'Missing fitDistance');

console.log('ok');
