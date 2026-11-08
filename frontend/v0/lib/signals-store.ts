"use client";

import useSWR, { mutate } from 'swr';
import type { Signal, SignalStatus } from './types';
import { mockSignals } from './mock-data';

const SIGNALS_KEY = 'signals';

// In-memory store (would be replaced with API calls in production)
let signalsData: Signal[] = [...mockSignals];

export function useSignals() {
  const { data, error, isLoading } = useSWR<Signal[]>(
    SIGNALS_KEY,
    () => Promise.resolve(signalsData),
    {
      fallbackData: signalsData,
      revalidateOnFocus: false,
    }
  );

  return {
    signals: data || [],
    isLoading: isLoading && !data,
    error,
  };
}

export function useSignal(id: string) {
  const { data, error, isLoading } = useSWR<Signal | null>(
    id ? `signal-${id}` : null,
    () => Promise.resolve(signalsData.find(s => s.id === id) || null),
    {
      revalidateOnFocus: false,
    }
  );

  return {
    signal: data,
    isLoading,
    error,
  };
}

export async function createSignal(signal: Omit<Signal, 'id' | 'createdAt' | 'updatedAt'>): Promise<Signal> {
  const newSignal: Signal = {
    ...signal,
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  
  signalsData = [...signalsData, newSignal];
  await mutate(SIGNALS_KEY, signalsData, false);
  
  return newSignal;
}

export async function updateSignal(id: string, updates: Partial<Signal>): Promise<Signal | null> {
  const index = signalsData.findIndex(s => s.id === id);
  if (index === -1) return null;
  
  const updatedSignal: Signal = {
    ...signalsData[index],
    ...updates,
    updatedAt: new Date().toISOString(),
  };
  
  signalsData = [
    ...signalsData.slice(0, index),
    updatedSignal,
    ...signalsData.slice(index + 1),
  ];
  
  await mutate(SIGNALS_KEY, signalsData, false);
  await mutate(`signal-${id}`, updatedSignal, false);
  
  return updatedSignal;
}

export async function deleteSignal(id: string): Promise<boolean> {
  const index = signalsData.findIndex(s => s.id === id);
  if (index === -1) return false;
  
  signalsData = signalsData.filter(s => s.id !== id);
  await mutate(SIGNALS_KEY, signalsData, false);
  await mutate(`signal-${id}`, null, false);
  
  return true;
}

export async function moveSignal(id: string, newStatus: SignalStatus): Promise<Signal | null> {
  return updateSignal(id, { status: newStatus });
}

export function getSignalsByStatus(signals: Signal[], status: SignalStatus): Signal[] {
  return signals.filter(s => s.status === status);
}

