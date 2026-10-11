import { create } from 'zustand';
import { sampleSimulation, type Mode, type Snapshot } from './simulation';
interface SimulationState {
  playing: boolean; speed: number; mode: Mode; elapsed: number; snapshot: Snapshot; autoOrbit: boolean; viewRevision: number;
}
export const useSimulation = create<SimulationState>(() => ({
  playing:true, speed:1, mode:'auto', elapsed:4, snapshot:sampleSimulation(4,'auto'), autoOrbit:false, viewRevision:0,
}));
