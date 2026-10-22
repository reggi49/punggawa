/**
 * device.ts
 * Utilitas deteksi perangkat & mode tampilan (2D Mobile vs 3D Desktop)
 * Mendukung preferensi hemat daya dan layar sentuh.
 */
import { useState, useEffect } from 'react';

export type ViewMode = 'auto' | '2d' | '3d';

export function isMobileDevice(): boolean {
  if (typeof window === 'undefined') return false;
  const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera || '';
  const isMobileUA = /android|iphone|ipad|ipod|blackberry|iemobile|opera mini|mobile/i.test(userAgent);
  const isSmallScreen = window.innerWidth < 768;
  return isMobileUA || isSmallScreen;
}

export function isTouchScreen(): boolean {
  if (typeof window === 'undefined') return false;
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

const STORAGE_KEY = 'punggawa_view_mode';

export function getSavedViewMode(): ViewMode {
  if (typeof window === 'undefined') return 'auto';
  try {
    const val = localStorage.getItem(STORAGE_KEY);
    if (val === '2d' || val === '3d' || val === 'auto') {
      return val as ViewMode;
    }
  } catch {
    // ignore
  }
  return 'auto';
}

export function setSavedViewMode(mode: ViewMode): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    // ignore
  }
}

/**
 * Hook reaktif untuk memantau ukuran layar dan mode tampilan aktif
 */
export function useDeviceMode() {
  const [viewMode, setViewModeState] = useState<ViewMode>(getSavedViewMode);
  const [isMobile, setIsMobile] = useState<boolean>(() => isMobileDevice());
  const [windowWidth, setWindowWidth] = useState<number>(() =>
    typeof window !== 'undefined' ? window.innerWidth : 1024
  );

  useEffect(() => {
    const handleResize = () => {
      const small = window.innerWidth < 768;
      setWindowWidth(window.innerWidth);
      setIsMobile(small || /android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent));
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const setViewMode = (mode: ViewMode) => {
    setViewModeState(mode);
    setSavedViewMode(mode);
  };

  // Resolusi mode aktif: jika 'auto', mobile -> 2d, desktop -> 3d
  const isEffective2D = viewMode === '2d' || (viewMode === 'auto' && isMobile);

  return {
    viewMode,
    setViewMode,
    isMobile,
    isEffective2D,
    windowWidth,
  };
}

