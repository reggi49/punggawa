/**
 * statusLabels.ts
 * Penerjemahan status teknis LangGraph ke label humanis Retro-Cyberpunk Pop & Synthwave.
 */

export interface HumanStatusConfig {
  label: string;
  action:
    | 'idle_coffee'
    | 'walk_to_desk'
    | 'searching_archive'
    | 'intense_typing'
    | 'drawing_canvas'
    | 'inspecting_sop'
    | 'success_celebration'
    | 'confused_scratch'
    | 'observing'
    | 'offline_rest';
  color: string;
  glowColor: string;
  badgeBg: string;
  description: string;
  icon: string;
  responsibleWorker: 'stark' | 'usagi' | 'bayzero' | 'team';
}

export const STATUS_LABELS: Record<string, HumanStatusConfig> = {
  IDLE: {
    label: 'Santai Ngopi ☕',
    action: 'idle_coffee',
    color: '#06b6d4',
    glowColor: '#0891b2',
    badgeBg: 'rgba(6, 182, 212, 0.2)',
    description: 'Seluruh kru bersantai di sofa synthwave, menikmati secangkir kopi hangat.',
    icon: '☕',
    responsibleWorker: 'team',
  },
  idle_coffee: {
    label: 'Santai Ngopi ☕',
    action: 'idle_coffee',
    color: '#06b6d4',
    glowColor: '#0891b2',
    badgeBg: 'rgba(6, 182, 212, 0.2)',
    description: 'Menikmati jeda istirahat sambil menunggu instruksi misi berikutnya.',
    icon: '☕',
    responsibleWorker: 'team',
  },
  STREAM_INIT: {
    label: 'Sistem Terhubung 📡',
    action: 'idle_coffee',
    color: '#10b981',
    glowColor: '#059669',
    badgeBg: 'rgba(16, 185, 129, 0.2)',
    description: 'Jaringan Redis & SSE Pub/Sub terhubung ke markas virtual.',
    icon: '📡',
    responsibleWorker: 'team',
  },
  ingest_node: {
    label: 'Mengambil Berkas 📥',
    action: 'walk_to_desk',
    color: '#38bdf8',
    glowColor: '#0284c7',
    badgeBg: 'rgba(56, 189, 248, 0.22)',
    description: 'Karakter bangkit, mengambil berkas tugas, dan menuju terminal kerja.',
    icon: '📥',
    responsibleWorker: 'stark',
  },
  ingest_trend_node: {
    label: 'Kurasi Tren Web 🚀',
    action: 'searching_archive',
    color: '#6366f1',
    glowColor: '#4f46e5',
    badgeBg: 'rgba(99, 102, 241, 0.22)',
    description: 'Menarik berita terkini dari Google News RSS & repositori viral GitHub Trending Weekly.',
    icon: '🚀',
    responsibleWorker: 'stark',
  },
  scrape_node: {
    label: 'Riset & Jelajah Web 🌐',
    action: 'searching_archive',
    color: '#f59e0b',
    glowColor: '#d97706',
    badgeBg: 'rgba(245, 158, 11, 0.22)',
    description: 'Menelusuri mainframe server & lemari data untuk mengekstrak materi referensi.',
    icon: '🌐',
    responsibleWorker: 'stark',
  },
  draft_node: {
    label: 'Mengetik Naskah Cepat ⚡',
    action: 'intense_typing',
    color: '#00f0ff',
    glowColor: '#0284c7',
    badgeBg: 'rgba(0, 240, 255, 0.22)',
    description: 'Duduk di terminal, mengetik kilat dengan pendar monitor biru neon.',
    icon: '⚡',
    responsibleWorker: 'stark',
  },
  processor_node: {
    label: 'Mengetik Naskah Cepat ⚡',
    action: 'intense_typing',
    color: '#818cf8',
    glowColor: '#6366f1',
    badgeBg: 'rgba(129, 140, 248, 0.22)',
    description: 'Mengolah naskah dwibahasa dan menyempurnakan struktur artikel.',
    icon: '⚡',
    responsibleWorker: 'stark',
  },
  curate_node: {
    label: 'Kurasi Media YouTube 🎬',
    action: 'intense_typing',
    color: '#f43f5e',
    glowColor: '#e11d48',
    badgeBg: 'rgba(244, 63, 94, 0.22)',
    description: 'Usagi memilah rekaman dongeng terbaik dan menganalisis cerita rakyat.',
    icon: '🎬',
    responsibleWorker: 'usagi',
  },
  thumbnail_node: {
    label: 'Mendesain Visual Cover 🎨',
    action: 'drawing_canvas',
    color: '#ec4899',
    glowColor: '#db2777',
    badgeBg: 'rgba(236, 72, 153, 0.22)',
    description: 'Papan gambar kanvas hologram menyala pink terang saat mendesain cover visual.',
    icon: '🎨',
    responsibleWorker: 'stark',
  },
  render_cover_node: {
    label: 'Mendesain Visual Cover 🎨',
    action: 'drawing_canvas',
    color: '#ec4899',
    glowColor: '#db2777',
    badgeBg: 'rgba(236, 72, 153, 0.22)',
    description: 'Merender visual cover dongeng dengan nuansa ilustrasi magis.',
    icon: '🎨',
    responsibleWorker: 'usagi',
  },
  sop_validator_node: {
    label: 'Audit Standar Mutu 🔍',
    action: 'inspecting_sop',
    color: '#facc15',
    glowColor: '#eab308',
    badgeBg: 'rgba(250, 204, 21, 0.22)',
    description: 'Bay-Zero memegang clipboard hologram untuk memvalidasi kelayakan SOP.',
    icon: '🔍',
    responsibleWorker: 'bayzero',
  },
  await_approval: {
    label: 'Menunggu Persetujuan ✋',
    action: 'observing',
    color: '#f59e0b',
    glowColor: '#d97706',
    badgeBg: 'rgba(245, 158, 11, 0.22)',
    description: 'Task checkpoint tertahan menunggu konfirmasi atau otorisasi persetujuan pengguna.',
    icon: '✋',
    responsibleWorker: 'bayzero',
  },
  blocked: {
    label: 'Investigasi Gangguan ⚠️',
    action: 'confused_scratch',
    color: '#ef4444',
    glowColor: '#dc2626',
    badgeBg: 'rgba(239, 68, 68, 0.25)',
    description: 'Eksekusi terhambat atau mengalami kegagalan teknis, membutuhkan intervensi.',
    icon: '⚠️',
    responsibleWorker: 'bayzero',
  },
  offline: {
    label: 'Koneksi Terputus / Offline 🔌',
    action: 'offline_rest',
    color: '#64748b',
    glowColor: '#475569',
    badgeBg: 'rgba(100, 116, 139, 0.22)',
    description: 'Agent sedang dalam status offline atau koneksi stream SSE terputus.',
    icon: '🔌',
    responsibleWorker: 'team',
  },
  publish_node: {
    label: 'Meluncurkan Konten! 🚀',
    action: 'success_celebration',
    color: '#10b981',
    glowColor: '#059669',
    badgeBg: 'rgba(16, 185, 129, 0.25)',
    description: 'Partikel kembang api neon menyala! Konten sukses dipublikasikan ke CMS.',
    icon: '🚀',
    responsibleWorker: 'team',
  },
  post_cms_node: {
    label: 'Meluncurkan Konten! 🚀',
    action: 'success_celebration',
    color: '#10b981',
    glowColor: '#059669',
    badgeBg: 'rgba(16, 185, 129, 0.25)',
    description: 'Dongeng berhasil diunggah ke CMS Bogorstore.',
    icon: '🚀',
    responsibleWorker: 'usagi',
  },
  complete_node: {
    label: 'Misi Selesai Gemilang ✨',
    action: 'success_celebration',
    color: '#34d399',
    glowColor: '#10b981',
    badgeBg: 'rgba(52, 211, 153, 0.25)',
    description: 'Seluruh alur kerja tuntas diselesaikan dengan standar mutu prima.',
    icon: '✨',
    responsibleWorker: 'team',
  },
  failed_node: {
    label: 'Investigasi Gangguan ⚠️',
    action: 'confused_scratch',
    color: '#ef4444',
    glowColor: '#dc2626',
    badgeBg: 'rgba(239, 68, 68, 0.25)',
    description: 'Layar glitch merah berkedip, tim menyelidiki anomali eksekusi.',
    icon: '⚠️',
    responsibleWorker: 'bayzero',
  },
  housekeeping: {
    label: 'Pembersihan Sistem 🧹',
    action: 'observing',
    color: '#06b6d4',
    glowColor: '#0891b2',
    badgeBg: 'rgba(6, 182, 212, 0.25)',
    description: 'Janitor Bot aktif menyapu sisa checkpoint & memangkas data database.',
    icon: '🧹',
    responsibleWorker: 'team',
  },
  housekeeping_node: {
    label: 'Pembersihan Sistem 🧹',
    action: 'observing',
    color: '#06b6d4',
    glowColor: '#0891b2',
    badgeBg: 'rgba(6, 182, 212, 0.25)',
    description: 'Janitor Bot aktif menyapu sisa checkpoint & memangkas data database.',
    icon: '🧹',
    responsibleWorker: 'team',
  },
};

