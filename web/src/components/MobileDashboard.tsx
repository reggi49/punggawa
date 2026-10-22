import React, { useState } from 'react';
import {
  Cpu,
  Wifi,
  WifiOff,
  Activity,
  Server,
  Layers,
  Sparkles,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Briefcase,
  Terminal,
  ExternalLink,
  Zap,
  Sliders,
  Send,
  Calendar,
} from 'lucide-react';
import { WORKER_PROFILES, WorkerId, ServicesHealthResponse } from '../types';
import { STATUS_LABELS, getHumanStatus } from '../utils/statusLabels';
import { LogEntry } from '../hooks/useEventStream';
import { CharacterVisualState } from '../simulation/useAmbientOffice';
import { CareerOpsModal } from './CareerOpsModal';

interface MobileDashboardProps {
  currentNode: string;
  threadId?: string;
  status?: string;
  message: string;
  details?: Record<string, any>;
  logs: LogEntry[];
  connected: boolean;
  characterStates?: Record<WorkerId, CharacterVisualState> | null;
  healthData?: ServicesHealthResponse | null;
  isDegraded?: boolean;
  isRechecking?: boolean;
  onSwitchTo3D?: () => void;
  onSimulateNode?: (node: string) => void;
  onReconnect?: () => void;
  onRecheckHealth?: () => void;
}

