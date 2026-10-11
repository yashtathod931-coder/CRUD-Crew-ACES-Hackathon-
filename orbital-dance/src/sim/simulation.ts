export type Mode = 'auto' | 'on' | 'off';
export type Phase = 'drift' | 'approach' | 'alert' | 'maneuver' | 'collision' | 'reset';
export type Vec3 = [number, number, number];
export interface Snapshot {
  time: number; cycle: number; phase: Phase; avoids: boolean; kp: number; flux: number; wind: number; drag: number; covariance: number;
  tca: number; miss: number; pc: number; beforePc: number; afterPc: number; predictedMiss: number; velocity: number; acceleration: number;
  altitude: number; inclination: number; target: Vec3; originalTarget: Vec3; debris: Vec3; before: Vec3; after: Vec3; burn: number;
}
export interface Maneuver { deltaV: number; fuel: number; saved: number; percent: number; efficiency: number; duration: number; }
// Deliberately simplified Gaussian estimate; this is not a flight-certified probability model.
export function sampleSimulation(totalTime: number, mode: Mode): Snapshot {
  const time = totalTime % 22;
  const cycle = Math.floor(totalTime / 22);
  const avoids = mode === 'auto' ? cycle % 2 === 0 : mode === 'on';
  const kp = 3.4 + Math.sin(totalTime * .12) * .6;
  const flux = 142 + Math.sin(totalTime * .08) * 7;
  const drag = 1 + kp * .08 + Math.max(0, flux - 100) * .002;
  const covariance = .16 * drag;
  const gaussian = (distance: number) => Math.min(.99, .016 * drag * Math.exp(-distance * distance / (2 * covariance * covariance)));
  const predictedMiss = .12 + .018 * Math.sin(cycle);
  const beforePc = gaussian(predictedMiss);
  const burn = avoids ? Math.min(1, Math.max(0, (time - 10) / 3)) : 0;
  const phase: Phase = time < 5 ? 'drift' : time < 9 ? 'approach' : time < 14 ? 'alert' : time < 18 ? (avoids ? 'maneuver' : 'collision') : 'reset';
  const theta = .045 * time + .1;
  const targetBase: Vec3 = [2.85 * Math.cos(theta), .7 * Math.sin(theta), 2.7 * Math.sin(theta)];
  const target: Vec3 = [targetBase[0] + burn * .52, targetBase[1] + burn * .25, targetBase[2]];
  const encounterTheta = .045 * 14 + .1;
  const encounter: Vec3 = [2.85 * Math.cos(encounterTheta), .7 * Math.sin(encounterTheta), 2.7 * Math.sin(encounterTheta)];
  const debris: Vec3 = [encounter[0] + (14 - time) * .22, encounter[1] + (14 - time) * .14, encounter[2] + (14 - time) * .09];
  const miss = Math.hypot(Math.abs(14 - time) * .38, predictedMiss + burn * 1.72);
  const radius = 6371 + 550;
  const before: Vec3 = [radius * Math.cos(encounterTheta), radius * Math.sin(encounterTheta) * .25, radius * Math.sin(encounterTheta) * .968];
  const after: Vec3 = [before[0] + 1.72, before[1] + .63, before[2] + .21];
  return { time, cycle, phase, avoids, kp, flux, wind: 426 + Math.sin(totalTime * .14) * 19, drag, covariance,
    tca: Math.max(0, 14-time), miss, pc: phase === 'collision' ? beforePc : gaussian(predictedMiss + Math.max(0,9-time)*.1 + burn*1.72), beforePc, afterPc: gaussian(predictedMiss + 1.72), predictedMiss,
    velocity: 7.64 + Math.sin(totalTime * .32) * .045, acceleration: .00032 * drag, altitude: 550 + Math.sin(time * .15) * 2.3,
    inclination: 51.6 + Math.sin(cycle) * .1, target, originalTarget: targetBase, debris, before, after, burn };
}
export function planManeuver(s: Snapshot): Maneuver {
  const deltaV = .68 * s.drag;
  const fuel = 420 * (1 - Math.exp(-deltaV / (220 * 9.80665)));
  const naiveFuel = fuel * (3.4 + s.drag * .2);
  return { deltaV, fuel, saved: naiveFuel - fuel, percent: fuel / 38 * 100, efficiency: (1 - fuel/naiveFuel) * 100, duration: deltaV / .047 };
}