/**
 * Mendapatkan konfigurasi ramah manusia untuk suatu nama node.
 */
export function getHumanStatus(node: string, defaultAction?: string): HumanStatusConfig {
  if (STATUS_LABELS[node]) {
    return STATUS_LABELS[node];
  }

  // Fallback berdasarkan kemiripan nama
  const lower = node.toLowerCase();
  if (lower.includes('idle') || lower.includes('coffee')) return STATUS_LABELS['IDLE'];
  if (lower.includes('ingest') || lower.includes('start')) return STATUS_LABELS['ingest_node'];
  if (lower.includes('scrape') || lower.includes('search') || lower.includes('fetch')) return STATUS_LABELS['scrape_node'];
  if (lower.includes('curate') || lower.includes('youtube')) return STATUS_LABELS['curate_node'];
  if (lower.includes('draft') || lower.includes('write') || lower.includes('processor')) return STATUS_LABELS['draft_node'];
  if (lower.includes('thumbnail') || lower.includes('image') || lower.includes('cover')) return STATUS_LABELS['thumbnail_node'];
  if (lower.includes('sop') || lower.includes('validate') || lower.includes('check')) return STATUS_LABELS['sop_validator_node'];
  if (lower.includes('publish') || lower.includes('post') || lower.includes('done') || lower.includes('complete')) return STATUS_LABELS['publish_node'];
  if (lower.includes('housekeep') || lower.includes('clean') || lower.includes('janitor')) return STATUS_LABELS['housekeeping'];
  if (lower.includes('fail') || lower.includes('error')) return STATUS_LABELS['failed_node'];

  return {
    label: node,
    action: 'intense_typing',
    color: '#38bdf8',
    glowColor: '#0284c7',
    badgeBg: 'rgba(56, 189, 248, 0.2)',
    description: `Sedang memproses node ${node}`,
    icon: '⚡',
    responsibleWorker: 'stark',
  };
}

