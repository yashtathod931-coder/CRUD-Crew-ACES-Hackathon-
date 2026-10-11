<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Application rules
- Keep the existing TanStack/React framework and mount the single simulation screen at `/` with SSR disabled, because the WebGL experience is browser-only.
- Keep orbital propagation, Gaussian risk estimation and maneuver planning in the compact two-function simulation module; use Zustand solely to synchronize scene controls and telemetry.
- Derive Three.js material colors from the CSS semantic palette so the scene and mission-control interface share one theme.
- Keep visuals procedural and update scene transforms per frame while publishing telemetry at a throttled rate to avoid unnecessary interface renders.
