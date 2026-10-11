# Orbital Dance

TIME BOX AND SCOPE

This is a hackathon prototype that must be built in 30-45 minutes. Optimize for a working, demo-ready result over completeness. Rules:

- Ship a working end-to-end version first, then polish. Never leave the app in a broken state.

- No backend, no auth, no routing. One page only.

- Use procedural visuals only (no external texture downloads, no model files). Earth = sphere with a simple shader/gradient + atmosphere glow.

- Keep the sim layer small: one file with simplified circular-orbit math, a Pc function (Gaussian on miss distance, inflated by a drag factor from Kp/F10.7), and a maneuver function. No service abstraction beyond two typed functions.

- Skip: README, tests, mobile responsiveness, replay button, postprocessing library (fake glow with emissive materials and additive sprites).

- Simplify the loop to: drift -> approach -> alert -> (collision OR maneuver, alternating) -> reset.

BUILD ORDER (complete each before moving on)

1. Layout + space theme + top bar with space-weather strip

2. 3D scene: Earth, 3-4 orbiting satellites, tumbling crewmate-style debris, continuous approach/collision/avoid loop

3. Right info panel: debris velocity/acceleration, before vs after coordinates, delta-v, fuel used/saved, efficiency ring, all driven by sim state

4. Polish: HUD overlays, glow, animations

Do all of this in a single pass without asking clarifying questions. Make reasonable assumptions and keep going.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/e178da95-949f-4cac-9c5b-56fbec1ca9c5).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
