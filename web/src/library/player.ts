import { useSyncExternalStore } from "react";
import { mediaUrl } from "../api";

let audio: HTMLAudioElement | null = null;
let playing: string | null = null;
const listeners = new Set<() => void>();

function emit(next: string | null) {
  playing = next;
  listeners.forEach((l) => l());
}

function element(): HTMLAudioElement {
  if (!audio) {
    audio = new Audio();
    audio.preload = "none";
    audio.addEventListener("ended", () => emit(null));
    audio.addEventListener("error", () => emit(null));
  }
  return audio;
}

export function toggle(id: string, media: string): void {
  const a = element();
  if (playing === id) {
    a.pause();
    emit(null);
    return;
  }
  a.pause();
  a.src = mediaUrl(media);
  a.currentTime = 0;
  emit(id);
  a.play().catch(() => emit(null));
}

export function stop(): void {
  audio?.pause();
  emit(null);
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function usePlaying(): string | null {
  return useSyncExternalStore(subscribe, () => playing);
}
