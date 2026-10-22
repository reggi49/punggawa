import React, { useState, useEffect } from 'react';
import { useProgress } from '@react-three/drei';
import { Sparkles, Layers, ArrowRight, Zap } from 'lucide-react';

interface OfficeLoadingScreenProps {
  onSwitchTo2D?: () => void;
  message?: string;
}

export function OfficeLoadingScreen({ onSwitchTo2D, message }: OfficeLoadingScreenProps) {
  const { progress, active, item } = useProgress();
  const [displayProgress, setDisplayProgress] = useState(0);

  // Smooth progress interpolation
  useEffect(() => {
    const target = Math.max(displayProgress, Math.round(progress));
    const timer = setTimeout(() => {
      setDisplayProgress(target);
    }, 50);
    return () => clearTimeout(timer);
  }, [progress, displayProgress]);

  // Derive human-readable loading hint
  const getLoadingHint = () => {
    if (message) return message;
    if (displayProgress < 30) return 'Mengunduh model furnitur & workstation...';
    if (displayProgress < 65) return 'Memproses material & tekstur Scandinavian...';
    if (displayProgress < 95) return 'Menyiapkan pencahayaan & ambient multi-agent...';
    return 'Menyempurnakan tata letak kantor...';
  };

  const cleanItemName = item ? item.split('/').pop()?.split('?')[0] : '';

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 50,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #E8E4DA 0%, #D8D2C5 100%)',
        color: '#30343A',
        fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
        padding: '24px',
      }}
    >
      {/* Central Glass Card */}
      <div
        className="warm-panel"
        style={{
          width: '100%',
          maxWidth: '460px',
          borderRadius: '24px',
          padding: '36px 32px',
          boxShadow: '0 20px 48px rgba(48, 52, 58, 0.12), 0 4px 12px rgba(48, 52, 58, 0.06)',
          border: '1px solid rgba(255, 255, 255, 0.7)',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '20px',
        }}
      >
        {/* Animated Brand Badge */}
        <div
          style={{
            width: '64px',
            height: '64px',
            borderRadius: '20px',
            background: 'linear-gradient(135deg, #354A60 0%, #2A3B4D 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#F4F1EA',
            boxShadow: '0 8px 24px rgba(53, 74, 96, 0.25)',
            position: 'relative',
          }}
        >
          <Layers size={30} />
          <div
            style={{
              position: 'absolute',
              top: '-4px',
              right: '-4px',
              width: '18px',
              height: '18px',
              borderRadius: '50%',
              background: '#C49A6C',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFF',
            }}
          >
            <Sparkles size={10} />
          </div>
        </div>

        {/* Title */}
        <div>
          <h2
            style={{
              fontSize: '20px',
              fontWeight: 700,
              color: '#30343A',
              margin: '0 0 6px 0',
              letterSpacing: '-0.02em',
            }}
          >
            Punggawa Autonomous Office
          </h2>
          <p
            style={{
              fontSize: '13px',
              color: '#666B74',
              margin: 0,
            }}
          >
            Memuat lingkungan visual 3D & workstation agen...
          </p>
        </div>

        {/* Progress Bar Container */}
        <div style={{ width: '100%' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '12px',
              fontWeight: 600,
              color: '#4B505A',
              marginBottom: '8px',
            }}
          >
            <span>{getLoadingHint()}</span>
            <span className="mono" style={{ color: '#354A60' }}>
              {displayProgress}%
            </span>
          </div>

          <div
            style={{
              width: '100%',
              height: '8px',
              borderRadius: '999px',
              backgroundColor: 'rgba(214, 210, 202, 0.6)',
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            <div
              style={{
                width: `${displayProgress}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #C49A6C 0%, #354A60 100%)',
                borderRadius: '999px',
                transition: 'width 0.25s ease-out',
              }}
            />
          </div>

          {cleanItemName && (
            <div
              className="mono"
              style={{
                fontSize: '10px',
                color: '#8A8F99',
                marginTop: '6px',
                textAlign: 'left',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              Asset: {cleanItemName}
            </div>
          )}
        </div>

        {/* Quick Skip to 2D Mode Button */}
        {onSwitchTo2D && (
          <div
            style={{
              width: '100%',
              paddingTop: '12px',
              borderTop: '1px solid rgba(214, 210, 202, 0.4)',
            }}
          >
            <button
              onClick={onSwitchTo2D}
              style={{
                width: '100%',
                padding: '10px 16px',
                borderRadius: '12px',
                backgroundColor: 'rgba(53, 74, 96, 0.08)',
                color: '#354A60',
                border: '1px solid rgba(53, 74, 96, 0.2)',
                fontSize: '12.5px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(53, 74, 96, 0.14)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(53, 74, 96, 0.08)';
              }}
            >
              <Zap size={14} style={{ color: '#C49A6C' }} />
              <span>Buka Cepat Mode 2D (Hemat Kuota)</span>
              <ArrowRight size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

