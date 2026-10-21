import React from 'react';
import { AlertTriangle, RefreshCw, X, ExternalLink } from 'lucide-react';
import { ServicesHealthResponse } from '../types';

export interface ServiceAlertBannerProps {
  healthData?: ServicesHealthResponse | null;
  isDegraded?: boolean;
  isRechecking?: boolean;
  isDismissed?: boolean;
  onRecheck?: () => void;
  onDismiss?: () => void;
  onOpenDetailsModal?: () => void;
  onViewDetails?: () => void;
}

export function ServiceAlertBanner({
  healthData,
  isDegraded,
  isRechecking = false,
  isDismissed = false,
  onRecheck,
  onDismiss,
  onOpenDetailsModal,
  onViewDetails,
}: ServiceAlertBannerProps) {
  if (isDismissed) {
    return null;
  }

  if (!healthData || healthData.overall_status !== 'degraded') {
    return null;
  }

  const downServices = healthData.services.filter((s) => s.status !== 'healthy');
  if (downServices.length === 0) {
    return null;
  }

  const handleOpenDetails = onViewDetails || onOpenDetailsModal;

  return (
    <div
      style={{
        position: 'absolute',
        top: '82px',
        left: '20px',
        right: '20px',
        zIndex: 50,
        pointerEvents: 'auto',
        background: 'rgba(185, 28, 28, 0.92)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        border: '1px solid rgba(248, 113, 113, 0.45)',
        borderRadius: '14px',
        padding: '10px 18px',
        color: '#FFFFFF',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '14px',
        boxShadow: '0 8px 30px rgba(185, 28, 28, 0.4), 0 0 16px rgba(239, 68, 68, 0.3)',
        animation: 'slideDown 0.3s ease-out',
      }}
    >
      {/* Left Icon & Outage Message */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '10px',
            background: 'rgba(255, 255, 255, 0.18)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            animation: 'pulse 1.8s infinite',
          }}
        >
          <AlertTriangle size={18} color="#FEF2F2" />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '12.5px', fontWeight: 800, letterSpacing: '0.02em', color: '#FFFFFF' }}>
              ⚠️ Service Outage Terdeteksi!
            </span>
            <span
              style={{
                fontSize: '10px',
                fontWeight: 700,
                background: 'rgba(0, 0, 0, 0.25)',
                padding: '2px 8px',
                borderRadius: '6px',
                color: '#FCA5A5',
                border: '1px solid rgba(254, 202, 202, 0.25)',
              }}
            >
              {downServices.length} Microservice Down
            </span>
          </div>

          <div
            style={{
              fontSize: '11.5px',
              color: '#FEE2E2',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {downServices.map((s, idx) => (
              <span key={s.id}>
                {idx > 0 && <span style={{ opacity: 0.6 }}> • </span>}
                <strong>{s.name}</strong> ({s.url.replace('https://', '').replace('/', '')}):{' '}
                <span style={{ color: '#FECACA', textDecoration: 'underline' }}>{s.error || 'Unhealthy'}</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Right Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        {handleOpenDetails && (
          <button
            onClick={handleOpenDetails}
            style={{
              background: 'rgba(255, 255, 255, 0.15)',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              color: '#FFFFFF',
              borderRadius: '8px',
              padding: '6px 12px',
              fontSize: '11.5px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              transition: 'all 0.15s ease',
            }}
            title="Buka rincian status semua service"
          >
            <span>Rincian</span>
            <ExternalLink size={12} />
          </button>
        )}

        <button
          onClick={onRecheck}
          disabled={isRechecking}
          style={{
            background: '#FFFFFF',
            border: 'none',
            color: '#991B1B',
            borderRadius: '8px',
            padding: '6px 14px',
            fontSize: '11.5px',
            fontWeight: 800,
            cursor: isRechecking ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
            transition: 'all 0.15s ease',
          }}
          title="Jalankan ulang HTTP health check ke semua service"
        >
          <RefreshCw size={12} className={isRechecking ? 'animate-spin' : ''} />
          <span>{isRechecking ? 'Memverifikasi...' : 'Cek Ulang'}</span>
        </button>

        <button
          onClick={onDismiss}
          style={{
            background: 'none',
            border: 'none',
            color: '#FCA5A5',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '6px',
            transition: 'color 0.15s ease',
          }}
          title="Tutup banner peringatan sementara"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}
