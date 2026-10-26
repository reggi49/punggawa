import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import {
  Terminal,
  Wifi,
  WifiOff,
  Send,
  ChevronDown,
  ChevronUp,
  Cpu,
  Users,
  Sparkles,
  Layers,
  FileText,
  AlertCircle,
  Play,
  Lock,
  Unlock,
  LogOut,
  CheckCircle2,
  Check,
  Settings2,
  Sliders,
  ShieldCheck,
  Calendar,
  ExternalLink,
  RefreshCw,
  AlertTriangle,
  Server,
  Trash2,
  Briefcase,
  Code2,
  Bug,
  RotateCcw,
  Archive,
} from 'lucide-react';
import { STATUS_LABELS, getHumanStatus } from '../utils/statusLabels';
import { WORKER_PROFILES, WorkerId, ActualAgentState, ServicesHealthResponse } from '../types';
import { LogEntry } from '../hooks/useEventStream';
import { CharacterVisualState } from '../simulation/useAmbientOffice';
import { ServiceAlertBanner } from './ServiceAlertBanner';
import { CareerOpsModal } from './CareerOpsModal';

export interface TaskPreset {
  id: string;
  agent: 'stark' | 'usagi' | 'bayzero' | 'clara' | 'scout';
  agentName: string;
  agentRole: string;
  title: string;
  description: string;
  type: 'article' | 'dongeng' | 'chat' | 'job_hunt' | string;
  category: string;
  defaultUrls?: string;
  videoId?: string;
  source?: 'github' | 'gnews';
  lang?: string;
  icon: string;
  badge: string;
}

export const TASK_PRESETS: TaskPreset[] = [
  // STARK (Tech Writer & Trend Researcher)
  {
    id: 'stark_github_trending_global',
    agent: 'stark',
    agentName: 'Stark',
    agentRole: 'Tech Architect & Writer',
    title: 'GitHub Trending: Repositori Internasional Viral',
    description: 'Menarik repositori open-source global teratas dari GitHub Trending Weekly (international / all spoken languages) dan menyusun artikel edukatif.',
    type: 'article',
    category: 'programming',
    source: 'github',
    icon: '🐙',
    badge: 'GitHub Global',
  },
  {
    id: 'stark_gnews_tech_global',
    agent: 'stark',
    agentName: 'Stark',
    agentRole: 'Tech Architect & Writer',
    title: 'Google News: Headline Teknologi Global (International)',
    description: 'Mengambil headline berita teknologi paling hangat langsung dari section feed resmi Google News Technology International (English).',
    type: 'article',
    category: 'technology',
    source: 'gnews',
    lang: 'en',
    icon: '📰',
    badge: 'Google News EN',
  },
  {
    id: 'stark_github_trending',
    agent: 'stark',
    agentName: 'Stark',
    agentRole: 'Tech Architect & Writer',
    title: 'GitHub Trending: Bedah Repositori Python Mingguan',
    description: 'Menarik repositori open-source Python paling viral di GitHub Trending Weekly, menganalisis arsitektur kodenya, dan menyusun artikel edukatif.',
    type: 'article',
    category: 'programming',
    source: 'github',
    lang: 'python',
    icon: '🐍',
    badge: 'Python Trend',
  },
  {
    id: 'stark_ai_trends_2026',
    agent: 'stark',
    agentName: 'Stark',
    agentRole: 'Tech Architect & Writer',
    title: 'Tren AI Agent & Autonomous Coding 2026',
    description: 'Riset tren arsitektur cognitive agents, pair programming otonom, dan benchmarking model reasoning terkini.',
    type: 'article',
    category: 'technology',
    defaultUrls: 'https://news.ycombinator.com',
    icon: '⚡',
    badge: 'Technology',
  },
  {
    id: 'stark_langgraph_arch',
    agent: 'stark',
    agentName: 'Stark',
    agentRole: 'Tech Architect & Writer',
    title: 'Arsitektur Multi-Agent dengan LangGraph & Redis',
    description: 'Panduan teknis orkestrasi multi-agent, checkpointer state graph, memory persistence, dan distributed queue.',
    type: 'article',
    category: 'programming',
    defaultUrls: 'https://langchain-ai.github.io/langgraph',
    icon: '🧠',
    badge: 'Architecture',
  },
  {
    id: 'stark_web3d_spatial',
    agent: 'stark',
    agentName: 'Stark',
    agentRole: 'Tech Architect & Writer',
    title: 'Modern Web 3D & Spatial UI dengan Three.js & R3F',
    description: 'Studi komprehensif implementasi visualisasi kantor virtual interaktif 60fps dengan React Three Fiber.',
    type: 'article',
    category: 'technology',
    defaultUrls: 'https://threejs.org',
    icon: '🌐',
    badge: '3D Web',
  },

  // USAGI (Media & Dongeng Curator)
  {
    id: 'usagi_dongeng_kancil',
    agent: 'usagi',
    agentName: 'Usagi',
    agentRole: 'Dongeng & Media Curator',
    title: 'Dongeng Nusantara: Kisah Si Kancil & Buaya Cerdik',
    description: 'Kurasi naskah fabel edukatif nusantara, generate cover thumbnail, dan posting ke CMS Dongeng Bogorstore.',
    type: 'dongeng',
    category: 'dongeng',
    videoId: 'UC7GZguUCh8gdEs-VKhWqkWA',
    icon: '🦊',
    badge: 'YouTube CMS',
  },
  {
    id: 'usagi_dongeng_sangkuriang',
    agent: 'usagi',
    agentName: 'Usagi',
    agentRole: 'Dongeng & Media Curator',
    title: 'Legenda: Sangkuriang & Gunung Tangkuban Perahu',
    description: 'Penyusunan naskah cerita rakyat Jawa Barat dengan visual cover dan pesan moral kearifan lokal.',
    type: 'dongeng',
    category: 'dongeng',
    videoId: 'UCaMrqakJglh9VQItR50pQwA',
    icon: '⛰️',
    badge: 'Legenda',
  },
  {
    id: 'usagi_visual_cover',
    agent: 'usagi',
    agentName: 'Usagi',
    agentRole: 'Dongeng & Media Curator',
    title: 'Studio Desain: Render Visual Cover & Media',
    description: 'Pembuatan thumbnail visual kreatif resolusi tinggi menggunakan palette Skandinavia modern.',
    type: 'article',
    category: 'general',
    icon: '🎨',
    badge: 'Design Art',
  },

  // BAY-ZERO (SOP Auditor & Lead Server Inspector)
  {
    id: 'bayzero_server_health',
    agent: 'bayzero',
    agentName: 'Bay-Zero',
    agentRole: 'SOP Auditor & Server Health Inspector',
    title: 'Pengecekan Kesehatan Server & Microservices Uptime',
    description: 'Inspeksi real-time seluruh microservice eksternal (Keselip, Kataku, Dongeng), latensi HTTP, konektivitas database & Redis, dan status rack server.',
    type: 'article',
    category: 'technology',
    icon: '🖥️',
    badge: 'Server Health',
  },
  {
    id: 'bayzero_cloud_security',
    agent: 'bayzero',
    agentName: 'Bay-Zero',
    agentRole: 'SOP Auditor & Server Health Inspector',
    title: 'Audit Keamanan Server & Hardening Cloud Gateway',
    description: 'Audit arsitektur keamanan server, verifikasi autentikasi token HMAC, mitigasi serangan DDoS, dan isolasi antrean Redis.',
    type: 'article',
    category: 'technology',
    icon: '🛡️',
    badge: 'Server Security',
  },
  {
    id: 'bayzero_audit_sop',
    agent: 'bayzero',
    agentName: 'Bay-Zero',
    agentRole: 'SOP Auditor & Server Health Inspector',
    title: 'Audit Kepatuhan SOP & Quality Gate Publikasi',
    description: 'Inspeksi menyeluruh struktur artikel, verifikasi standar editorial, dan deteksi kejanggalan sebelum rilis.',
    type: 'article',
    category: 'general',
    icon: '📋',
    badge: 'Quality Gate',
  },
  {
    id: 'bayzero_fact_check',
    agent: 'bayzero',
    agentName: 'Bay-Zero',
    agentRole: 'SOP Auditor & Server Health Inspector',
    title: 'Verifikasi Fakta, Sitasi Sumber & Plagiarisme',
    description: 'Validasi referensi web, akurasi kutipan teknis, dan verifikasi orisinalitas naskah.',
    type: 'article',
    category: 'general',
    icon: '🔍',
    badge: 'Fact-Check',
  },
  {
    id: 'bayzero_clean_system',
    agent: 'bayzero',
    agentName: 'Bay-Zero',
    agentRole: 'SOP Auditor & Server Health Inspector',
    title: 'Pembersihan Buffer Sistem & Maintenance Antrean',
    description: 'Pemeliharaan memori Redis, pembersihan riwayat log kedaluwarsa, dan auto-cleanup database PostgreSQL.',
    type: 'article',
    category: 'technology',
    icon: '🧹',
    badge: 'System Care',
  },
  {
    id: 'scout_analyze_url',
    agent: 'scout',
    agentName: 'Scout',
    agentRole: 'Career Intelligence Lead',
    title: 'Analisis Mendalam Loker dari URL',
    description: 'Evaluasi keselarasan kualifikasi A–H, Dual-Scoring (Fit & Quality), deteksi ATS, Skill Gap Heatmap, serta Tailored Cover Letter.',
    type: 'job_hunt',
    category: 'career_ops',
    icon: '🎯',
    badge: 'Career-Ops',
  },
  {
    id: 'scout_auto_scout_remote',
    agent: 'scout',
    agentName: 'Scout',
    agentRole: 'Career Intelligence Lead',
    title: 'Auto-Scout Loker Remote (RemoteOK)',
    description: 'Mencari dan menyaring lowongan remote engineering aktif di RemoteOK yang paling cocok dengan skill profil kandidat.',
    type: 'job_hunt',
    category: 'career_ops',
    icon: '🌐',
    badge: 'Auto-Scout',
  },
];

interface HUDOverlayProps {
  currentNode: string;
  threadId: string;
  status: string;
  message: string;
  details: Record<string, any>;
  logs: LogEntry[];
  connected: boolean;
  characterStates?: Record<WorkerId, CharacterVisualState> | null;
  onSimulateNode: (node: string, msg?: string) => void;
  onReconnect: () => void;
  // Microservices Health Observability Props
  healthData?: ServicesHealthResponse | null;
  isDegraded?: boolean;
  isRechecking?: boolean;
  isAlertDismissed?: boolean;
  onDismissAlert?: () => void;
  onRecheckHealth?: () => void;
  onSwitchTo2D?: () => void;
  loadingLogs?: boolean;
  onRefreshLogs?: () => void;
}