export function MobileDashboard({
  currentNode,
  threadId = '',
  status = 'idle',
  message,
  details = {},
  logs,
  connected,
  characterStates,
  healthData,
  isDegraded = false,
  isRechecking = false,
  onSwitchTo3D,
  onReconnect,
  onRecheckHealth,
}: MobileDashboardProps) {
  const [activeTab, setActiveTab] = useState<'agents' | 'logs' | 'health'>('agents');
  const [careerOpsOpen, setCareerOpsOpen] = useState(false);
  const [quickDispatchOpen, setQuickDispatchOpen] = useState(false);
  const [dispatchStatus, setDispatchStatus] = useState<string | null>(null);

  const humanStatus = getHumanStatus(currentNode);
  const isRunning = status === 'running' || status === 'in_progress';
  const isError = status === 'failed' || status === 'error' || currentNode.includes('failed');

  // Trigger quick preset
  const handleQuickTrigger = async (presetType: 'github' | 'dongeng' | 'server_check' | 'scout') => {
    if (presetType === 'scout') {
      setCareerOpsOpen(true);
      return;
    }

    setDispatchStatus('Mengirim instruksi...');
    try {
      const token = localStorage.getItem('punggawa_auth_token') || '';
      let payload: any = {};

      if (presetType === 'github') {
        payload = {
          action: 'trend-article',
          source: 'github',
          category: 'programming',
          prompt: 'Python trending weekly repository',
          lang: 'python',
        };
      } else if (presetType === 'dongeng') {
        payload = {
          action: 'dongeng',
          type: 'dongeng',
          category: 'cerita',
          prompt: 'Kisah misteri lereng bukit berkabut',
        };
      } else if (presetType === 'server_check') {
        payload = {
          action: 'housekeeping',
          type: 'audit',
        };
      }

      const res = await fetch('/api/dispatch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        setDispatchStatus(`✅ Diluncurkan: ${data.task_id || 'OK'}`);
      } else if (res.status === 401) {
        setDispatchStatus('❌ Butuh login pengelola');
      } else {
        setDispatchStatus('❌ Gagal memicu task');
      }
    } catch (e: any) {
      setDispatchStatus(`❌ Error: ${e.message}`);
    } finally {
      setTimeout(() => setDispatchStatus(null), 3000);
    }
  };

  const agentIds: WorkerId[] = ['stark', 'usagi', 'bayzero', 'scout'];

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        minHeight: '100vh',
        backgroundColor: '#E8E4DA',
        color: '#30343A',
        fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        paddingBottom: '80px',
        overflowX: 'hidden',
        overflowY: 'auto',
        WebkitOverflowScrolling: 'touch',
      }}
    >
      {/* 1. TOP STICKY HEADER */}
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 40,
          backgroundColor: 'rgba(244, 241, 234, 0.95)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          borderBottom: '1px solid rgba(196, 154, 108, 0.3)',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #354A60, #8DA895)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFF',
              boxShadow: '0 2px 8px rgba(53, 74, 96, 0.2)',
            }}
          >
            <Cpu size={18} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '14px', fontWeight: 800, letterSpacing: '0.02em', color: '#30343A' }}>
                PUNGGAWA
              </span>
              <span
                style={{
                  fontSize: '9px',
                  fontWeight: 700,
                  backgroundColor: '#8DA895',
                  color: '#FFF',
                  padding: '2px 5px',
                  borderRadius: '4px',
                }}
              >
                2D ECO
              </span>
            </div>
            <p style={{ fontSize: '10px', color: '#7A7E85', margin: 0 }}>Mobile Ops Center</p>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Connection Status Pill */}
          <button
            onClick={onReconnect}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 8px',
              borderRadius: '8px',
              fontSize: '11px',
              fontWeight: 600,
              border: 'none',
              backgroundColor: connected ? 'rgba(141, 168, 149, 0.2)' : 'rgba(217, 128, 120, 0.2)',
              color: connected ? '#2E693F' : '#A33B32',
              cursor: 'pointer',
            }}
            title={connected ? 'SSE Terhubung (Klik untuk refresh)' : 'Terputus (Klik reconnect)'}
          >
            {connected ? <Wifi size={12} /> : <WifiOff size={12} />}
            <span>{connected ? 'Live' : 'Off'}</span>
          </button>

          {/* Switch to 3D View Button */}
          {onSwitchTo3D && (
            <button
              onClick={onSwitchTo3D}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '6px 12px',
                borderRadius: '10px',
                backgroundColor: '#354A60',
                color: '#FFF',
                border: 'none',
                fontSize: '11px',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 2px 6px rgba(53, 74, 96, 0.25)',
              }}
            >
              <Sparkles size={12} style={{ color: '#C49A6C' }} />
              <span>Buka 3D</span>
            </button>
          )}
        </div>
      </header>

      {/* 2. SUB-HERO: ACTIVE PIPELINE / STATUS BANNER */}
      <div style={{ padding: '16px 16px 8px 16px' }}>
        <div
          className="warm-panel"
          style={{
            borderRadius: '16px',
            padding: '16px',
            border: isError
              ? '1px solid rgba(217, 128, 120, 0.6)'
              : isRunning
              ? '1px solid rgba(196, 154, 108, 0.5)'
              : '1px solid rgba(255, 255, 255, 0.6)',
            boxShadow: '0 4px 16px rgba(48, 52, 58, 0.05)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: isError ? '#D98078' : isRunning ? '#C49A6C' : '#8DA895',
                  display: 'inline-block',
                }}
              />
              <span style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {isRunning ? 'PIPELINE AKTIF' : isError ? 'PIPELINE ERROR' : 'SISTEM STANDBY'}
              </span>
            </div>
            <span
              className="mono"
              style={{
                fontSize: '10px',
                color: '#8A8F99',
                backgroundColor: 'rgba(48, 52, 58, 0.06)',
                padding: '2px 6px',
                borderRadius: '4px',
              }}
            >
              {currentNode || 'IDLE'}
            </span>
          </div>

          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 700, margin: '0 0 4px 0', color: '#30343A' }}>
              {humanStatus.label}
            </h3>
            <p style={{ fontSize: '12px', color: '#5A5F69', margin: 0, lineHeight: 1.4 }}>
              {message || humanStatus.description}
            </p>
          </div>

          {threadId && (
            <div style={{ fontSize: '10.5px', color: '#8A8F99' }}>
              Thread: <span className="mono">{threadId.slice(0, 16)}...</span>
            </div>
          )}
        </div>
      </div>

      {/* 3. QUICK ACTION BAR (MOBILE SHORTCUTS) */}
      <div style={{ padding: '0 16px 8px 16px' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '8px',
          }}
        >
          <button
            onClick={() => handleQuickTrigger('github')}
            style={{
              padding: '10px 6px',
              borderRadius: '12px',
              border: '1px solid rgba(53, 74, 96, 0.2)',
              backgroundColor: 'rgba(244, 241, 234, 0.9)',
              color: '#354A60',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: '18px' }}>🐙</span>
            <span style={{ fontSize: '10px', fontWeight: 700 }}>GitHub</span>
          </button>

          <button
            onClick={() => handleQuickTrigger('dongeng')}
            style={{
              padding: '10px 6px',
              borderRadius: '12px',
              border: '1px solid rgba(217, 128, 120, 0.3)',
              backgroundColor: 'rgba(244, 241, 234, 0.9)',
              color: '#D98078',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: '18px' }}>🦊</span>
            <span style={{ fontSize: '10px', fontWeight: 700 }}>Dongeng</span>
          </button>

          <button
            onClick={() => handleQuickTrigger('server_check')}
            style={{
              padding: '10px 6px',
              borderRadius: '12px',
              border: '1px solid rgba(141, 168, 149, 0.3)',
              backgroundColor: 'rgba(244, 241, 234, 0.9)',
              color: '#466850',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: '18px' }}>🛡️</span>
            <span style={{ fontSize: '10px', fontWeight: 700 }}>Infra</span>
          </button>

          <button
            onClick={() => handleQuickTrigger('scout')}
            style={{
              padding: '10px 6px',
              borderRadius: '12px',
              border: '1px solid rgba(13, 148, 136, 0.3)',
              backgroundColor: 'rgba(244, 241, 234, 0.9)',
              color: '#0D9488',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: '18px' }}>🎯</span>
            <span style={{ fontSize: '10px', fontWeight: 700 }}>Career</span>
          </button>
        </div>

        {dispatchStatus && (
          <div
            style={{
              marginTop: '8px',
              padding: '8px 12px',
              borderRadius: '8px',
              backgroundColor: '#354A60',
              color: '#FFF',
              fontSize: '11px',
              fontWeight: 600,
              textAlign: 'center',
            }}
          >
            {dispatchStatus}
          </div>
        )}
      </div>

      {/* 4. SEGMENTED NAVIGATION TABS */}
      <div style={{ padding: '8px 16px' }}>
        <div
          style={{
            display: 'flex',
            backgroundColor: 'rgba(214, 210, 202, 0.5)',
            borderRadius: '12px',
            padding: '3px',
          }}
        >
          <button
            onClick={() => setActiveTab('agents')}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: '9px',
              border: 'none',
              backgroundColor: activeTab === 'agents' ? '#FFF' : 'transparent',
              color: activeTab === 'agents' ? '#30343A' : '#686D76',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: activeTab === 'agents' ? '0 2px 6px rgba(0,0,0,0.06)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            Multi-Agent ({agentIds.length})
          </button>

          <button
            onClick={() => setActiveTab('logs')}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: '9px',
              border: 'none',
              backgroundColor: activeTab === 'logs' ? '#FFF' : 'transparent',
              color: activeTab === 'logs' ? '#30343A' : '#686D76',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: activeTab === 'logs' ? '0 2px 6px rgba(0,0,0,0.06)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            Live Logs ({logs.length})
          </button>

          <button
            onClick={() => setActiveTab('health')}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: '9px',
              border: 'none',
              backgroundColor: activeTab === 'health' ? '#FFF' : 'transparent',
              color: activeTab === 'health' ? '#30343A' : '#686D76',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: activeTab === 'health' ? '0 2px 6px rgba(0,0,0,0.06)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            Health {isDegraded ? '⚠️' : '✅'}
          </button>
        </div>
      </div>

      {/* 5. TAB CONTENT AREA */}
      <div style={{ padding: '8px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {/* TAB 1: AGENTS */}
        {activeTab === 'agents' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {agentIds.map((id) => {
              const profile = WORKER_PROFILES[id];
              const state = characterStates ? characterStates[id] : null;
              const isActive = state?.isActive || false;
              const actualState = state?.actualState || 'Idle';
              const activityLabel = state?.ambientLabel || (isActive ? 'Sedang bekerja...' : 'Standby di workstation');

              const getEmoji = (agentId: WorkerId) => {
                switch (agentId) {
                  case 'stark':
                    return '⚡';
                  case 'usagi':
                    return '🦊';
                  case 'bayzero':
                    return '🛡️';
                  case 'scout':
                    return '🎯';
                  default:
                    return '🤖';
                }
              };

              return (
                <div
                  key={id}
                  className="warm-panel"
                  style={{
                    borderRadius: '16px',
                    padding: '14px 16px',
                    border: isActive
                      ? `1.5px solid ${profile.color}`
                      : '1px solid rgba(255, 255, 255, 0.6)',
                    boxShadow: '0 2px 10px rgba(48, 52, 58, 0.04)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div
                        style={{
                          width: '40px',
                          height: '40px',
                          borderRadius: '12px',
                          backgroundColor: profile.color,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '20px',
                          color: '#FFF',
                          boxShadow: `0 4px 12px ${profile.color}40`,
                        }}
                      >
                        {getEmoji(id)}
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontSize: '14px', fontWeight: 800, color: '#30343A' }}>
                            {profile.name}
                          </span>
                          <span
                            style={{
                              fontSize: '10px',
                              color: '#7A7E85',
                              fontWeight: 600,
                            }}
                          >
                            ({profile.codeName})
                          </span>
                        </div>
                        <p style={{ fontSize: '11px', color: '#666B74', margin: 0 }}>
                          {profile.role}
                        </p>
                      </div>
                    </div>

                    {/* Status Badge */}
                    <span
                      style={{
                        fontSize: '10.5px',
                        fontWeight: 700,
                        padding: '3px 8px',
                        borderRadius: '6px',
                        backgroundColor: isActive
                          ? 'rgba(196, 154, 108, 0.2)'
                          : 'rgba(141, 168, 149, 0.15)',
                        color: isActive ? '#8E602A' : '#466850',
                      }}
                    >
                      {actualState.toUpperCase()}
                    </span>
                  </div>

                  {/* Activity Description */}
                  <div
                    style={{
                      fontSize: '12px',
                      color: '#4A4E57',
                      backgroundColor: 'rgba(255, 255, 255, 0.5)',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      lineHeight: 1.4,
                    }}
                  >
                    {activityLabel}
                  </div>

                  {/* Agent Specific Action */}
                  {id === 'scout' && (
                    <button
                      onClick={() => setCareerOpsOpen(true)}
                      style={{
                        padding: '8px 12px',
                        borderRadius: '10px',
                        backgroundColor: 'rgba(13, 148, 136, 0.1)',
                        color: '#0D9488',
                        border: '1px solid rgba(13, 148, 136, 0.3)',
                        fontSize: '12px',
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                      }}
                    >
                      <Briefcase size={14} />
                      <span>Buka Peluang Karir Scout</span>
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* TAB 2: LIVE LOGS */}
        {activeTab === 'logs' && (
          <div
            style={{
              backgroundColor: '#1E222A',
              color: '#E0E4EC',
              borderRadius: '16px',
              padding: '16px',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px',
              lineHeight: 1.6,
              maxHeight: '480px',
              overflowY: 'auto',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '12px',
                paddingBottom: '8px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#8DA895' }}>
                <Terminal size={14} />
                <span style={{ fontWeight: 700 }}>Punggawa SSE Feed</span>
              </div>
              <span style={{ fontSize: '10px', color: '#7A8291' }}>{logs.length} events</span>
            </div>

            {logs.length === 0 ? (
              <div style={{ color: '#6A7282', textAlign: 'center', padding: '24px 0' }}>
                Belum ada aktivitas baru tercatat...
              </div>
            ) : (
              logs.map((log, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '6px 0',
                    borderBottom: '1px dashed rgba(255, 255, 255, 0.05)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#7E8696', fontSize: '9.5px' }}>
                    <span style={{ color: log.status === 'failed' ? '#D98078' : '#C49A6C' }}>
                      [{log.node || 'EVENT'}]
                    </span>
                    <span>{log.time ? new Date(log.time).toLocaleTimeString() : ''}</span>
                  </div>
                  <div style={{ color: log.status === 'failed' ? '#F87171' : '#E0E4EC', marginTop: '2px' }}>
                    {log.message}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 3: SYSTEM HEALTH */}
        {activeTab === 'health' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div
              className="warm-panel"
              style={{
                borderRadius: '16px',
                padding: '16px',
                border: isDegraded ? '1px solid #D98078' : '1px solid #8DA895',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <h4 style={{ margin: '0 0 4px 0', fontSize: '14px', fontWeight: 700 }}>
                  {isDegraded ? 'Perhatian: Ada Service Terganggu' : 'Semua Microservice Sehat'}
                </h4>
                <p style={{ margin: 0, fontSize: '11px', color: '#666B74' }}>
                  Dipantau secara berkala oleh Bay-Zero (SRE Lead)
                </p>
              </div>

              {onRecheckHealth && (
                <button
                  onClick={onRecheckHealth}
                  disabled={isRechecking}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '10px',
                    backgroundColor: '#354A60',
                    color: '#FFF',
                    border: 'none',
                    fontSize: '11px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <RotateCcw size={12} className={isRechecking ? 'spin' : ''} />
                  <span>{isRechecking ? 'Cek...' : 'Cek Ulang'}</span>
                </button>
              )}
            </div>

            {/* Individual Services */}
            {healthData?.services &&
              healthData.services.map((srv) => (
                <div
                  key={srv.id}
                  className="warm-panel"
                  style={{
                    borderRadius: '12px',
                    padding: '12px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    border: '1px solid rgba(255, 255, 255, 0.6)',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#30343A' }}>
                      {srv.name}
                    </div>
                    <div style={{ fontSize: '10.5px', color: '#7E848F' }}>
                      {srv.latency_ms > 0 ? `${srv.latency_ms} ms` : 'N/A'} • {srv.url}
                    </div>
                  </div>

                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      padding: '3px 8px',
                      borderRadius: '6px',
                      backgroundColor:
                        srv.status === 'healthy' ? 'rgba(141, 168, 149, 0.2)' : 'rgba(217, 128, 120, 0.2)',
                      color: srv.status === 'healthy' ? '#2E693F' : '#A33B32',
                    }}
                  >
                    {srv.status === 'healthy' ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* 6. CAREER OPS MODAL IF TRIGGERED */}
      <CareerOpsModal
        isOpen={careerOpsOpen}
        onClose={() => setCareerOpsOpen(false)}
        onOpenDispatch={() => {
          setCareerOpsOpen(false);
          // can open dispatch
        }}
      />
    </div>
  );
}