export function HUDOverlay({
  currentNode,
  threadId,
  status,
  message,
  details,
  logs,
  connected,
  characterStates,
  onSimulateNode,
  onReconnect,
  healthData,
  isDegraded = false,
  isRechecking = false,
  isAlertDismissed = false,
  onDismissAlert,
  onRecheckHealth,
  onSwitchTo2D,
  loadingLogs = false,
  onRefreshLogs,
}: HUDOverlayProps) {
  const [terminalOpen, setTerminalOpen] = useState(false);
  const [teamPanelOpen, setTeamPanelOpen] = useState(true);
  const [stagePanelOpen, setStagePanelOpen] = useState(true);
  const [immersiveMode, setImmersiveMode] = useState(false);
  const [servicesModalOpen, setServicesModalOpen] = useState(false);
  const [logAgentFilter, setLogAgentFilter] = useState<string>('all');

  // Filter logs per agent
  const filteredLogs = useMemo(() => {
    if (logAgentFilter === 'all') return logs;
    return logs.filter((log) => {
      const rawActor = (log.agent_name || (log.details && log.details.agent_name) || '').toLowerCase();
      if (logAgentFilter === 'stark') return rawActor.includes('stark');
      if (logAgentFilter === 'usagi') return rawActor.includes('usagi');
      if (logAgentFilter === 'bayzero') return rawActor.includes('bay') || rawActor.includes('zero');
      if (logAgentFilter === 'clara') return rawActor.includes('clara') || rawActor.includes('scout') || rawActor.includes('job');
      if (logAgentFilter === 'janitor') return rawActor.includes('janitor') || rawActor.includes('droid');
      return true;
    });
  }, [logs, logAgentFilter]);

  // Authentication State
  const [authToken, setAuthToken] = useState<string | null>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('punggawa_auth_token');
    }
    return null;
  });
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authUsername, setAuthUsername] = useState('admin');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);

  // Developer Simulation Mode (Hidden by default, toggleable via ?dev=true or Ctrl+Alt+S)
  const [showDevSimulation, setShowDevSimulation] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return (
        new URLSearchParams(window.location.search).has('dev') ||
        new URLSearchParams(window.location.search).has('test') ||
        localStorage.getItem('punggawa_dev_mode') === 'true'
      );
    }
    return false;
  });

  // Task Dispatch Modal State
  const [dispatchModalOpen, setDispatchModalOpen] = useState(false);
  const [jobModalOpen, setJobModalOpen] = useState(false);
  const [activeAgentTab, setActiveAgentTab] = useState<'all' | 'stark' | 'usagi' | 'bayzero' | 'scout'>('all');
  const [selectedPresetId, setSelectedPresetId] = useState<string>('stark_ai_trends_2026');
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  const [customCategory, setCustomCategory] = useState('technology');
  const [customUrls, setCustomUrls] = useState('');
  const [customVideoId, setCustomVideoId] = useState('');
  const [dryRun, setDryRun] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [dispatchResult, setDispatchResult] = useState<string | null>(null);

  // Editorial Schedules & Observability State (Bay-Zero Planner)
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [schedulesList, setSchedulesList] = useState<any[]>([]);
  const [isLoadingSchedules, setIsLoadingSchedules] = useState(false);
  const [scheduleFilter, setScheduleFilter] = useState<'all' | 'pending' | 'in_progress' | 'completed' | 'failed' | 'discarded'>('all');
  const [scheduleDaysFilter, setScheduleDaysFilter] = useState<'7days' | '14days' | 'all'>('7days');
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
  const [expandedSchedErrorId, setExpandedSchedErrorId] = useState<string | null>(null);
  const [scheduleActionMsg, setScheduleActionMsg] = useState<string | null>(null);

  // Failure tracking per agent: Hanya catat kegagalan jika event TERAKHIR agent tersebut memang masih berstatus gagal
  const latestAgentFailures = useMemo(() => {
    const map: Record<string, string> = {};
    const seenAgents = new Set<WorkerId>();

    // Telusuri logs dari yang PALING BARU (index 0) ke yang terlama
    for (let i = 0; i < logs.length; i++) {
      const l = logs[i];
      const aName = ((l as any).agent_name || (l as any).agent || '').toLowerCase();
      let matchedId: WorkerId | null = null;
      if (aName.includes('stark')) matchedId = 'stark';
      else if (aName.includes('usagi')) matchedId = 'usagi';
      else if (aName.includes('bay') || aName.includes('zero')) matchedId = 'bayzero';
      else {
        const conf = getHumanStatus(l.node);
        if (conf.responsibleWorker && (conf.responsibleWorker as string) !== 'team') {
          matchedId = conf.responsibleWorker as WorkerId;
        }
      }

      if (!matchedId) continue;

      // Jika agent ini sudah diperiksa event terbarunya, abaikan log historis sebelumnya
      if (seenAgents.has(matchedId)) continue;
      seenAgents.add(matchedId);

      // Jika event terbaru berstatus failed atau node kegagalan:
      if (l.status === 'failed' || l.node === 'failed_node') {
        // Pengecualian khusus Uptime Alert: Jika sistem microservice saat ini sudah normal (!isDegraded),
        // atau jika pesan ini tentang service down yang kini sudah solved,
        // maka alert service down sebelumnya sudah SOLVED dan tidak boleh mem-block Bay-Zero lagi!
        if ((l.node === 'uptime_alert' || (l.message && l.message.includes('Peringatan Service Down'))) && !isDegraded) {
          continue;
        }
        map[matchedId] = (l as any).error || l.message || 'Task error';
      }
    }
    return map;
  }, [logs, isDegraded]);

  // Filtered schedules list based on selected tab and days window
  const filteredSchedules = useMemo(() => {
    let list = schedulesList;
    if (scheduleFilter === 'all') {
      list = list.filter((s) => s.status !== 'discarded');
    } else {
      list = list.filter((s) => s.status === scheduleFilter);
    }

    if (scheduleDaysFilter !== 'all') {
      const days = scheduleDaysFilter === '7days' ? 7 : 14;
      const now = new Date().getTime();
      const windowMs = days * 24 * 60 * 60 * 1000;
      list = list.filter((s) => {
        if (!s.scheduled_at) return true;
        const schedTime = new Date(s.scheduled_at).getTime();
        // Mencakup tugas dari [now - windowMs] sampai [now + windowMs]
        return schedTime >= (now - windowMs) && schedTime <= (now + windowMs);
      });
    }

    return list;
  }, [schedulesList, scheduleFilter, scheduleDaysFilter]);

  // Count per status category for tab badges
  const scheduleCounts = useMemo(() => {
    const counts = { all: 0, pending: 0, in_progress: 0, completed: 0, failed: 0, discarded: 0 };
    for (const s of schedulesList) {
      if (s.status === 'discarded') {
        counts.discarded++;
      } else {
        counts.all++;
        if (s.status in counts) {
          counts[s.status as keyof typeof counts]++;
        }
      }
    }
    return counts;
  }, [schedulesList]);

  const formatScheduleTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return (
        d.toLocaleDateString('id-ID', {
          weekday: 'short',
          day: 'numeric',
          month: 'short',
          hour: '2-digit',
          minute: '2-digit',
        }) + ' WIB'
      );
    } catch {
      return isoString;
    }
  };

  const fetchSchedules = async () => {
    setIsLoadingSchedules(true);
    try {
      // Ambil hingga 150 item termasuk discarded agar tab Recycle Bin dan filter terisi lengkap
      const res = await fetch('/api/schedules?limit=150&include_discarded=true');
      if (res.ok) {
        const data = await res.json();
        setSchedulesList(data.schedules || []);
      }
    } catch (err) {
      console.error('Failed to fetch schedules:', err);
    } finally {
      setIsLoadingSchedules(false);
    }
  };

  useEffect(() => {
    if (scheduleModalOpen) {
      fetchSchedules();
    }
  }, [scheduleModalOpen]);

  const handleGenerateWeeklyPlan = async () => {
    setIsLoadingSchedules(true);
    setScheduleActionMsg('Bay-Zero sedang mengurasi tren & menyusun kalender...');
    try {
      const res = await fetch('/api/schedules/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken || ''}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setSchedulesList(data.schedules || []);
        setScheduleActionMsg(`✅ ${data.message}`);
        setTimeout(() => setScheduleActionMsg(null), 3000);
      } else if (res.status === 401) {
        setScheduleActionMsg('❌ Memerlukan login pengelola untuk generate jadwal.');
        setTimeout(() => setScheduleActionMsg(null), 3000);
      }
    } catch (err: any) {
      setScheduleActionMsg(`❌ Gagal: ${err.message}`);
      setTimeout(() => setScheduleActionMsg(null), 3000);
    } finally {
      setIsLoadingSchedules(false);
    }
  };

  const handleTriggerScheduleNow = async (schedId: string) => {
    setScheduleActionMsg(`Memicu jadwal ${schedId}...`);
    try {
      const res = await fetch(`/api/schedules/${schedId}/trigger`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken || ''}`,
        },
      });
      if (res.ok) {
        setScheduleActionMsg('✅ Jadwal berhasil didorong ke antrean eksekusi!');
        fetchSchedules();
        setTimeout(() => setScheduleActionMsg(null), 3000);
      } else if (res.status === 401) {
        setScheduleActionMsg('❌ Memerlukan login pengelola.');
        setTimeout(() => setScheduleActionMsg(null), 3000);
      }
    } catch (err: any) {
      setScheduleActionMsg(`❌ Gagal: ${err.message}`);
      setTimeout(() => setScheduleActionMsg(null), 3000);
    }
  };

  const handleDeleteSchedule = async (schedId: string, title: string, permanent: boolean = false) => {
    const actionLabel = permanent ? 'hapus PERMANEN' : 'pindahkan ke Recycle Bin';
    if (!confirm(`Apakah Anda yakin ingin ${actionLabel} jadwal berikut?\n"${title}"`)) return;
    setScheduleActionMsg(`Memproses ${schedId}...`);
    try {
      const res = await fetch(`/api/schedules/${schedId}?force=true&permanent=${permanent}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken || ''}`,
        },
      });
      if (res.ok) {
        if (permanent) {
          setScheduleActionMsg('🗑️ Jadwal berhasil dihapus secara permanen!');
          setSchedulesList((prev) => prev.filter((s) => s.id !== schedId));
        } else {
          setScheduleActionMsg('📦 Jadwal dipindahkan ke Recycle Bin & di-blacklist dari planner.');
          // Update status lokal menjadi discarded
          setSchedulesList((prev) =>
            prev.map((s) => (s.id === schedId ? { ...s, status: 'discarded' } : s))
          );
        }
        setTimeout(() => setScheduleActionMsg(null), 3500);
      } else if (res.status === 401) {
        setScheduleActionMsg('❌ Memerlukan login pengelola untuk menghapus jadwal.');
        setTimeout(() => setScheduleActionMsg(null), 3000);
      } else {
        const err = await res.json().catch(() => ({}));
        setScheduleActionMsg(`❌ Gagal: ${err.detail || 'Tidak dapat menghapus jadwal'}`);
        setTimeout(() => setScheduleActionMsg(null), 3000);
      }
    } catch (err: any) {
      setScheduleActionMsg(`❌ Gagal: ${err.message}`);
      setTimeout(() => setScheduleActionMsg(null), 3000);
    }
  };

  const handleRestoreSchedule = async (schedId: string, title: string) => {
    setScheduleActionMsg(`Memulihkan jadwal ${schedId}...`);
    try {
      const res = await fetch(`/api/schedules/${schedId}/restore`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken || ''}`,
        },
      });
      if (res.ok) {
        setScheduleActionMsg(`♻️ Jadwal "${title.slice(0, 30)}..." berhasil dipulihkan ke antrean!`);
        setSchedulesList((prev) =>
          prev.map((s) => (s.id === schedId ? { ...s, status: 'pending', error_message: null } : s))
        );
        setTimeout(() => setScheduleActionMsg(null), 3500);
      } else {
        const err = await res.json().catch(() => ({}));
        setScheduleActionMsg(`❌ Gagal memulihkan: ${err.detail || 'Terjadi kesalahan'}`);
        setTimeout(() => setScheduleActionMsg(null), 3000);
      }
    } catch (err: any) {
      setScheduleActionMsg(`❌ Gagal: ${err.message}`);
      setTimeout(() => setScheduleActionMsg(null), 3000);
    }
  };

  const handleEmptyTrash = async () => {
    if (!confirm('Apakah Anda yakin ingin MENGOSONGKAN SELURUH Recycle Bin secara permanen?')) return;
    setScheduleActionMsg('Mengosongkan Recycle Bin...');
    try {
      const res = await fetch('/api/schedules/trash/empty', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken || ''}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setScheduleActionMsg(`🧹 ${data.message}`);
        setSchedulesList((prev) => prev.filter((s) => s.status !== 'discarded'));
        setTimeout(() => setScheduleActionMsg(null), 3500);
      } else {
        const err = await res.json().catch(() => ({}));
        setScheduleActionMsg(`❌ Gagal: ${err.detail || 'Tidak dapat mengosongkan sampah'}`);
        setTimeout(() => setScheduleActionMsg(null), 3000);
      }
    } catch (err: any) {
      setScheduleActionMsg(`❌ Gagal: ${err.message}`);
      setTimeout(() => setScheduleActionMsg(null), 3000);
    }
  };

  const handleCleanupDuplicates = async () => {
    if (!confirm('Bersihkan semua jadwal pending yang memiliki judul sama (duplikat)?')) return;
    setIsLoadingSchedules(true);
    setScheduleActionMsg('Membersihkan jadwal duplikat...');
    try {
      const res = await fetch('/api/schedules/cleanup-duplicates', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken || ''}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setScheduleActionMsg(`✅ Berhasil membersihkan ${data.deleted_count} jadwal duplikat!`);
        fetchSchedules();
        setTimeout(() => setScheduleActionMsg(null), 3500);
      } else {
        const err = await res.json().catch(() => ({}));
        setScheduleActionMsg(`❌ Gagal: ${err.detail || 'Tidak dapat membersihkan duplikat'}`);
        setTimeout(() => setScheduleActionMsg(null), 3000);
      }
    } catch (err: any) {
      setScheduleActionMsg(`❌ Gagal: ${err.message}`);
      setTimeout(() => setScheduleActionMsg(null), 3000);
    } finally {
      setIsLoadingSchedules(false);
    }
  };

  // Listen for developer simulation hotkey (Ctrl + Alt + S)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.altKey && e.key.toLowerCase() === 's') {
        setShowDevSimulation((prev) => {
          const next = !prev;
          localStorage.setItem('punggawa_dev_mode', next ? 'true' : 'false');
          return next;
        });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Suppress 3D labels and apply modal-active state to document.body
  useEffect(() => {
    const isModalActive = authModalOpen || dispatchModalOpen || scheduleModalOpen || servicesModalOpen || jobModalOpen;
    if (isModalActive) {
      document.body.classList.add('punggawa-modal-active');
    } else {
      document.body.classList.remove('punggawa-modal-active');
    }
    return () => {
      document.body.classList.remove('punggawa-modal-active');
    };
  }, [authModalOpen, dispatchModalOpen, scheduleModalOpen, servicesModalOpen, jobModalOpen]);

  // Deduplicate status labels for dev preview
  const uniqueStatusOptions = useMemo(() => {
    const seen = new Set<string>();
    const list: { key: string; label: string; icon: string }[] = [];
    for (const [key, conf] of Object.entries(STATUS_LABELS)) {
      if (!seen.has(conf.label)) {
        seen.add(conf.label);
        list.push({ key, label: conf.label, icon: conf.icon });
      }
    }
    return list;
  }, []);

  // Active selected preset object
  const currentPreset = useMemo(() => {
    return TASK_PRESETS.find((p) => p.id === selectedPresetId) || TASK_PRESETS[0];
  }, [selectedPresetId]);

  // Filtered presets based on tab
  const filteredPresets = useMemo(() => {
    if (activeAgentTab === 'all') return TASK_PRESETS;
    return TASK_PRESETS.filter((p) => p.agent === activeAgentTab);
  }, [activeAgentTab]);

  const humanStatus = getHumanStatus(currentNode);

  // Deteksi pipeline aktif
  const currentPipeline =
    details.action_type ||
    details.task_type ||
    (threadId.toLowerCase().includes('dongeng') ? 'dongeng' : 'article');

  const isDongeng = currentPipeline === 'dongeng';
  const isSOP = currentNode === 'sop_validator_node';
  const isIdle = currentNode === 'IDLE' || currentNode === 'idle_coffee' || currentNode === 'STREAM_INIT';

  // Menentukan status tiap worker
  const getWorkerStatus = (wId: WorkerId) => {
    if (isIdle) return { label: 'Santai ☕', active: false, color: '#8A8A82' };
    if (isSOP) {
      if (wId === 'bayzero') return { label: 'Auditing 🔍', active: true, color: '#facc15' };
      return { label: 'Observing 👀', active: false, color: '#8A8A82' };
    }
    if (isDongeng) {
      if (wId === 'usagi') return { label: 'Active 🎬', active: true, color: '#f43f5e' };
      return { label: 'Standby ⏳', active: false, color: '#8A8A82' };
    }
    // Default article
    if (wId === 'stark') return { label: 'Active ⚡', active: true, color: '#354A60' };
    return { label: 'Standby ⏳', active: false, color: '#8A8A82' };
  };

  const handleOpenDispatch = () => {
    if (!authToken) {
      setAuthModalOpen(true);
    } else {
      setDispatchModalOpen(true);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: authUsername, password: authPassword }),
      });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem('punggawa_auth_token', data.token);
        setAuthToken(data.token);
        setAuthModalOpen(false);
        setAuthPassword('');
        setDispatchModalOpen(true);
      } else {
        const err = await res.json().catch(() => ({ detail: 'Password salah' }));
        setAuthError(err.detail || 'Username atau password pengelola salah.');
      }
    } catch (err: any) {
      setAuthError(`Koneksi gagal: ${err.message}`);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('punggawa_auth_token');
    setAuthToken(null);
  };

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authToken) {
      setDispatchModalOpen(false);
      setAuthModalOpen(true);
      return;
    }

    setIsSubmitting(true);
    setDispatchResult(null);

    try {
      // Pengecekan server khusus Bay-Zero: picu pengecekan langsung dan buka modal observabilitas
      if (currentPreset.id === 'bayzero_server_health') {
        if (onRecheckHealth) {
          onRecheckHealth();
        }
        setDispatchResult('✅ Bay-Zero sedang menjalankan pengecekan server & microservices...');
        setTimeout(() => {
          setDispatchModalOpen(false);
          setDispatchResult(null);
          setServicesModalOpen(true);
        }, 1200);
        return;
      }

      const prompt =
        showCustomInput && customPrompt.trim()
          ? customPrompt.trim()
          : currentPreset.title;

      const category =
        showCustomInput && customCategory
          ? customCategory
          : currentPreset.category;

      const urls =
        showCustomInput
          ? customUrls
          : (currentPreset.defaultUrls || '');

      const videoId =
        showCustomInput
          ? customVideoId
          : (currentPreset.videoId || undefined);

      const type = currentPreset.type;

      const payload: Record<string, any> = {
        prompt,
        type,
        action: currentPreset.source ? 'trend-article' : (type === 'dongeng' ? 'dongeng' : (type === 'job_hunt' ? 'job_hunt' : 'article')),
        source: currentPreset.source,
        lang: currentPreset.lang,
        query: currentPreset.source === 'gnews' ? prompt : (type === 'job_hunt' ? prompt : undefined),
        job_url: urls || (prompt.startsWith('http') ? prompt : undefined),
        category,
        urls,
        video_id: videoId || undefined,
        dry_run: dryRun,
      };

      const res = await fetch('/api/dispatch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        setDispatchResult(`✅ Task Berhasil Diluncurkan: ${data.task_id}`);
        setTimeout(() => {
          setDispatchModalOpen(false);
          setDispatchResult(null);
        }, 2200);
      } else if (res.status === 401) {
        setDispatchResult('❌ Sesi pengelola kedaluwarsa. Silakan masukkan password kembali.');
        localStorage.removeItem('punggawa_auth_token');
        setAuthToken(null);
        setTimeout(() => {
          setDispatchModalOpen(false);
          setAuthModalOpen(true);
        }, 1200);
      } else {
        const err = await res.json().catch(() => ({ detail: 'Gagal mendispatch task' }));
        setDispatchResult(`❌ ${err.detail || 'Gagal mengirimkan task ke antrean'}`);
      }
    } catch (err: any) {
      setDispatchResult(`❌ Network Error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 10 }}>
      {/* 1. TOP HEADER BAR */}
      <div
        className="warm-panel"
        style={{
          pointerEvents: 'auto',
          margin: '16px 20px',
          padding: '12px 20px',
          borderRadius: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          border: '1px solid rgba(196, 154, 108, 0.3)',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
        }}
      >
        {/* Brand Logo & Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #354A60, #8DA895)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(225, 29, 72, 0.5)',
            }}
          >
            <Cpu size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '15px', fontWeight: 900, letterSpacing: '0.06em', margin: 0 }}>
                PUNGGAWA <span style={{ color: '#354A60' }}>OWLABS</span>
              </h1>
              <span
                style={{
                  fontSize: '9px',
                  fontWeight: 800,
                  padding: '2px 6px',
                  borderRadius: '6px',
                  background: '#8DA895',
                  color: '#ffffff',
                }}
              >
                MODERN
              </span>
            </div>
            <p style={{ fontSize: '11px', color: '#8A8A82', margin: 0 }}>
              Multi-Agent Orchestrator • Stark, Usagi, Bay-Zero & Clara
            </p>
          </div>
        </div>

        {/* Quick Actions & Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Developer Animation Simulation Dropdown (Hidden on clean public view; toggle with Ctrl+Alt+S or ?dev=true) */}
          {showDevSimulation && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'rgba(217, 128, 120, 0.12)',
                border: '1px dashed #D98078',
                borderRadius: '8px',
                padding: '4px 8px',
              }}
              title="Test mode aktif (Toggle: Ctrl+Alt+S)"
            >
              <span style={{ fontSize: '10px', color: '#D98078', fontWeight: 800 }}>DEV SIM:</span>
              <select
                value={currentNode}
                onChange={(e) => onSimulateNode(e.target.value)}
                style={{
                  background: 'rgba(244, 241, 234, 0.94)',
                  color: '#30343A',
                  border: '1px solid rgba(196, 154, 108, 0.3)',
                  borderRadius: '6px',
                  padding: '4px 8px',
                  fontSize: '11px',
                  fontWeight: 600,
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >
                {uniqueStatusOptions.map((opt) => (
                  <option key={opt.key} value={opt.key}>
                    {opt.icon} {opt.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Clean Presentation Mode / Immersive Mode Toggle */}
          <button
            onClick={() => setImmersiveMode(!immersiveMode)}
            style={{
              background: immersiveMode
                ? 'linear-gradient(135deg, #10B981, #059669)'
                : 'rgba(244, 241, 234, 0.94)',
              color: immersiveMode ? '#ffffff' : '#30343A',
              border: `1px solid ${immersiveMode ? '#10B981' : 'rgba(196, 154, 108, 0.4)'}`,
              borderRadius: '10px',
              padding: '7px 14px',
              fontSize: '12px',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              boxShadow: immersiveMode
                ? '0 4px 14px rgba(16, 185, 129, 0.35)'
                : '0 2px 8px rgba(0, 0, 0, 0.08)',
              letterSpacing: '0.02em',
              transition: 'all 0.2s ease',
            }}
            title="Clean Presentation Mode: Sembunyikan panel HUD agar tampilan 3D bersih"
          >
            <Sparkles size={14} color={immersiveMode ? '#ffffff' : '#D98078'} />
            <span>{immersiveMode ? 'ArchViz Clean ON' : 'ArchViz Clean View'}</span>
          </button>

          {/* Kalender Editorial Modal Button */}
          <button
            onClick={() => setScheduleModalOpen(true)}
            style={{
              background: 'rgba(244, 241, 234, 0.94)',
              color: '#30343A',
              border: '1px solid rgba(196, 154, 108, 0.4)',
              borderRadius: '10px',
              padding: '7px 14px',
              fontSize: '12px',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
              letterSpacing: '0.02em',
              transition: 'all 0.2s ease',
            }}
            title="Buka Kalender Editorial & Observability Jadwal Konten (Bay-Zero Planner)"
          >
            <Calendar size={14} color="#354A60" />
            <span>Kalender Konten</span>
          </button>

          {/* Peluang Karir (Career-Ops Clara) Modal Button */}
          <button
            onClick={() => setJobModalOpen(true)}
            style={{
              background: 'rgba(244, 241, 234, 0.94)',
              color: '#30343A',
              border: '1px solid rgba(212, 163, 115, 0.5)',
              borderRadius: '10px',
              padding: '7px 14px',
              fontSize: '12px',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
              letterSpacing: '0.02em',
              transition: 'all 0.2s ease',
            }}
            title="Buka Peluang Karir & Hasil Kurasi Loker (Career-Ops Clara)"
          >
            <Briefcase size={14} color="#D4A373" />
            <span>Peluang Karir</span>
          </button>

          {/* Mode 2D Eco Toggle Button */}
          {onSwitchTo2D && (
            <button
              onClick={onSwitchTo2D}
              style={{
                background: 'rgba(244, 241, 234, 0.94)',
                color: '#30343A',
                border: '1px solid rgba(13, 148, 136, 0.4)',
                borderRadius: '10px',
                padding: '7px 14px',
                fontSize: '12px',
                fontWeight: 800,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
                letterSpacing: '0.02em',
                transition: 'all 0.2s ease',
              }}
              title="Beralih ke Dashboard 2D (Cepat, Ringan & Hemat Baterai)"
            >
              <Sliders size={14} color="#0D9488" />
              <span>Mode 2D</span>
            </button>
          )}

          {/* Kirim Task Action Button (Shows Lock if guest, Send if logged in) */}
          <button
            onClick={handleOpenDispatch}
            style={{
              background: authToken
                ? 'linear-gradient(135deg, #2D3748, #354A60)'
                : 'linear-gradient(135deg, #354A60, #D98078)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '10px',
              padding: '7px 16px',
              fontSize: '12px',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(53, 74, 96, 0.25)',
              letterSpacing: '0.02em',
              transition: 'all 0.2s ease',
            }}
            title={authToken ? 'Kirim task baru ke squad (Admin aktif)' : 'Kirim task (Memerlukan password pengelola)'}
          >
            {authToken ? <Send size={14} /> : <Lock size={14} />}
            <span>Kirim Task</span>
            {authToken && (
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: '#10B981',
                  boxShadow: '0 0 6px #10B981',
                  marginLeft: '2px',
                }}
              />
            )}
          </button>

          {/* Optional Logout Button for Authenticated Admin */}
          {authToken && (
            <button
              onClick={handleLogout}
              title="Keluar dari sesi pengelola"
              style={{
                background: 'rgba(244, 241, 234, 0.94)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '8px',
                padding: '6px 10px',
                color: '#EF4444',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '11px',
                fontWeight: 700,
              }}
            >
              <LogOut size={12} />
              <span>Keluar</span>
            </button>
          )}

          {/* Microservices Health Status Button */}
          <button
            onClick={() => setServicesModalOpen(true)}
            style={{
              background: isDegraded ? 'rgba(239, 68, 68, 0.15)' : 'rgba(244, 241, 234, 0.94)',
              color: isDegraded ? '#EF4444' : '#30343A',
              border: `1px solid ${isDegraded ? 'rgba(239, 68, 68, 0.5)' : 'rgba(196, 154, 108, 0.4)'}`,
              borderRadius: '10px',
              padding: '7px 14px',
              fontSize: '12px',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              boxShadow: isDegraded ? '0 0 12px rgba(239, 68, 68, 0.3)' : '0 2px 8px rgba(0, 0, 0, 0.08)',
              letterSpacing: '0.02em',
              transition: 'all 0.2s ease',
            }}
            title="Cek Status Ketersediaan Microservice (Keselip-API, Kataku-API & Dongeng-API)"
          >
            <Server size={14} color={isDegraded ? '#EF4444' : '#354A60'} />
            <span>{isDegraded ? 'Outage ⚠️' : 'Services'}</span>
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: isDegraded ? '#EF4444' : '#10B981',
                boxShadow: isDegraded ? '0 0 8px #EF4444' : '0 0 6px #10B981',
                marginLeft: '2px',
              }}
            />
          </button>

          {/* Connection Status Badge */}
          <div
            onClick={onReconnect}
            title={connected ? 'Stream SSE Aktif' : 'Terputus. Klik untuk konek ulang'}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: connected ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.2)',
              border: `1px solid ${connected ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
              borderRadius: '20px',
              padding: '5px 12px',
              fontSize: '11px',
              fontWeight: 700,
              color: connected ? '#34d399' : '#f87171',
              cursor: 'pointer',
            }}
          >
            {connected ? <Wifi size={13} /> : <WifiOff size={13} />}
            <span>{connected ? 'LIVE' : 'OFFLINE'}</span>
          </div>
        </div>
      </div>

      {/* Floating Service Outage Alert Banner (Under Top Header) */}
      <ServiceAlertBanner
        healthData={healthData}
        isDegraded={isDegraded}
        isRechecking={isRechecking}
        isDismissed={isAlertDismissed}
        onDismiss={onDismissAlert}
        onRecheck={onRecheckHealth}
        onViewDetails={() => setServicesModalOpen(true)}
      />

      {/* 2. LEFT PANEL: Active Stage Card */}
      {!immersiveMode && (
        <div
          className="warm-panel"
          style={{
            pointerEvents: 'auto',
            position: 'absolute',
            top: '90px',
            left: '20px',
            width: '320px',
            borderRadius: '16px',
            padding: '14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            border: `1px solid ${humanStatus.color}55`,
            boxShadow: `0 8px 24px rgba(0, 0, 0, 0.08), 0 0 10px ${humanStatus.glowColor}10`,
            background: 'rgba(248, 246, 240, 0.94)',
            backdropFilter: 'blur(12px)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '11px', color: '#8A8A82', fontWeight: 800, letterSpacing: '0.06em' }}>
              STATUS EKSEKUSI
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '10px',
                  background: humanStatus.badgeBg,
                  color: humanStatus.color,
                  border: `1px solid ${humanStatus.color}66`,
                }}
              >
                {status.toUpperCase()}
              </span>
              <button
                onClick={() => setStagePanelOpen(!stagePanelOpen)}
                style={{ background: 'none', border: 'none', color: '#8A8A82', cursor: 'pointer', padding: 0 }}
                title={stagePanelOpen ? 'Collapse' : 'Expand'}
              >
                {stagePanelOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            </div>
          </div>

          {stagePanelOpen && (
            <>
              {/* Humanized Node Badge */}
              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.8)',
                  border: `1px solid ${humanStatus.color}66`,
                  borderRadius: '12px',
                  padding: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  boxShadow: `inset 0 0 16px ${humanStatus.color}15`,
                }}
              >
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '10px',
                    backgroundColor: `${humanStatus.color}22`,
                    border: `1px solid ${humanStatus.color}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '18px',
                    flexShrink: 0,
                  }}
                >
                  {humanStatus.icon}
                </div>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 800, color: '#30343A' }}>
                    {humanStatus.label}
                  </div>
                  <div style={{ fontSize: '11px', color: '#8A8A82', marginTop: '2px' }}>
                    Penanggung Jawab:{' '}
                    <span style={{ color: humanStatus.color, fontWeight: 700 }}>
                      {humanStatus.responsibleWorker.toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Message / Task Description */}
              <div>
                <div style={{ fontSize: '10px', color: '#8A8A82', fontWeight: 700, marginBottom: '4px' }}>
                  DESKRIPSI AKTIVITAS:
                </div>
                <div
                  style={{
                    fontSize: '12px',
                    color: '#30343A',
                    lineHeight: 1.4,
                    background: 'rgba(196, 154, 108, 0.08)',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    border: '1px solid rgba(48, 52, 58, 0.1)',
                  }}
                >
                  {message || humanStatus.description}
                </div>
              </div>

              {/* Thread Info */}
              <div
                style={{
                  fontSize: '11px',
                  color: '#8A8A82',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  borderTop: '1px solid rgba(48, 52, 58, 0.12)',
                  paddingTop: '10px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Pipeline:</span>
                  <span style={{ color: '#D98078', fontWeight: 700 }}>
                    {currentPipeline.toUpperCase()}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Thread ID:</span>
                  <span className="mono" style={{ color: '#354A60', fontWeight: 600 }}>
                    {threadId ? threadId.slice(0, 16) : 'system'}
                  </span>
                </div>
                {details?.topic && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Topik:</span>
                    <span
                      style={{
                        color: '#30343A',
                        fontWeight: 600,
                        maxWidth: '180px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        textAlign: 'right',
                      }}
                    >
                      {details.topic}
                    </span>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* 3. RIGHT PANEL: Multi-Agent Team Roster & Ambient Life Tracker */}
      {!immersiveMode && (
        <div
          className="warm-panel"
          style={{
            pointerEvents: 'auto',
            position: 'absolute',
            top: '90px',
            right: '20px',
            width: '320px',
            borderRadius: '16px',
            padding: '14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            border: '1px solid rgba(196, 154, 108, 0.3)',
            boxShadow: '0 8px 20px rgba(0, 0, 0, 0.1)',
          }}
        >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Users size={14} color="#D98078" />
            <span style={{ fontSize: '11px', color: '#30343A', fontWeight: 800, letterSpacing: '0.05em' }}>
              MULTI-AGENT SQUAD & AMBIENT
            </span>
          </div>
          <button
            onClick={() => setTeamPanelOpen(!teamPanelOpen)}
            style={{ background: 'none', border: 'none', color: '#8A8A82', cursor: 'pointer' }}
          >
            {teamPanelOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>

        {teamPanelOpen && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {(['stark', 'bayzero', 'usagi'] as WorkerId[]).map((wId) => {
              const prof = WORKER_PROFILES[wId];
              const visual = characterStates?.[wId];
              const isUptimeAlertOutdated =
                (currentNode === 'uptime_alert' || (message && message.includes('Peringatan Service Down'))) && !isDegraded;
              const agentFailure =
                latestAgentFailures[wId] ||
                (status === 'failed' && humanStatus.responsibleWorker === wId && !isUptimeAlertOutdated ? message : null);
              const hasFailed = Boolean(agentFailure);

              const actualState: ActualAgentState = hasFailed
                ? 'Blocked'
                : (visual?.actualState || (isIdle ? 'Idle' : 'Working'));
              const isWorking = actualState === 'Working';

              // Badging color & label for Actual Agent State
              let stateBadgeBg = 'rgba(100, 116, 139, 0.15)';
              let stateBadgeColor = '#64748b';
              let stateBadgeBorder = 'rgba(100, 116, 139, 0.3)';
              let stateBadgeText: string = actualState.toUpperCase();

              if (hasFailed) {
                stateBadgeBg = 'rgba(239, 68, 68, 0.2)';
                stateBadgeColor = '#ef4444';
                stateBadgeBorder = 'rgba(239, 68, 68, 0.55)';
                stateBadgeText = 'ERROR ⚠️';
              } else if (actualState === 'Working') {
                stateBadgeBg = 'rgba(16, 185, 129, 0.18)';
                stateBadgeColor = '#10b981';
                stateBadgeBorder = 'rgba(16, 185, 129, 0.45)';
              } else if (actualState === 'Blocked') {
                stateBadgeBg = 'rgba(239, 68, 68, 0.2)';
                stateBadgeColor = '#ef4444';
                stateBadgeBorder = 'rgba(239, 68, 68, 0.45)';
              } else if (actualState === 'Waiting') {
                stateBadgeBg = 'rgba(245, 158, 11, 0.18)';
                stateBadgeColor = '#d97706';
                stateBadgeBorder = 'rgba(245, 158, 11, 0.45)';
              } else if (actualState === 'Offline') {
                stateBadgeBg = 'rgba(71, 85, 105, 0.18)';
                stateBadgeColor = '#475569';
                stateBadgeBorder = 'rgba(71, 85, 105, 0.35)';
              }

              // Visual Activity Presentation Text
              const displayActivity = visual
                ? isWorking
                  ? humanStatus.label
                  : visual.ambientLabel
                : 'Santai di Meja ☕';

              return (
                <div
                  key={wId}
                  style={{
                    background: hasFailed
                      ? 'rgba(254, 242, 242, 0.95)'
                      : isWorking
                      ? 'rgba(232, 228, 218, 0.92)'
                      : 'rgba(244, 241, 234, 0.65)',
                    border: hasFailed
                      ? '1.5px solid #EF4444'
                      : `1.5px solid ${isWorking ? prof.color : 'rgba(48, 52, 58, 0.12)'}`,
                    borderRadius: '12px',
                    padding: '8px 12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    boxShadow: hasFailed
                      ? '0 0 14px rgba(239, 68, 68, 0.35)'
                      : isWorking
                      ? `0 0 10px ${prof.glowColor}30`
                      : 'none',
                    transition: 'all 0.3s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div
                        style={{
                          width: '26px',
                          height: '26px',
                          borderRadius: '8px',
                          backgroundColor: hasFailed ? '#EF4444' : prof.color,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 900,
                          fontSize: '11px',
                          color: '#ffffff',
                          boxShadow: hasFailed ? '0 0 8px rgba(239, 68, 68, 0.5)' : 'none',
                        }}
                      >
                        {hasFailed ? '!' : prof.name[0]}
                      </div>
                      <div>
                        <div style={{ fontSize: '12px', fontWeight: 800, color: hasFailed ? '#991B1B' : '#30343A' }}>
                          {prof.name}
                        </div>
                        <div style={{ fontSize: '10px', color: '#8A8A82' }}>{prof.role}</div>
                      </div>
                    </div>

                    {/* Actual State Badge */}
                    <span
                      style={{
                        fontSize: '9px',
                        fontWeight: 800,
                        letterSpacing: '0.04em',
                        padding: '2px 7px',
                        borderRadius: '6px',
                        background: stateBadgeBg,
                        color: stateBadgeColor,
                        border: `1px solid ${stateBadgeBorder}`,
                      }}
                    >
                      {stateBadgeText}
                    </span>
                  </div>

                  {/* Failure Alert Reason Callout */}
                  {hasFailed && agentFailure && (
                    <div
                      style={{
                        fontSize: '10px',
                        color: '#B91C1C',
                        background: 'rgba(239, 68, 68, 0.12)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        borderRadius: '6px',
                        padding: '3px 8px',
                        marginTop: '2px',
                        lineHeight: 1.3,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                      }}
                    >
                      <AlertTriangle size={11} color="#DC2626" style={{ flexShrink: 0 }} />
                      <span
                        style={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontWeight: 600,
                        }}
                        title={agentFailure}
                      >
                        {agentFailure}
                      </span>
                    </div>
                  )}

                  {/* Ambient Visual Activity Indicator */}
                  <div
                    style={{
                      fontSize: '10.5px',
                      color: isWorking ? '#354A60' : '#6B7A8A',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      paddingLeft: '34px',
                      marginTop: '2px',
                    }}
                  >
                    <span style={{ color: '#A0907A', fontSize: '9px' }}>
                      {isWorking ? 'AKTIVITAS:' : 'VISUAL:'}
                    </span>
                    <span style={{ color: isWorking ? prof.color : '#30343A', fontWeight: 700 }}>
                      {displayActivity}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
      )}

      {/* 4. BOTTOM LOG TERMINAL */}
      {!immersiveMode && (
        <div
          className="warm-panel"
        style={{
          pointerEvents: 'auto',
          position: 'absolute',
          bottom: '20px',
          left: '20px',
          right: '20px',
          borderRadius: '16px',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: terminalOpen ? '200px' : '44px',
          transition: 'max-height 0.25s ease',
          border: '1px solid rgba(196, 154, 108, 0.25)',
        }}
      >
        {/* Terminal Header */}
        <div
          onClick={() => setTerminalOpen(!terminalOpen)}
          style={{
            padding: '10px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(244, 241, 234, 0.94)',
            borderBottom: terminalOpen ? '1px solid rgba(48, 52, 58, 0.12)' : 'none',
            cursor: 'pointer',
            userSelect: 'none',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={15} color="#354A60" />
            <span style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '0.04em' }}>
              LIVE AGENT LOG STREAM ({filteredLogs.length}{filteredLogs.length !== logs.length ? `/${logs.length}` : ''})
            </span>
            <span style={{ fontSize: '10px', color: '#8A8A82', marginLeft: '4px' }}>
              • Persisten
            </span>
          </div>

          <div
            style={{ display: 'flex', alignItems: 'center', gap: '10px' }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Filter Agen */}
            <select
              value={logAgentFilter}
              onChange={(e) => setLogAgentFilter(e.target.value)}
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: '6px',
                border: '1px solid rgba(48, 52, 58, 0.2)',
                background: '#FFF',
                color: '#30343A',
                cursor: 'pointer',
              }}
            >
              <option value="all">Semua Agen</option>
              <option value="stark">⚡ Stark (Tech)</option>
              <option value="usagi">🦊 Usagi (Dongeng)</option>
              <option value="bayzero">🔍 Bay-Zero (SRE)</option>
              <option value="clara">🎯 Clara (Career)</option>
              <option value="janitor">🧹 Janitor</option>
            </select>

            {/* Sync Button */}
            {onRefreshLogs && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRefreshLogs();
                }}
                disabled={loadingLogs}
                title="Muat ulang log dari database PostgreSQL"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '2px 8px',
                  fontSize: '10.5px',
                  fontWeight: 600,
                  borderRadius: '6px',
                  border: '1px solid rgba(53, 74, 96, 0.3)',
                  background: 'rgba(53, 74, 96, 0.08)',
                  color: '#354A60',
                  cursor: loadingLogs ? 'wait' : 'pointer',
                }}
              >
                <RefreshCw size={11} className={loadingLogs ? 'spin' : ''} />
                <span>{loadingLogs ? 'Sync...' : 'Sync'}</span>
              </button>
            )}

            <div
              onClick={() => setTerminalOpen(!terminalOpen)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#8A8A82', cursor: 'pointer' }}
            >
              <span style={{ fontSize: '11px' }}>{terminalOpen ? 'Collapse' : 'Expand'}</span>
              {terminalOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
            </div>
          </div>
        </div>

        {/* Terminal Body */}
        {terminalOpen && (
          <div
            className="mono"
            style={{
              padding: '10px 16px',
              overflowY: 'auto',
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              fontSize: '11px',
              background: 'rgba(244, 241, 234, 0.95)',
            }}
          >
            {filteredLogs.length === 0 ? (
              <div style={{ color: '#8A8A82', fontStyle: 'italic', padding: '10px 0' }}>
                {loadingLogs ? 'Sedang memuat riwayat log dari database...' : 'Belum ada event log yang sesuai dengan filter.'}
              </div>
            ) : (
              filteredLogs.map((log) => {
                const conf = getHumanStatus(log.node);
                const isFailed = log.status === 'failed' || log.node === 'failed_node';
                const isCompleted = log.status === 'completed' || log.node === 'publish_node';
                const isExpanded = expandedLogId === log.id;
                const errorDetail =
                  (log as any).error ||
                  (log.details && log.details.error) ||
                  (isFailed ? log.message : null);
                const resultUrl =
                  (log.details && (log.details.url || log.details.result_url)) ||
                  (log as any).result_url;

                // 1. Tentukan Aktor Agen
                const rawActor = (log.agent_name || (log.details && log.details.agent_name) || '').toLowerCase();
                const respWorker = (conf.responsibleWorker || '') as string;
                let actor = {
                  name: 'Squad',
                  icon: '🏢',
                  bg: 'rgba(141, 168, 149, 0.2)',
                  color: '#2E5A44',
                  border: 'rgba(141, 168, 149, 0.4)',
                };

                if (rawActor.includes('stark') || (!rawActor && respWorker === 'stark')) {
                  actor = {
                    name: 'Stark',
                    icon: '⚡',
                    bg: 'rgba(53, 74, 96, 0.15)',
                    color: '#354A60',
                    border: 'rgba(53, 74, 96, 0.35)',
                  };
                } else if (rawActor.includes('usagi') || (!rawActor && respWorker === 'usagi')) {
                  actor = {
                    name: 'Usagi',
                    icon: '🦊',
                    bg: 'rgba(244, 63, 94, 0.15)',
                    color: '#E11D48',
                    border: 'rgba(244, 63, 94, 0.35)',
                  };
                } else if (rawActor.includes('bay') || rawActor.includes('zero') || (!rawActor && respWorker === 'bayzero')) {
                  actor = {
                    name: 'Bay-Zero',
                    icon: '🔍',
                    bg: 'rgba(245, 158, 11, 0.15)',
                    color: '#D97706',
                    border: 'rgba(245, 158, 11, 0.35)',
                  };
                } else if (rawActor.includes('droid') || rawActor.includes('janitor')) {
                  actor = {
                    name: 'Janitor',
                    icon: '🧹',
                    bg: 'rgba(100, 116, 139, 0.15)',
                    color: '#475569',
                    border: 'rgba(100, 116, 139, 0.35)',
                  };
                }

                // 2. Status Badge Formatting
                let statusBadge = {
                  label: log.status.toUpperCase(),
                  bg: 'rgba(100, 116, 139, 0.12)',
                  color: '#475569',
                  border: 'rgba(100, 116, 139, 0.25)',
                };
                if (isFailed) {
                  statusBadge = {
                    label: '❌ GAGAL',
                    bg: 'rgba(239, 68, 68, 0.2)',
                    color: '#DC2626',
                    border: 'rgba(239, 68, 68, 0.4)',
                  };
                } else if (isCompleted) {
                  statusBadge = {
                    label: '✅ SELESAI',
                    bg: 'rgba(16, 185, 129, 0.2)',
                    color: '#059669',
                    border: 'rgba(16, 185, 129, 0.4)',
                  };
                } else {
                  const s = log.status.toLowerCase();
                  if (s === 'started') {
                    statusBadge = {
                      label: '▶ MULAI',
                      bg: 'rgba(53, 74, 96, 0.14)',
                      color: '#354A60',
                      border: 'rgba(53, 74, 96, 0.3)',
                    };
                  } else if (s === 'in_progress' || s === 'processing') {
                    statusBadge = {
                      label: '⚡ PROSES',
                      bg: 'rgba(59, 130, 246, 0.16)',
                      color: '#2563EB',
                      border: 'rgba(59, 130, 246, 0.35)',
                    };
                  } else if (s === 'skipped') {
                    statusBadge = {
                      label: '⏭️ DILEWATI',
                      bg: 'rgba(245, 158, 11, 0.18)',
                      color: '#D97706',
                      border: 'rgba(245, 158, 11, 0.35)',
                    };
                  } else if (s === 'idle') {
                    statusBadge = {
                      label: '☕ IDLE',
                      bg: 'rgba(100, 116, 139, 0.12)',
                      color: '#64748B',
                      border: 'rgba(100, 116, 139, 0.25)',
                    };
                  }
                }

                // 3. Label Bersih tanpa duplikasi emoji
                const cleanLabel = conf.label.replace(conf.icon, '').trim() || conf.label;

                return (
                  <div
                    key={log.id}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                      padding: isFailed || isCompleted ? '6px 10px' : '4px 8px',
                      borderRadius: '8px',
                      marginBottom: '2px',
                      background: isFailed
                        ? 'rgba(239, 68, 68, 0.15)'
                        : isCompleted
                        ? 'rgba(16, 185, 129, 0.12)'
                        : 'transparent',
                      border: isFailed
                        ? '1px solid rgba(239, 68, 68, 0.35)'
                        : isCompleted
                        ? '1px solid rgba(16, 185, 129, 0.3)'
                        : '1px solid rgba(48, 52, 58, 0.05)',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', width: '100%' }}>
                      {/* Timestamp */}
                      <span style={{ color: '#8A8A82', fontSize: '11px', minWidth: '70px', flexShrink: 0, fontFamily: 'monospace' }}>
                        [{log.time}]
                      </span>

                      {/* Aktor Badge */}
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '2px 8px',
                          borderRadius: '6px',
                          fontSize: '10.5px',
                          fontWeight: 800,
                          background: actor.bg,
                          color: actor.color,
                          border: `1px solid ${actor.border}`,
                          minWidth: '82px',
                          justifyContent: 'center',
                          flexShrink: 0,
                          letterSpacing: '0.02em',
                        }}
                      >
                        <span>{actor.icon}</span>
                        <span>{actor.name}</span>
                      </span>

                      {/* Status Badge */}
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '6px',
                          fontSize: '10px',
                          fontWeight: 800,
                          minWidth: '76px',
                          textAlign: 'center',
                          flexShrink: 0,
                          background: statusBadge.bg,
                          color: statusBadge.color,
                          border: `1px solid ${statusBadge.border}`,
                          letterSpacing: '0.04em',
                        }}
                      >
                        {statusBadge.label}
                      </span>

                      {/* Aktivitas / Node */}
                      <span
                        style={{
                          color: isFailed ? '#DC2626' : conf.color,
                          fontWeight: 700,
                          fontSize: '11px',
                          minWidth: '150px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px',
                          flexShrink: 0,
                        }}
                      >
                        {isFailed ? (
                          <AlertTriangle size={13} color="#DC2626" />
                        ) : (
                          <span>{conf.icon}</span>
                        )}
                        <span>{isFailed ? 'Error Terdeteksi' : cleanLabel}</span>
                      </span>

                      {/* Pesan Deskripsi */}
                      <span
                        style={{
                          color: isFailed ? '#DC2626' : '#30343A',
                          flex: 1,
                          fontSize: '11.5px',
                          fontWeight: isFailed ? 700 : 400,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                        title={log.message}
                      >
                        {log.message}
                      </span>

                      {/* Optional publication URL for completed log */}
                      {resultUrl && (
                        <a
                          href={resultUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '11px',
                            color: '#0284C7',
                            fontWeight: 700,
                            textDecoration: 'underline',
                            marginLeft: '8px',
                            flexShrink: 0,
                          }}
                        >
                          <span>Buka Hasil</span>
                          <ExternalLink size={11} />
                        </a>
                      )}

                      {/* Expand Button for full failure details */}
                      {isFailed && (
                        <button
                          onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                          style={{
                            background: 'rgba(239, 68, 68, 0.2)',
                            border: '1px solid rgba(239, 68, 68, 0.4)',
                            borderRadius: '6px',
                            padding: '3px 8px',
                            fontSize: '10.5px',
                            color: '#DC2626',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            flexShrink: 0,
                          }}
                        >
                          <span>{isExpanded ? 'Tutup Detail' : 'Detail Error'}</span>
                          {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                        </button>
                      )}
                    </div>

                    {/* Expanded error reason / stacktrace & Admin Technical Debug */}
                    {isExpanded && errorDetail && (
                      <div
                        style={{
                          marginTop: '6px',
                          padding: '10px 12px',
                          borderRadius: '8px',
                          background: 'rgba(239, 68, 68, 0.08)',
                          border: '1px solid rgba(239, 68, 68, 0.25)',
                          color: '#B91C1C',
                          fontSize: '11px',
                          lineHeight: 1.45,
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px',
                        }}
                      >
                        <div
                          style={{
                            fontWeight: 800,
                            marginBottom: '2px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                          }}
                        >
                          <AlertCircle size={12} />
                          <span>ALASAN KEGAGALAN LENGKAP:</span>
                        </div>
                        <code style={{ fontSize: '11px', color: '#991B1B' }}>{errorDetail}</code>

                        {/* Admin Technical Diagnostics Inspector */}
                        {authToken ? (
                          <div
                            style={{
                              marginTop: '8px',
                              padding: '8px 10px',
                              borderRadius: '6px',
                              background: 'rgba(30, 41, 59, 0.95)',
                              border: '1px solid rgba(59, 130, 246, 0.35)',
                              color: '#F8FAFC',
                              fontSize: '10.5px',
                              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
                            }}
                          >
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                marginBottom: '6px',
                                paddingBottom: '4px',
                                borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#38BDF8', fontWeight: 800 }}>
                                <Bug size={12} />
                                <span>DIAGNOSTIK TEKNIS (ADMIN AKTIF)</span>
                              </div>
                              <span style={{ fontSize: '9.5px', color: '#94A3B8', fontFamily: 'monospace' }}>
                                ID: {log.id}
                              </span>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 10px', fontSize: '10.5px' }}>
                              <span style={{ color: '#94A3B8', fontWeight: 600 }}>Tingkat Pipeline:</span>
                              <span style={{ color: '#FCD34D', fontFamily: 'monospace', fontWeight: 700 }}>
                                {log.details?.original_node || log.node}
                              </span>

                              <span style={{ color: '#94A3B8', fontWeight: 600 }}>Thread ID:</span>
                              <span style={{ color: '#E2E8F0', fontFamily: 'monospace' }}>
                                {log.thread_id || '-'}
                              </span>

                              <span style={{ color: '#94A3B8', fontWeight: 600 }}>Aktor Agen:</span>
                              <span style={{ color: '#E2E8F0' }}>
                                {log.agent_name || actor.name}
                              </span>

                              {log.details?.task_id && (
                                <>
                                  <span style={{ color: '#94A3B8', fontWeight: 600 }}>Task ID:</span>
                                  <span style={{ color: '#E2E8F0', fontFamily: 'monospace' }}>
                                    {log.details.task_id}
                                  </span>
                                </>
                              )}

                              {log.details?.video_id && (
                                <>
                                  <span style={{ color: '#94A3B8', fontWeight: 600 }}>Video ID:</span>
                                  <span style={{ color: '#67E8F9', fontFamily: 'monospace', fontWeight: 700 }}>
                                    {log.details.video_id}
                                  </span>
                                </>
                              )}

                              {log.details?.query && (
                                <>
                                  <span style={{ color: '#94A3B8', fontWeight: 600 }}>Target Query:</span>
                                  <span style={{ color: '#E2E8F0' }}>{log.details.query}</span>
                                </>
                              )}
                            </div>

                            {/* Raw Details JSON */}
                            {log.details && Object.keys(log.details).length > 0 && (
                              <details style={{ marginTop: '8px' }}>
                                <summary
                                  style={{
                                    cursor: 'pointer',
                                    color: '#93C5FD',
                                    fontWeight: 700,
                                    fontSize: '10px',
                                    userSelect: 'none',
                                    outline: 'none',
                                  }}
                                >
                                  ▶ Raw Payload / Details JSON
                                </summary>
                                <pre
                                  style={{
                                    marginTop: '4px',
                                    padding: '6px',
                                    background: 'rgba(15, 23, 42, 0.85)',
                                    borderRadius: '4px',
                                    overflowX: 'auto',
                                    fontSize: '9.5px',
                                    color: '#A7F3D0',
                                    maxHeight: '120px',
                                  }}
                                >
                                  {JSON.stringify(log.details, null, 2)}
                                </pre>
                              </details>
                            )}
                          </div>
                        ) : (
                          <div
                            style={{
                              marginTop: '4px',
                              fontSize: '10px',
                              color: '#6B7280',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontStyle: 'italic',
                            }}
                          >
                            <Lock size={10} />
                            <span>Masuk dengan Password Admin (di kanan atas) untuk melihat detail teknis & node pipeline.</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
      )}

      {/* 5. AUTHENTICATION MODAL */}
      {authModalOpen && createPortal(
        <div
          className="punggawa-portal-modal-backdrop"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(30, 33, 40, 0.75)',
            backdropFilter: 'blur(14px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 999999,
            pointerEvents: 'auto',
          }}
        >
          <div
            className="warm-panel-accent"
            style={{
              width: '420px',
              maxWidth: '92vw',
              borderRadius: '24px',
              padding: '28px',
              background: 'rgba(248, 246, 240, 0.98)',
              boxShadow: '0 24px 60px rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(196, 154, 108, 0.4)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div
                  style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '12px',
                    background: 'linear-gradient(135deg, #354A60, #D98078)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 4px 12px rgba(53, 74, 96, 0.25)',
                  }}
                >
                  <Lock size={18} color="#FFFFFF" />
                </div>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 900, margin: 0, color: '#2B3038' }}>
                    Autentikasi Pengelola Squad
                  </h3>
                  <p style={{ fontSize: '11px', color: '#8A8A82', margin: '2px 0 0 0' }}>
                    Akses kontrol pengiriman perintah agent
                  </p>
                </div>
              </div>
              <button
                onClick={() => setAuthModalOpen(false)}
                style={{ background: 'none', border: 'none', color: '#8A8A82', fontSize: '18px', cursor: 'pointer', padding: 4 }}
              >
                ✕
              </button>
            </div>

            <p style={{ fontSize: '12px', color: '#555A64', lineHeight: 1.5, marginBottom: '18px' }}>
              Dashboard ini bebas dipantau oleh siapa saja melalui internet. Namun untuk mengirim instruksi atau menjalankan pipeline agent, silakan masukkan kredensial pengelola.
            </p>

            <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 700, color: '#30343A', display: 'block', marginBottom: '6px' }}>
                  Username:
                </label>
                <input
                  type="text"
                  required
                  value={authUsername}
                  onChange={(e) => setAuthUsername(e.target.value)}
                  placeholder="admin"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '10px',
                    background: '#FFFFFF',
                    border: '1px solid rgba(48, 52, 58, 0.2)',
                    fontSize: '13px',
                    color: '#30343A',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 700, color: '#30343A', display: 'block', marginBottom: '6px' }}>
                  Password:
                </label>
                <input
                  type="password"
                  required
                  autoFocus
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  placeholder="Masukkan password pengelola"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '10px',
                    background: '#FFFFFF',
                    border: '1px solid rgba(48, 52, 58, 0.2)',
                    fontSize: '13px',
                    color: '#30343A',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              {authError && (
                <div
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    background: 'rgba(239, 68, 68, 0.12)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    color: '#DC2626',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}
                >
                  ⚠️ {authError}
                </div>
              )}

              <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
                <button
                  type="button"
                  onClick={() => setAuthModalOpen(false)}
                  style={{
                    flex: 1,
                    padding: '11px',
                    borderRadius: '10px',
                    background: 'rgba(48, 52, 58, 0.08)',
                    border: 'none',
                    color: '#64748B',
                    fontSize: '13px',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={authLoading}
                  style={{
                    flex: 2,
                    padding: '11px',
                    borderRadius: '10px',
                    background: 'linear-gradient(135deg, #354A60, #D98078)',
                    border: 'none',
                    color: '#FFFFFF',
                    fontSize: '13px',
                    fontWeight: 800,
                    cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(53, 74, 96, 0.25)',
                  }}
                >
                  {authLoading ? 'Memverifikasi...' : 'Masuk & Lanjutkan 🔓'}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* 6. PRESET-DRIVEN TASK DISPATCH MODAL */}
      {dispatchModalOpen && createPortal(
        <div
          className="punggawa-portal-modal-backdrop"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(30, 33, 40, 0.72)',
            backdropFilter: 'blur(14px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 999999,
            pointerEvents: 'auto',
          }}
        >
          <div
            className="warm-panel-accent"
            style={{
              width: '600px',
              maxWidth: '94vw',
              maxHeight: '90vh',
              overflowY: 'auto',
              borderRadius: '24px',
              padding: '26px',
              background: 'rgba(248, 246, 240, 0.98)',
              boxShadow: '0 24px 60px rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(196, 154, 108, 0.4)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '12px',
                borderBottom: '1px solid rgba(48, 52, 58, 0.1)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div
                  style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '12px',
                    background: 'linear-gradient(135deg, #354A60, #8DA895)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 4px 12px rgba(53, 74, 96, 0.2)',
                  }}
                >
                  <Send size={18} color="#ffffff" />
                </div>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 900, margin: 0, color: '#2B3038' }}>
                    Luncurkan Task ke Squad Agent
                  </h3>
                  <p style={{ fontSize: '11px', color: '#8A8A82', margin: '2px 0 0 0' }}>
                    Pilih opsi misi di bawah tanpa perlu mengingat perintah
                  </p>
                </div>
              </div>
              <button
                onClick={() => setDispatchModalOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#8A8A82',
                  fontSize: '20px',
                  cursor: 'pointer',
                  padding: '4px',
                }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleDispatch} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {/* Squad Agent Filter Tabs */}
              <div>
                <label style={{ fontSize: '12px', fontWeight: 800, color: '#30343A', display: 'block', marginBottom: '8px' }}>
                  Pilih Spesialis Agent:
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {[
                    { id: 'all', label: `Semua Misi (${TASK_PRESETS.length})`, icon: '🌟' },
                    { id: 'stark', label: '⚡ Stark (Writer)', icon: '⚡' },
                    { id: 'usagi', label: '🦊 Usagi (Dongeng)', icon: '🦊' },
                    { id: 'bayzero', label: '🛡️ Bay-Zero (Server & Audit)', icon: '🛡️' },
                    { id: 'scout', label: '🎯 Scout (Career Intelligence)', icon: '🎯' },
                  ].map((tab) => {
                    const active = activeAgentTab === tab.id;
                    return (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => setActiveAgentTab(tab.id as any)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '8px',
                          border: active ? '1.5px solid #354A60' : '1px solid rgba(48, 52, 58, 0.15)',
                          background: active ? '#354A60' : 'rgba(255, 255, 255, 0.75)',
                          color: active ? '#FFFFFF' : '#30343A',
                          fontSize: '11.5px',
                          fontWeight: active ? 800 : 600,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px',
                        }}
                      >
                        <span>{tab.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Preset Cards Selection */}
              <div>
                <label style={{ fontSize: '12px', fontWeight: 800, color: '#30343A', display: 'block', marginBottom: '8px' }}>
                  Pilih Paket Misi:
                </label>
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                    maxHeight: '260px',
                    overflowY: 'auto',
                    paddingRight: '4px',
                  }}
                >
                  {filteredPresets.map((preset) => {
                    const isSelected = selectedPresetId === preset.id;
                    return (
                      <div
                        key={preset.id}
                        onClick={() => setSelectedPresetId(preset.id)}
                        style={{
                          border: isSelected ? '2px solid #354A60' : '1px solid rgba(48, 52, 58, 0.14)',
                          borderRadius: '12px',
                          padding: '10px 14px',
                          background: isSelected ? 'rgba(53, 74, 96, 0.08)' : 'rgba(255, 255, 255, 0.85)',
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '4px',
                          transition: 'all 0.15s ease',
                          boxShadow: isSelected ? '0 2px 10px rgba(53, 74, 96, 0.15)' : 'none',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '16px' }}>{preset.icon}</span>
                            <span style={{ fontSize: '13px', fontWeight: 800, color: '#2B3038' }}>
                              {preset.title}
                            </span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span
                              style={{
                                fontSize: '10px',
                                fontWeight: 700,
                                padding: '2px 8px',
                                borderRadius: '6px',
                                background: isSelected ? '#354A60' : 'rgba(48, 52, 58, 0.08)',
                                color: isSelected ? '#FFFFFF' : '#475569',
                              }}
                            >
                              {preset.badge}
                            </span>
                            {isSelected && <Check size={14} color="#354A60" style={{ strokeWidth: 3 }} />}
                          </div>
                        </div>
                        <p style={{ fontSize: '11px', color: '#64748B', margin: '2px 0 0 24px', lineHeight: 1.4 }}>
                          {preset.description}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Selected Preset Summary */}
              <div
                style={{
                  background: 'rgba(232, 228, 218, 0.75)',
                  borderRadius: '12px',
                  padding: '10px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  border: '1px solid rgba(196, 154, 108, 0.3)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '11px', color: '#64748B', fontWeight: 700 }}>Agen Pelaksana:</span>
                  <span style={{ fontSize: '12px', fontWeight: 800, color: '#354A60' }}>
                    {currentPreset.agentName} ({currentPreset.agentRole})
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowCustomInput(!showCustomInput)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#64748B',
                    fontSize: '11px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    textDecoration: 'underline',
                  }}
                >
                  <Sliders size={12} />
                  <span>{showCustomInput ? 'Tutup Kustomisasi' : 'Kustomisasi (Opsional)'}</span>
                </button>
              </div>

              {/* Optional Custom Input Accordion */}
              {showCustomInput && (
                <div
                  style={{
                    background: '#FFFFFF',
                    border: '1px solid rgba(48, 52, 58, 0.15)',
                    borderRadius: '12px',
                    padding: '12px 14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                  }}
                >
                  <div style={{ fontSize: '11px', fontWeight: 800, color: '#354A60' }}>
                    ⚙️ Opsi Penyesuaian Kustom (Jika tidak diubah, menggunakan preset default):
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 700, color: '#475569', display: 'block', marginBottom: '4px' }}>
                      Prompt Kustom:
                    </label>
                    <input
                      type="text"
                      placeholder={currentPreset.title}
                      value={customPrompt}
                      onChange={(e) => setCustomPrompt(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '8px 10px',
                        borderRadius: '8px',
                        border: '1px solid #CBD5E1',
                        fontSize: '12px',
                        outline: 'none',
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>
                  {currentPreset.type === 'dongeng' ? (
                    <div>
                      <label style={{ fontSize: '11px', fontWeight: 700, color: '#475569', display: 'block', marginBottom: '4px' }}>
                        YouTube Video ID / URL:
                      </label>
                      <input
                        type="text"
                        placeholder={currentPreset.videoId || 'e.g. UC7GZguUCh8gdEs-VKhWqkWA'}
                        value={customVideoId}
                        onChange={(e) => setCustomVideoId(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '8px 10px',
                          borderRadius: '8px',
                          border: '1px solid #CBD5E1',
                          fontSize: '12px',
                          outline: 'none',
                          boxSizing: 'border-box',
                        }}
                      />
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                      <div>
                        <label style={{ fontSize: '11px', fontWeight: 700, color: '#475569', display: 'block', marginBottom: '4px' }}>
                          Kategori:
                        </label>
                        <select
                          value={customCategory}
                          onChange={(e) => setCustomCategory(e.target.value)}
                          style={{
                            width: '100%',
                            padding: '8px',
                            borderRadius: '8px',
                            border: '1px solid #CBD5E1',
                            fontSize: '12px',
                            outline: 'none',
                            boxSizing: 'border-box',
                          }}
                        >
                          <option value="technology">technology</option>
                          <option value="programming">programming</option>
                          <option value="artificial-intelligence">artificial-intelligence</option>
                          <option value="general">general</option>
                        </select>
                      </div>
                      <div>
                        <label style={{ fontSize: '11px', fontWeight: 700, color: '#475569', display: 'block', marginBottom: '4px' }}>
                          Target URL Referensi:
                        </label>
                        <input
                          type="text"
                          placeholder={currentPreset.defaultUrls || 'https://...'}
                          value={customUrls}
                          onChange={(e) => setCustomUrls(e.target.value)}
                          style={{
                            width: '100%',
                            padding: '8px 10px',
                            borderRadius: '8px',
                            border: '1px solid #CBD5E1',
                            fontSize: '12px',
                            outline: 'none',
                            boxSizing: 'border-box',
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Dry Run Checkbox */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '2px 0' }}>
                <input
                  type="checkbox"
                  id="dryRunCheckbox"
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                  style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                />
                <label
                  htmlFor="dryRunCheckbox"
                  style={{ fontSize: '12px', color: '#30343A', cursor: 'pointer', fontWeight: 600 }}
                >
                  Dry-Run Mode (Simulasi visual 3D & SOP tanpa publish HTTP ke CMS luar)
                </label>
              </div>

              {/* Status / Feedback message */}
              {dispatchResult && (
                <div
                  style={{
                    padding: '10px 14px',
                    borderRadius: '10px',
                    fontSize: '12.5px',
                    background: dispatchResult.includes('✅')
                      ? 'rgba(34, 197, 94, 0.15)'
                      : 'rgba(239, 68, 68, 0.15)',
                    border: `1px solid ${dispatchResult.includes('✅') ? '#86efac' : '#fca5a5'}`,
                    color: dispatchResult.includes('✅') ? '#166534' : '#991b1b',
                    fontWeight: 700,
                  }}
                >
                  {dispatchResult}
                </div>
              )}

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
                <button
                  type="button"
                  onClick={() => setDispatchModalOpen(false)}
                  style={{
                    flex: 1,
                    padding: '12px',
                    borderRadius: '12px',
                    background: 'rgba(48, 52, 58, 0.08)',
                    border: 'none',
                    color: '#64748B',
                    fontSize: '13px',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{
                    flex: 2,
                    padding: '12px',
                    borderRadius: '12px',
                    background: 'linear-gradient(135deg, #354A60, #D98078)',
                    border: 'none',
                    color: '#ffffff',
                    fontSize: '13px',
                    fontWeight: 800,
                    cursor: 'pointer',
                    boxShadow: '0 4px 14px rgba(53, 74, 96, 0.25)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                  }}
                >
                  <Send size={15} />
                  <span>{isSubmitting ? 'Mengirim ke Squad...' : `Luncurkan Misi: ${currentPreset.title.split(':')[0]}`}</span>
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* 7. EDITORIAL CALENDAR & OBSERVABILITY MODAL (Bay-Zero Planner) */}
      {scheduleModalOpen && createPortal(
        <div
          className="punggawa-portal-modal-backdrop"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(30, 33, 40, 0.75)',
            backdropFilter: 'blur(14px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 999999,
            pointerEvents: 'auto',
          }}
        >
          <div
            className="warm-panel-accent"
            style={{
              width: '940px',
              maxWidth: '95vw',
              maxHeight: '90vh',
              overflowY: 'auto',
              borderRadius: '24px',
              padding: '26px',
              background: 'rgba(248, 246, 240, 0.98)',
              boxShadow: '0 24px 60px rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(196, 154, 108, 0.4)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '14px',
                borderBottom: '1px solid rgba(48, 52, 58, 0.1)',
                flexWrap: 'wrap',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '12px',
                    background: 'linear-gradient(135deg, #354A60, #D98078)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 4px 12px rgba(53, 74, 96, 0.25)',
                  }}
                >
                  <Calendar size={20} color="#ffffff" />
                </div>
                <div>
                  <h3 style={{ fontSize: '17px', fontWeight: 900, margin: 0, color: '#2B3038' }}>
                    Kalender Editorial & Observability Jadwal
                  </h3>
                  <p style={{ fontSize: '11px', color: '#8A8A82', margin: '2px 0 0 0' }}>
                    Perencanaan otonom Bay-Zero (Stark @ 09:00 WIB, Usagi @ 19:00 WIB) & Pelaporan Real-Time
                  </p>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button
                  type="button"
                  onClick={
                    authToken
                      ? handleGenerateWeeklyPlan
                      : () => {
                          setAuthError('Silakan masukkan password pengelola untuk membuat jadwal baru.');
                          setAuthModalOpen(true);
                        }
                  }
                  disabled={isLoadingSchedules}
                  style={{
                    background: authToken
                      ? 'linear-gradient(135deg, #354A60, #8DA895)'
                      : 'rgba(53, 74, 96, 0.45)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '8px 14px',
                    fontSize: '12px',
                    fontWeight: 800,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    cursor: isLoadingSchedules ? 'not-allowed' : 'pointer',
                    boxShadow: '0 4px 12px rgba(53, 74, 96, 0.2)',
                  }}
                  title={
                    authToken
                      ? 'Tarik tren Google News, GitHub & YouTube untuk menyusun kalender 7 hari ke depan (Smart Conflict-Free Merging)'
                      : 'Login pengelola diperlukan untuk menyusun jadwal baru'
                  }
                >
                  <RefreshCw size={13} className={isLoadingSchedules ? 'animate-spin' : ''} />
                  <span>{isLoadingSchedules ? 'Menyusun...' : '⚡ Generate Jadwal 7 Hari'}</span>
                </button>

                <button
                  type="button"
                  onClick={fetchSchedules}
                  disabled={isLoadingSchedules}
                  style={{
                    background: 'rgba(255, 255, 255, 0.85)',
                    color: '#30343A',
                    border: '1px solid rgba(48, 52, 58, 0.15)',
                    borderRadius: '10px',
                    padding: '8px 12px',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                  title="Segarkan data jadwal"
                >
                  <RefreshCw size={13} />
                  <span>Refresh</span>
                </button>

                <button
                  type="button"
                  onClick={handleCleanupDuplicates}
                  disabled={isLoadingSchedules}
                  style={{
                    background: 'rgba(239, 68, 68, 0.08)',
                    color: '#DC2626',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    borderRadius: '10px',
                    padding: '8px 12px',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                  title="Hapus jadwal pending/failed duplikat yang memiliki judul sama"
                >
                  <Trash2 size={13} />
                  <span>Bersihkan Duplikat</span>
                </button>

                <button
                  type="button"
                  onClick={() => setScheduleModalOpen(false)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#8A8A82',
                    fontSize: '20px',
                    cursor: 'pointer',
                    padding: '4px 8px',
                  }}
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Notification alert banner */}
            {scheduleActionMsg && (
              <div
                style={{
                  padding: '10px 14px',
                  borderRadius: '10px',
                  fontSize: '12px',
                  fontWeight: 700,
                  background: scheduleActionMsg.includes('❌')
                    ? 'rgba(239, 68, 68, 0.15)'
                    : 'rgba(16, 185, 129, 0.15)',
                  border: `1px solid ${
                    scheduleActionMsg.includes('❌') ? '#fca5a5' : '#86efac'
                  }`,
                  color: scheduleActionMsg.includes('❌') ? '#991b1b' : '#166534',
                }}
              >
                {scheduleActionMsg}
              </div>
            )}

            {/* Filter Tabs & Time Window Selector */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {[
                  { id: 'all', label: 'Semua', count: scheduleCounts.all },
                  { id: 'pending', label: '⏳ Pending', count: scheduleCounts.pending },
                  { id: 'in_progress', label: '⚡ Berjalan', count: scheduleCounts.in_progress },
                  { id: 'completed', label: '✅ Selesai', count: scheduleCounts.completed },
                  { id: 'failed', label: '❌ Gagal', count: scheduleCounts.failed },
                  { id: 'discarded', label: '🗑️ Sampah', count: scheduleCounts.discarded },
                ].map((tab) => {
                  const active = scheduleFilter === tab.id;
                  const isTrash = tab.id === 'discarded';
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setScheduleFilter(tab.id as any)}
                      style={{
                        padding: '6px 11px',
                        borderRadius: '8px',
                        border: active
                          ? isTrash
                            ? '1.5px solid #DC2626'
                            : '1.5px solid #354A60'
                          : '1px solid rgba(48, 52, 58, 0.12)',
                        background: active
                          ? isTrash
                            ? '#DC2626'
                            : '#354A60'
                          : isTrash
                          ? 'rgba(254, 242, 242, 0.7)'
                          : 'rgba(255, 255, 255, 0.8)',
                        color: active ? '#ffffff' : isTrash ? '#B91C1C' : '#30343A',
                        fontSize: '11.5px',
                        fontWeight: active ? 800 : 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      <span>{tab.label}</span>
                      <span
                        style={{
                          padding: '1px 5px',
                          borderRadius: '10px',
                          fontSize: '10px',
                          background: active
                            ? 'rgba(255, 255, 255, 0.25)'
                            : isTrash
                            ? 'rgba(239, 68, 68, 0.15)'
                            : 'rgba(48, 52, 58, 0.08)',
                          color: active ? '#ffffff' : isTrash ? '#DC2626' : '#64748B',
                        }}
                      >
                        {tab.count}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Time Window (Rentang Waktu Tampilan) & Empty Trash Action */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {scheduleFilter === 'discarded' && scheduleCounts.discarded > 0 && authToken && (
                  <button
                    type="button"
                    onClick={handleEmptyTrash}
                    style={{
                      background: 'rgba(239, 68, 68, 0.15)',
                      border: '1px solid rgba(239, 68, 68, 0.35)',
                      color: '#DC2626',
                      borderRadius: '8px',
                      padding: '5px 10px',
                      fontSize: '11px',
                      fontWeight: 800,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <Trash2 size={12} />
                    <span>Kosongkan Sampah</span>
                  </button>
                )}

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    background: 'rgba(244, 241, 234, 0.9)',
                    padding: '3px 6px',
                    borderRadius: '8px',
                    border: '1px solid rgba(48, 52, 58, 0.1)',
                    fontSize: '11px',
                  }}
                >
                  <span style={{ color: '#8A8A82', fontWeight: 600, fontSize: '10.5px' }}>Rentang:</span>
                  {(['7days', '14days', 'all'] as const).map((mode) => {
                    const sel = scheduleDaysFilter === mode;
                    const label = mode === '7days' ? '±7 Hari' : mode === '14days' ? '±14 Hari' : 'Semua';
                    return (
                      <button
                        key={mode}
                        type="button"
                        onClick={() => setScheduleDaysFilter(mode)}
                        style={{
                          background: sel ? '#354A60' : 'transparent',
                          color: sel ? '#ffffff' : '#475569',
                          border: 'none',
                          borderRadius: '5px',
                          padding: '2px 7px',
                          fontSize: '10.5px',
                          fontWeight: sel ? 800 : 500,
                          cursor: 'pointer',
                        }}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Schedules Table */}
            <div
              style={{
                borderRadius: '12px',
                border: '1px solid rgba(48, 52, 58, 0.12)',
                background: '#FFFFFF',
                overflow: 'hidden',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
              }}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '100px 135px 95px 1fr 195px',
                  gap: '8px',
                  padding: '10px 14px',
                  background: 'rgba(244, 241, 234, 0.85)',
                  borderBottom: '1px solid rgba(48, 52, 58, 0.1)',
                  fontSize: '11px',
                  fontWeight: 800,
                  color: '#64748B',
                  letterSpacing: '0.04em',
                }}
              >
                <span>STATUS</span>
                <span>WAKTU (WIB)</span>
                <span>AGEN</span>
                <span>JUDUL & KONTEN</span>
                <span style={{ textAlign: 'right' }}>OBSERVABILITY / AKSI</span>
              </div>

              <div style={{ maxHeight: '440px', overflowY: 'auto' }}>
                {filteredSchedules.length === 0 ? (
                  <div
                    style={{
                      padding: '36px 20px',
                      textAlign: 'center',
                      color: '#8A8A82',
                      fontSize: '12px',
                    }}
                  >
                    {isLoadingSchedules ? (
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                        <RefreshCw size={14} className="animate-spin" />
                        <span>Mengambil daftar jadwal konten...</span>
                      </div>
                    ) : (
                      <div>
                        Belum ada jadwal dalam kategori ini. Klik tombol <strong>'Generate Jadwal 7 Hari'</strong> untuk menyusun rencana editorial baru.
                      </div>
                    )}
                  </div>
                ) : (
                  filteredSchedules.map((sched) => {
                    const isFailed = sched.status === 'failed';
                    const isCompleted = sched.status === 'completed';
                    const isInProgress = sched.status === 'in_progress';
                    const isPending = sched.status === 'pending';
                    const isDiscarded = sched.status === 'discarded';
                    const isErrorExpanded = expandedSchedErrorId === sched.id;

                    return (
                      <div
                        key={sched.id}
                        style={{
                          borderBottom: '1px solid rgba(48, 52, 58, 0.06)',
                          background: isDiscarded
                            ? 'rgba(241, 245, 249, 0.7)'
                            : isFailed
                            ? 'rgba(254, 242, 242, 0.6)'
                            : isCompleted
                            ? 'rgba(240, 253, 244, 0.6)'
                            : isInProgress
                            ? 'rgba(239, 246, 255, 0.6)'
                            : '#FFFFFF',
                          padding: '10px 14px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px',
                          opacity: isDiscarded ? 0.8 : 1,
                        }}
                      >
                        <div
                          style={{
                            display: 'grid',
                            gridTemplateColumns: '100px 135px 95px 1fr 195px',
                            gap: '8px',
                            alignItems: 'center',
                            fontSize: '12px',
                          }}
                        >
                          {/* Status Badge */}
                          <div>
                            <span
                              style={{
                                display: 'inline-block',
                                padding: '3px 8px',
                                borderRadius: '6px',
                                fontSize: '10px',
                                fontWeight: 800,
                                textTransform: 'uppercase',
                                background: isDiscarded
                                  ? 'rgba(100, 116, 139, 0.18)'
                                  : isFailed
                                  ? 'rgba(239, 68, 68, 0.18)'
                                  : isCompleted
                                  ? 'rgba(16, 185, 129, 0.18)'
                                  : isInProgress
                                  ? 'rgba(59, 130, 246, 0.18)'
                                  : 'rgba(245, 158, 11, 0.18)',
                                color: isDiscarded
                                  ? '#475569'
                                  : isFailed
                                  ? '#DC2626'
                                  : isCompleted
                                  ? '#059669'
                                  : isInProgress
                                  ? '#2563EB'
                                  : '#D97706',
                                border: `1px solid ${
                                  isDiscarded
                                    ? 'rgba(100, 116, 139, 0.35)'
                                    : isFailed
                                    ? 'rgba(239, 68, 68, 0.35)'
                                    : isCompleted
                                    ? 'rgba(16, 185, 129, 0.35)'
                                    : isInProgress
                                    ? 'rgba(59, 130, 246, 0.35)'
                                    : 'rgba(245, 158, 11, 0.35)'
                                }`,
                              }}
                            >
                              {isDiscarded
                                ? '🗑️ Sampah'
                                : isFailed
                                ? '❌ Gagal'
                                : isCompleted
                                ? '✅ Selesai'
                                : isInProgress
                                ? '⚡ Berjalan'
                                : '⏳ Pending'}
                            </span>
                          </div>

                          {/* Schedule Time (WIB) */}
                          <div style={{ color: '#475569', fontSize: '11.5px', fontWeight: 600 }}>
                            {formatScheduleTime(sched.scheduled_at)}
                          </div>

                          {/* Agent Name */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                            <span>
                              {sched.agent_name === 'Stark'
                                ? '⚡'
                                : sched.agent_name === 'Usagi'
                                ? '🦊'
                                : '📋'}
                            </span>
                            <span style={{ fontWeight: 800, color: '#30343A' }}>
                              {sched.agent_name}
                            </span>
                          </div>

                          {/* Title & Task Type */}
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', paddingRight: '12px' }}>
                            <span style={{ fontWeight: 700, color: '#2B3038', lineHeight: 1.3 }}>
                              {sched.title}
                            </span>
                            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                              <span
                                style={{
                                  fontSize: '9.5px',
                                  padding: '1px 5px',
                                  borderRadius: '4px',
                                  background: 'rgba(48, 52, 58, 0.08)',
                                  color: '#64748B',
                                  fontWeight: 600,
                                }}
                              >
                                {sched.task_type}
                              </span>
                              {sched.payload?.category && (
                                <span style={{ fontSize: '9.5px', color: '#94A3B8' }}>
                                  • {sched.payload.category}
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Observability / Action Button */}
                          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '6px' }}>
                            {isDiscarded && (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
                                <button
                                  type="button"
                                  onClick={() => handleRestoreSchedule(sched.id, sched.title)}
                                  title="Pulihkan jadwal ini kembali ke status pending"
                                  style={{
                                    background: 'rgba(16, 185, 129, 0.15)',
                                    border: '1px solid rgba(16, 185, 129, 0.35)',
                                    color: '#059669',
                                    borderRadius: '6px',
                                    padding: '4px 8px',
                                    fontSize: '11px',
                                    fontWeight: 700,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                  }}
                                >
                                  <RotateCcw size={11} />
                                  <span>Pulihkan</span>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteSchedule(sched.id, sched.title, true)}
                                  title="Hapus permanen dari database"
                                  style={{
                                    background: 'rgba(239, 68, 68, 0.12)',
                                    border: '1px solid rgba(239, 68, 68, 0.25)',
                                    color: '#DC2626',
                                    borderRadius: '6px',
                                    padding: '4px 7px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '2px',
                                  }}
                                >
                                  <Trash2 size={11} />
                                </button>
                              </div>
                            )}

                            {isCompleted && (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
                                {sched.result_url && (
                                  <a
                                    href={sched.result_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      gap: '4px',
                                      fontSize: '11px',
                                      color: '#0284C7',
                                      fontWeight: 700,
                                      textDecoration: 'underline',
                                    }}
                                  >
                                    <span>Hasil Publikasi</span>
                                    <ExternalLink size={11} />
                                  </a>
                                )}
                                <button
                                  type="button"
                                  onClick={() => handleDeleteSchedule(sched.id, sched.title, false)}
                                  title="Pindahkan riwayat jadwal selesai ini ke Recycle Bin"
                                  style={{
                                    background: 'rgba(100, 116, 139, 0.12)',
                                    border: '1px solid rgba(100, 116, 139, 0.25)',
                                    color: '#64748B',
                                    borderRadius: '6px',
                                    padding: '4px 6px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                  }}
                                >
                                  <Trash2 size={11} />
                                </button>
                              </div>
                            )}

                            {isFailed && (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', justifyContent: 'flex-end' }}>
                                <button
                                  type="button"
                                  onClick={() =>
                                    setExpandedSchedErrorId(
                                      isErrorExpanded ? null : sched.id
                                    )
                                  }
                                  style={{
                                    background: 'rgba(239, 68, 68, 0.15)',
                                    border: '1px solid rgba(239, 68, 68, 0.35)',
                                    color: '#DC2626',
                                    borderRadius: '6px',
                                    padding: '3px 8px',
                                    fontSize: '10.5px',
                                    fontWeight: 700,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '3px',
                                  }}
                                >
                                  <span>{isErrorExpanded ? 'Tutup' : 'Alasan'}</span>
                                  {isErrorExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                                </button>
                                {authToken && (
                                  <button
                                    type="button"
                                    onClick={() => handleTriggerScheduleNow(sched.id)}
                                    title="Coba eksekusi ulang jadwal yang gagal"
                                    style={{
                                      background: '#DC2626',
                                      border: 'none',
                                      color: '#FFFFFF',
                                      borderRadius: '6px',
                                      padding: '3px 8px',
                                      fontSize: '10.5px',
                                      fontWeight: 800,
                                      cursor: 'pointer',
                                    }}
                                  >
                                    Retry
                                  </button>
                                )}
                                <button
                                  type="button"
                                  onClick={() => handleDeleteSchedule(sched.id, sched.title, false)}
                                  title="Pindahkan jadwal gagal ini ke Recycle Bin (blacklist dari auto-planner)"
                                  style={{
                                    background: 'rgba(100, 116, 139, 0.12)',
                                    border: '1px solid rgba(100, 116, 139, 0.25)',
                                    color: '#64748B',
                                    borderRadius: '6px',
                                    padding: '4px 6px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                  }}
                                >
                                  <Trash2 size={11} />
                                </button>
                              </div>
                            )}

                            {isPending && (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', justifyContent: 'flex-end' }}>
                                {authToken ? (
                                  <button
                                    type="button"
                                    onClick={() => handleTriggerScheduleNow(sched.id)}
                                    style={{
                                      background: 'linear-gradient(135deg, #354A60, #D98078)',
                                      color: '#ffffff',
                                      border: 'none',
                                      borderRadius: '6px',
                                      padding: '4px 9px',
                                      fontSize: '11px',
                                      fontWeight: 800,
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '4px',
                                      boxShadow: '0 2px 6px rgba(53, 74, 96, 0.2)',
                                    }}
                                  >
                                    <Play size={10} fill="#ffffff" />
                                    <span>Trigger</span>
                                  </button>
                                ) : (
                                  <span style={{ fontSize: '11px', color: '#8A8A82', fontStyle: 'italic', marginRight: '4px' }}>
                                    Terjadwal
                                  </span>
                                )}
                                <button
                                  type="button"
                                  onClick={() => handleDeleteSchedule(sched.id, sched.title, false)}
                                  title="Tolak dan pindahkan ke Recycle Bin (jangan pernah jadwalkan lagi)"
                                  style={{
                                    background: 'rgba(239, 68, 68, 0.12)',
                                    border: '1px solid rgba(239, 68, 68, 0.25)',
                                    color: '#DC2626',
                                    borderRadius: '6px',
                                    padding: '4px 6px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '2px',
                                  }}
                                >
                                  <Trash2 size={11} />
                                </button>
                              </div>
                            )}

                            {isInProgress && (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
                                <span style={{ fontSize: '11px', color: '#2563EB', fontWeight: 700 }}>
                                  Berjalan...
                                </span>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteSchedule(sched.id, sched.title, false)}
                                  title="Batalkan / pindahkan jadwal ini ke Recycle Bin"
                                  style={{
                                    background: 'rgba(239, 68, 68, 0.12)',
                                    border: '1px solid rgba(239, 68, 68, 0.25)',
                                    color: '#DC2626',
                                    borderRadius: '6px',
                                    padding: '4px 6px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '2px',
                                  }}
                                >
                                  <Trash2 size={11} />
                                </button>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Error details callout if expanded */}
                        {isErrorExpanded && sched.error_message && (
                          <div
                            style={{
                              marginTop: '4px',
                              padding: '10px 12px',
                              borderRadius: '8px',
                              background: 'rgba(239, 68, 68, 0.08)',
                              border: '1px solid rgba(239, 68, 68, 0.25)',
                              color: '#B91C1C',
                              fontSize: '11px',
                              lineHeight: 1.45,
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '6px',
                            }}
                          >
                            <div
                              style={{
                                fontWeight: 800,
                                marginBottom: '2px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                            >
                              <AlertCircle size={12} />
                              <span>DETAIL KESALAHAN EKSEKUSI:</span>
                            </div>
                            <code style={{ fontSize: '11px', color: '#991B1B' }}>{sched.error_message}</code>

                            {/* Admin Technical Diagnostics Inspector for Schedule */}
                            {authToken ? (
                              <div
                                style={{
                                  marginTop: '6px',
                                  padding: '8px 10px',
                                  borderRadius: '6px',
                                  background: 'rgba(30, 41, 59, 0.95)',
                                  border: '1px solid rgba(59, 130, 246, 0.35)',
                                  color: '#F8FAFC',
                                  fontSize: '10.5px',
                                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
                                }}
                              >
                                <div
                                  style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    marginBottom: '6px',
                                    paddingBottom: '4px',
                                    borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
                                  }}
                                >
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#38BDF8', fontWeight: 800 }}>
                                    <Bug size={12} />
                                    <span>DIAGNOSTIK TEKNIS JADWAL (ADMIN AKTIF)</span>
                                  </div>
                                  <span style={{ fontSize: '9.5px', color: '#94A3B8', fontFamily: 'monospace' }}>
                                    ID: {sched.id}
                                  </span>
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 10px', fontSize: '10.5px' }}>
                                  <span style={{ color: '#94A3B8', fontWeight: 600 }}>Tipe Konten:</span>
                                  <span style={{ color: '#FCD34D', fontFamily: 'monospace', fontWeight: 700 }}>
                                    {sched.task_type || '-'}
                                  </span>

                                  <span style={{ color: '#94A3B8', fontWeight: 600 }}>Aktor Agen:</span>
                                  <span style={{ color: '#E2E8F0' }}>
                                    {sched.agent_name || '-'}
                                  </span>

                                  {sched.payload?.input_data?.video_id && (
                                    <>
                                      <span style={{ color: '#94A3B8', fontWeight: 600 }}>Video ID:</span>
                                      <span style={{ color: '#67E8F9', fontFamily: 'monospace', fontWeight: 700 }}>
                                        {sched.payload.input_data.video_id}
                                      </span>
                                    </>
                                  )}

                                  {sched.payload?.input_data?.urls && (
                                    <>
                                      <span style={{ color: '#94A3B8', fontWeight: 600 }}>Input URLs:</span>
                                      <span style={{ color: '#E2E8F0', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                        {Array.isArray(sched.payload.input_data.urls)
                                          ? sched.payload.input_data.urls.join(', ')
                                          : String(sched.payload.input_data.urls)}
                                      </span>
                                    </>
                                  )}
                                </div>

                                {/* Raw Payload JSON */}
                                {sched.payload && (
                                  <details style={{ marginTop: '8px' }}>
                                    <summary
                                      style={{
                                        cursor: 'pointer',
                                        color: '#93C5FD',
                                        fontWeight: 700,
                                        fontSize: '10px',
                                        userSelect: 'none',
                                        outline: 'none',
                                      }}
                                    >
                                      ▶ Raw Schedule Payload JSON
                                    </summary>
                                    <pre
                                      style={{
                                        marginTop: '4px',
                                        padding: '6px',
                                        background: 'rgba(15, 23, 42, 0.85)',
                                        borderRadius: '4px',
                                        overflowX: 'auto',
                                        fontSize: '9.5px',
                                        color: '#A7F3D0',
                                        maxHeight: '120px',
                                      }}
                                    >
                                      {JSON.stringify(sched.payload, null, 2)}
                                    </pre>
                                  </details>
                                )}
                              </div>
                            ) : (
                              <div
                                style={{
                                  marginTop: '4px',
                                  fontSize: '10px',
                                  color: '#6B7280',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  fontStyle: 'italic',
                                }}
                              >
                                <Lock size={10} />
                                <span>Masuk dengan Password Admin untuk melihat detail payload teknis.</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '11px',
                color: '#8A8A82',
                paddingTop: '6px',
              }}
            >
              <div>
                Worker ticker memeriksa tabel <code>content_schedules</code> setiap 60 detik.
              </div>
              <button
                type="button"
                onClick={() => setScheduleModalOpen(false)}
                style={{
                  padding: '8px 18px',
                  borderRadius: '8px',
                  background: 'rgba(48, 52, 58, 0.08)',
                  border: 'none',
                  color: '#475569',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                Tutup Kalender
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* 6. MICROSERVICES UPTIME & OBSERVABILITY MODAL */}
      {servicesModalOpen && createPortal(
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 999999,
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
            pointerEvents: 'auto',
          }}
          onClick={() => setServicesModalOpen(false)}
        >
          <div
            className="warm-panel"
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: '740px',
              maxHeight: '88vh',
              borderRadius: '20px',
              padding: '24px',
              background: 'rgba(248, 246, 240, 0.98)',
              border: isDegraded ? '2px solid rgba(239, 68, 68, 0.5)' : '1px solid rgba(196, 154, 108, 0.35)',
              boxShadow: isDegraded
                ? '0 20px 50px rgba(239, 68, 68, 0.25), 0 0 30px rgba(239, 68, 68, 0.15)'
                : '0 20px 50px rgba(0, 0, 0, 0.25)',
              display: 'flex',
              flexDirection: 'column',
              gap: '18px',
              overflow: 'hidden',
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '14px',
                borderBottom: '1px solid rgba(48, 52, 58, 0.1)',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '12px',
                    background: isDegraded
                      ? 'linear-gradient(135deg, #DC2626, #EF4444)'
                      : 'linear-gradient(135deg, #059669, #10B981)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: isDegraded
                      ? '0 4px 14px rgba(220, 38, 38, 0.35)'
                      : '0 4px 14px rgba(16, 185, 129, 0.35)',
                  }}
                >
                  <Server size={22} color="#ffffff" />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '17px', fontWeight: 900, margin: 0, color: '#2B3038' }}>
                      Microservices Uptime & Observability
                    </h3>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 800,
                        padding: '2px 8px',
                        borderRadius: '10px',
                        background: isDegraded ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                        color: isDegraded ? '#DC2626' : '#059669',
                        border: `1px solid ${isDegraded ? 'rgba(239, 68, 68, 0.4)' : 'rgba(16, 185, 129, 0.4)'}`,
                      }}
                    >
                      {isDegraded ? 'DEGRADED' : 'OPERATIONAL'}
                    </span>
                  </div>
                  <p style={{ fontSize: '11px', color: '#8A8A82', margin: '2px 0 0 0' }}>
                    Dikelola oleh Bay-Zero (Server & Quality Inspector) • Pemantauan ketersediaan endpoint periodik (1 jam sekali) • Redis Caching • Zero LLM Cost
                  </p>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button
                  type="button"
                  onClick={onRecheckHealth}
                  disabled={isRechecking}
                  style={{
                    background: 'linear-gradient(135deg, #354A60, #8DA895)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '8px 14px',
                    fontSize: '12px',
                    fontWeight: 800,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    cursor: isRechecking ? 'not-allowed' : 'pointer',
                    boxShadow: '0 4px 12px rgba(53, 74, 96, 0.2)',
                    opacity: isRechecking ? 0.75 : 1,
                  }}
                  title="Ping semua service sekarang dan perbarui cache"
                >
                  <RefreshCw size={13} className={isRechecking ? 'animate-spin' : ''} />
                  <span>{isRechecking ? 'Memeriksa...' : 'Cek Ulang Sekarang'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => setServicesModalOpen(false)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#8A8A82',
                    fontSize: '20px',
                    cursor: 'pointer',
                    padding: '4px 8px',
                  }}
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Status Summary Banner */}
            {isDegraded ? (
              <div
                style={{
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '12px',
                  padding: '12px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                }}
              >
                <AlertTriangle size={24} color="#DC2626" style={{ flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#DC2626' }}>
                    PERINGATAN GANGGUAN LAYANAN TERDETEKSI
                  </div>
                  <div style={{ fontSize: '11px', color: '#7F1D1D', marginTop: '2px' }}>
                    Satu atau lebih microservice eksternal mengalami timeout atau mengembalikan HTTP status selain 200 OK. Lampu indikator rak server di visualizer 3D menyala merah.
                  </div>
                </div>
              </div>
            ) : (
              <div
                style={{
                  background: 'rgba(16, 185, 129, 0.08)',
                  border: '1px solid rgba(16, 185, 129, 0.25)',
                  borderRadius: '12px',
                  padding: '12px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                }}
              >
                <CheckCircle2 size={24} color="#059669" style={{ flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#059669' }}>
                    SEMUA SISTEM BERJALAN NORMAL
                  </div>
                  <div style={{ fontSize: '11px', color: '#065F46', marginTop: '2px' }}>
                    Seluruh endpoint microservice yang dipantau merespons dengan HTTP 200 OK. Server rack blade di kantor 3D berstatus normal (lampu hijau aktif).
                  </div>
                </div>
              </div>
            )}

            {/* Monitored Services List */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                overflowY: 'auto',
                maxHeight: '48vh',
                paddingRight: '4px',
              }}
            >
              {(healthData?.services || []).map((srv) => {
                const isHealthy = srv.status === 'healthy';
                return (
                  <div
                    key={srv.id}
                    style={{
                      background: 'rgba(255, 255, 255, 0.95)',
                      border: `1px solid ${isHealthy ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.4)'}`,
                      borderRadius: '12px',
                      padding: '14px 16px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span
                          style={{
                            width: '10px',
                            height: '10px',
                            borderRadius: '50%',
                            background: isHealthy ? '#10B981' : '#EF4444',
                            boxShadow: `0 0 8px ${isHealthy ? '#10B981' : '#EF4444'}`,
                            flexShrink: 0,
                          }}
                        />
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 800, color: '#1E293B' }}>
                            {srv.name}
                          </div>
                          <a
                            href={srv.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              fontSize: '11px',
                              color: '#64748B',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              textDecoration: 'none',
                            }}
                          >
                            <span>{srv.url}</span>
                            <ExternalLink size={10} />
                          </a>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {/* Status Badge */}
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 800,
                            padding: '3px 8px',
                            borderRadius: '6px',
                            background: isHealthy ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                            color: isHealthy ? '#059669' : '#DC2626',
                            border: `1px solid ${isHealthy ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)'}`,
                          }}
                        >
                          {isHealthy ? 'HEALTHY' : 'DOWN'}
                        </span>

                        {/* HTTP Status Code */}
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '3px 8px',
                            borderRadius: '6px',
                            background: '#F1F5F9',
                            color: isHealthy ? '#0F766E' : '#B91C1C',
                          }}
                        >
                          HTTP {srv.status_code ?? 'ERR'}
                        </span>

                        {/* Latency */}
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '3px 8px',
                            borderRadius: '6px',
                            background: srv.latency_ms > 1000 ? '#FEF2F2' : '#F0FDF4',
                            color: srv.latency_ms > 1000 ? '#DC2626' : '#15803D',
                          }}
                        >
                          ⚡ {srv.latency_ms} ms
                        </span>
                      </div>
                    </div>

                    {/* Error details if unhealthy */}
                    {!isHealthy && srv.error && (
                      <div
                        style={{
                          background: 'rgba(239, 68, 68, 0.08)',
                          border: '1px solid rgba(239, 68, 68, 0.25)',
                          borderRadius: '8px',
                          padding: '8px 12px',
                          fontSize: '11px',
                          color: '#DC2626',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <AlertCircle size={13} style={{ flexShrink: 0 }} />
                        <span><strong>Alasan Gangguan:</strong> {srv.error}</span>
                      </div>
                    )}

                    {/* Last checked timestamp */}
                    <div style={{ fontSize: '10px', color: '#94A3B8', textAlign: 'right' }}>
                      Terakhir dicek: {srv.last_checked ? new Date(srv.last_checked * 1000).toLocaleString('id-ID') : '-'} WIB
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '11px',
                color: '#8A8A82',
                paddingTop: '6px',
                borderTop: '1px solid rgba(48, 52, 58, 0.08)',
              }}
            >
              <div>
                Auto-check interval: <strong>3600s (1 jam)</strong> via background worker. Redis key: <code>system:services_health</code>.
              </div>
              <button
                type="button"
                onClick={() => setServicesModalOpen(false)}
                style={{
                  padding: '8px 18px',
                  borderRadius: '8px',
                  background: 'rgba(48, 52, 58, 0.08)',
                  border: 'none',
                  color: '#475569',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                Tutup
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* 9. CAREER-OPS & TALENT OPPORTUNITIES MODAL (Clara) */}
      <CareerOpsModal
        isOpen={jobModalOpen}
        onClose={() => setJobModalOpen(false)}
        onOpenDispatch={handleOpenDispatch}
      />
    </div>
  );
}
