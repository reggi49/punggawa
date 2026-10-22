import React, { useState, useEffect } from 'react';
import {
  Briefcase,
  X,
  ExternalLink,
  Copy,
  Check,
  Star,
  Search,
  Building,
  MapPin,
  DollarSign,
  ShieldCheck,
  AlertTriangle,
  FileText,
  UserCheck,
  Sparkles,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';

export interface JobOpportunity {
  id: string;
  job_url: string;
  company_name: string;
  role_title: string;
  location: string | null;
  work_mode: string | null;
  salary_range: string | null;
  fit_score: number;
  fit_reasoning: string;
  is_active: boolean;
  status: string;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobDetail extends JobOpportunity {
  job_description: string;
  evaluation_report: {
    A_role_summary?: string;
    B_fit_score?: number;
    C_skills_match?: {
      matching_skills?: string[];
      missing_skills?: string[];
    };
    D_seniority_level?: string;
    E_compensation_review?: string;
    F_red_flags?: string;
    G_legitimacy_block?: string;
    H_pitch_points?: string[];
  };
  tailored_cover_letter: string | null;
  tailored_cv_points: string[] | null;
  interview_star_prep: Array<{
    question: string;
    competency_tested?: string;
    situation: string;
    task: string;
    action: string;
    result: string;
    reflection: string;
  }> | null;
}

interface CareerOpsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenDispatch: () => void;
}

export const CareerOpsModal: React.FC<CareerOpsModalProps> = ({
  isOpen,
  onClose,
  onOpenDispatch,
}) => {
  const [jobs, setJobs] = useState<JobOpportunity[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [jobDetail, setJobDetail] = useState<JobDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'cover_letter' | 'report' | 'star_prep'>('cover_letter');

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/jobs');
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs || []);
        if (data.jobs && data.jobs.length > 0 && !selectedJobId) {
          setSelectedJobId(data.jobs[0].id);
        }
      }
    } catch (err) {
      console.error('Gagal mengambil daftar loker:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchJobDetail = async (id: string) => {
    setDetailLoading(true);
    try {
      const res = await fetch(`/api/jobs/${id}`);
      if (res.ok) {
        const data = await res.json();
        setJobDetail(data);
      }
    } catch (err) {
      console.error(`Gagal mengambil detail loker ${id}:`, err);
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchJobs();
    }
  }, [isOpen]);

  useEffect(() => {
    if (selectedJobId) {
      fetchJobDetail(selectedJobId);
    }
  }, [selectedJobId]);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2500);
  };

  const handleUpdateStatus = async (id: string, newStatus: string) => {
    try {
      const res = await fetch(`/api/jobs/${id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        fetchJobs();
        if (jobDetail && jobDetail.id === id) {
          setJobDetail({ ...jobDetail, status: newStatus });
        }
      }
    } catch (err) {
      console.error('Gagal mengubah status lowongan:', err);
    }
  };

  if (!isOpen) return null;

  const filteredJobs = jobs.filter((j) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'high_fit') return j.fit_score >= 4;
    return j.status === statusFilter;
  });

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: 'rgba(23, 26, 31, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '1180px',
          height: '88vh',
          background: '#FAF8F5',
          borderRadius: '20px',
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.45)',
          border: '1px solid rgba(212, 163, 115, 0.35)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          fontFamily: "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif",
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '16px 24px',
            background: 'linear-gradient(135deg, #2D3748, #354A60)',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '10px',
                background: 'rgba(212, 163, 115, 0.25)',
                border: '1px solid #D4A373',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Briefcase size={20} color="#F59E0B" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ margin: 0, fontSize: '17px', fontWeight: 800, letterSpacing: '0.01em' }}>
                  Punggawa Career-Ops Command Center
                </h2>
                <span
                  style={{
                    background: 'rgba(212, 163, 115, 0.3)',
                    color: '#FDE68A',
                    fontSize: '11px',
                    fontWeight: 800,
                    padding: '2px 8px',
                    borderRadius: '6px',
                    border: '1px solid rgba(245, 158, 11, 0.4)',
                  }}
                >
                  Agent: Clara
                </span>
              </div>
              <p style={{ margin: '2px 0 0 0', fontSize: '12px', color: '#CBD5E1' }}>
                Matriks Evaluasi A–H • Fit Scoring (1–5) • Drafter-Reviewer Cover Letter • STAR+R Prep
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={() => {
                onClose();
                onOpenDispatch();
              }}
              style={{
                background: '#D4A373',
                color: '#1E293B',
                border: 'none',
                borderRadius: '10px',
                padding: '7px 14px',
                fontSize: '12px',
                fontWeight: 800,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <Sparkles size={14} />
              <span>Analisis Loker Baru</span>
            </button>

            <button
              onClick={fetchJobs}
              title="Refresh Daftar"
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '8px',
                padding: '7px',
                color: '#FFFFFF',
                cursor: 'pointer',
              }}
            >
              <RefreshCw size={15} />
            </button>

            <button
              onClick={onClose}
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                border: 'none',
                borderRadius: '8px',
                padding: '6px',
                color: '#FFFFFF',
                cursor: 'pointer',
              }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Body: Split View (List 35% | Detail 65%) */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left Column: Job List */}
          <div
            style={{
              width: '360px',
              borderRight: '1px solid rgba(48, 52, 58, 0.12)',
              display: 'flex',
              flexDirection: 'column',
              background: '#F4F1EA',
            }}
          >
            {/* Filter Bar */}
            <div
              style={{
                padding: '12px 14px',
                borderBottom: '1px solid rgba(48, 52, 58, 0.1)',
                display: 'flex',
                gap: '6px',
                overflowX: 'auto',
              }}
            >
              {[
                { id: 'all', label: 'Semua' },
                { id: 'high_fit', label: '⭐ Skor >= 4' },
                { id: 'shortlisted', label: 'Shortlist' },
                { id: 'applied', label: 'Dilamar' },
              ].map((f) => (
                <button
                  key={f.id}
                  onClick={() => setStatusFilter(f.id)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    border: statusFilter === f.id ? '1px solid #354A60' : '1px solid rgba(48, 52, 58, 0.15)',
                    background: statusFilter === f.id ? '#354A60' : 'rgba(255, 255, 255, 0.7)',
                    color: statusFilter === f.id ? '#FFFFFF' : '#30343A',
                    fontSize: '11px',
                    fontWeight: statusFilter === f.id ? 700 : 500,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* List Container */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
              {loading && jobs.length === 0 ? (
                <div style={{ padding: '30px', textAlign: 'center', color: '#64748B', fontSize: '13px' }}>
                  Memuat data lowongan...
                </div>
              ) : filteredJobs.length === 0 ? (
                <div style={{ padding: '40px 20px', textAlign: 'center' }}>
                  <Briefcase size={36} color="#94A3B8" style={{ margin: '0 auto 10px' }} />
                  <p style={{ fontSize: '13px', fontWeight: 700, color: '#334155', margin: 0 }}>
                    Belum ada lowongan terdaftar
                  </p>
                  <p style={{ fontSize: '12px', color: '#64748B', margin: '4px 0 14px' }}>
                    Kirim link loker pertama Anda ke Clara untuk dievaluasi.
                  </p>
                  <button
                    onClick={() => {
                      onClose();
                      onOpenDispatch();
                    }}
                    style={{
                      background: '#354A60',
                      color: '#FFF',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '6px 14px',
                      fontSize: '11.5px',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    + Tambah Loker
                  </button>
                </div>
              ) : (
                filteredJobs.map((j) => {
                  const isSelected = selectedJobId === j.id;
                  const isHighFit = j.fit_score >= 4;

                  return (
                    <div
                      key={j.id}
                      onClick={() => setSelectedJobId(j.id)}
                      style={{
                        padding: '12px',
                        marginBottom: '8px',
                        borderRadius: '12px',
                        background: isSelected ? 'rgba(53, 74, 96, 0.1)' : '#FFFFFF',
                        border: isSelected ? '1.5px solid #354A60' : '1px solid rgba(48, 52, 58, 0.1)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>
                          {j.company_name}
                        </span>
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '3px',
                            background: isHighFit ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                            color: isHighFit ? '#059669' : '#D97706',
                            padding: '2px 6px',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: 800,
                          }}
                        >
                          <Star size={11} fill={isHighFit ? '#059669' : '#D97706'} />
                          <span>{j.fit_score}/5</span>
                        </div>
                      </div>

                      <div style={{ fontSize: '13px', fontWeight: 800, color: '#1E293B', marginBottom: '6px', lineHeight: 1.3 }}>
                        {j.role_title}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: '#64748B' }}>
                        <span>🌐 {j.work_mode || 'Remote'}</span>
                        {j.salary_range && j.salary_range !== 'Tidak Disebutkan' && (
                          <span>💵 {j.salary_range}</span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Column: In-Depth Job Details */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#FFFFFF', overflow: 'hidden' }}>
            {detailLoading ? (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748B' }}>
                Memuat detail evaluasi & draf lamaran...
              </div>
            ) : !jobDetail ? (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8' }}>
                Pilih lowongan di sebelah kiri untuk melihat hasil kurasi Career-Ops.
              </div>
            ) : (
              <>
                {/* Header Lowongan */}
                <div style={{ padding: '18px 24px', borderBottom: '1px solid rgba(48, 52, 58, 0.1)' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span style={{ fontSize: '13px', fontWeight: 700, color: '#64748B' }}>
                          {jobDetail.company_name}
                        </span>
                        {jobDetail.location && (
                          <span style={{ fontSize: '12px', color: '#94A3B8' }}>• {jobDetail.location}</span>
                        )}
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '1px 8px',
                            borderRadius: '12px',
                            background: jobDetail.is_active ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                            color: jobDetail.is_active ? '#059669' : '#DC2626',
                          }}
                        >
                          {jobDetail.is_active ? '✓ Loker Aktif (Block G)' : '⚠️ Terdeteksi Kadaluarsa'}
                        </span>
                      </div>
                      <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 800, color: '#1E293B' }}>
                        {jobDetail.role_title}
                      </h1>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <select
                        value={jobDetail.status}
                        onChange={(e) => handleUpdateStatus(jobDetail.id, e.target.value)}
                        style={{
                          padding: '6px 10px',
                          borderRadius: '8px',
                          border: '1px solid rgba(48, 52, 58, 0.2)',
                          fontSize: '12px',
                          fontWeight: 700,
                          color: '#30343A',
                          background: '#FAF8F5',
                          cursor: 'pointer',
                        }}
                      >
                        <option value="evaluated">Status: Dievaluasi</option>
                        <option value="shortlisted">Status: Shortlist ⭐</option>
                        <option value="applied">Status: Sudah Dilamar 🚀</option>
                        <option value="interviewing">Status: Wawancara 🎙️</option>
                        <option value="archived">Status: Arsip 📁</option>
                      </select>

                      <a
                        href={jobDetail.job_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '6px 12px',
                          borderRadius: '8px',
                          background: '#354A60',
                          color: '#FFFFFF',
                          fontSize: '12px',
                          fontWeight: 700,
                          textDecoration: 'none',
                        }}
                      >
                        <span>Buka Loker</span>
                        <ExternalLink size={13} />
                      </a>
                    </div>
                  </div>

                  {/* Fit Score Banner */}
                  <div
                    style={{
                      marginTop: '14px',
                      padding: '10px 14px',
                      borderRadius: '10px',
                      background: jobDetail.fit_score >= 4 ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.08)',
                      border: `1px solid ${jobDetail.fit_score >= 4 ? 'rgba(16, 185, 129, 0.25)' : 'rgba(245, 158, 11, 0.25)'}`,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                    }}
                  >
                    <div
                      style={{
                        padding: '4px 8px',
                        borderRadius: '6px',
                        background: jobDetail.fit_score >= 4 ? '#10B981' : '#F59E0B',
                        color: '#FFF',
                        fontSize: '13px',
                        fontWeight: 900,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      FIT SCORE: {jobDetail.fit_score}/5
                    </div>
                    <div style={{ fontSize: '12.5px', color: '#334155', lineHeight: 1.4 }}>
                      <strong>Alasan Kecocokan:</strong> {jobDetail.fit_reasoning}
                    </div>
                  </div>
                </div>

                {/* Sub-Navigation Tabs */}
                <div
                  style={{
                    display: 'flex',
                    borderBottom: '1px solid rgba(48, 52, 58, 0.1)',
                    padding: '0 24px',
                    background: '#FAF8F5',
                  }}
                >
                  {[
                    { id: 'cover_letter', label: '✍️ Tailored Cover Letter & CV' },
                    { id: 'report', label: '📊 Matriks Evaluasi A–H' },
                    { id: 'star_prep', label: '🎯 STAR+R Interview Prep' },
                  ].map((tab) => {
                    const active = activeTab === tab.id;
                    return (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as any)}
                        style={{
                          padding: '12px 16px',
                          border: 'none',
                          borderBottom: active ? '2.5px solid #354A60' : '2.5px solid transparent',
                          background: 'none',
                          color: active ? '#1E293B' : '#64748B',
                          fontSize: '13px',
                          fontWeight: active ? 800 : 600,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        {tab.label}
                      </button>
                    );
                  })}
                </div>

                {/* Tab Content Area */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
                  {/* TAB 1: COVER LETTER & CV BULLET POINTS */}
                  {activeTab === 'cover_letter' && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                        <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 800, color: '#1E293B' }}>
                          Tailored Cover Letter (Diaudit oleh Reviewer Agent)
                        </h3>
                        {jobDetail.tailored_cover_letter && (
                          <button
                            onClick={() => handleCopy(jobDetail.tailored_cover_letter!, 'cl')}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '5px',
                              padding: '5px 10px',
                              borderRadius: '6px',
                              border: '1px solid rgba(48, 52, 58, 0.2)',
                              background: '#FFF',
                              fontSize: '11.5px',
                              fontWeight: 700,
                              color: '#334155',
                              cursor: 'pointer',
                            }}
                          >
                            {copiedKey === 'cl' ? <Check size={13} color="#10B981" /> : <Copy size={13} />}
                            <span>{copiedKey === 'cl' ? 'Tersalin!' : 'Salin Cover Letter'}</span>
                          </button>
                        )}
                      </div>

                      {jobDetail.tailored_cover_letter ? (
                        <div
                          style={{
                            padding: '16px',
                            borderRadius: '12px',
                            background: '#F8FAFC',
                            border: '1px solid #E2E8F0',
                            whiteSpace: 'pre-wrap',
                            fontSize: '13px',
                            lineHeight: 1.6,
                            color: '#1E293B',
                            marginBottom: '20px',
                          }}
                        >
                          {jobDetail.tailored_cover_letter}
                        </div>
                      ) : (
                        <div style={{ padding: '20px', color: '#94A3B8', fontSize: '13px' }}>
                          Cover letter tidak dihasilkan karena skor kecocokan di bawah batas minimum (3/5).
                        </div>
                      )}

                      {/* Tailored CV Points */}
                      {jobDetail.tailored_cv_points && jobDetail.tailored_cv_points.length > 0 && (
                        <div>
                          <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', fontWeight: 800, color: '#1E293B' }}>
                            Poin Pencapaian CV yang Disesuaikan (Impact-Driven):
                          </h3>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {jobDetail.tailored_cv_points.map((pt, idx) => (
                              <div
                                key={idx}
                                style={{
                                  padding: '10px 14px',
                                  borderRadius: '8px',
                                  background: 'rgba(53, 74, 96, 0.05)',
                                  border: '1px solid rgba(53, 74, 96, 0.12)',
                                  fontSize: '12.5px',
                                  color: '#1E293B',
                                  lineHeight: 1.4,
                                }}
                              >
                                🎯 {pt}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 2: MATRIKS EVALUASI A-H */}
                  {activeTab === 'report' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      {/* Summary & Mission */}
                      <div style={{ padding: '14px', borderRadius: '10px', background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                        <div style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', marginBottom: '4px' }}>
                          A - ROLE SUMMARY & CORE MISSION
                        </div>
                        <div style={{ fontSize: '13px', color: '#1E293B', lineHeight: 1.5 }}>
                          {jobDetail.evaluation_report?.A_role_summary || 'Tidak ada data'}
                        </div>
                      </div>

                      {/* Skills Matching */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <div style={{ padding: '14px', borderRadius: '10px', background: 'rgba(16, 185, 129, 0.06)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                          <div style={{ fontSize: '11px', fontWeight: 800, color: '#059669', marginBottom: '6px' }}>
                            ✓ KEAHLIAN YANG COCOK (MATCHING SKILLS)
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {(jobDetail.evaluation_report?.C_skills_match?.matching_skills || []).map((s, i) => (
                              <span key={i} style={{ background: '#10B981', color: '#FFF', fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '4px' }}>
                                {s}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div style={{ padding: '14px', borderRadius: '10px', background: 'rgba(239, 68, 68, 0.06)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                          <div style={{ fontSize: '11px', fontWeight: 800, color: '#DC2626', marginBottom: '6px' }}>
                            ⚠️ SKILL GAP (PERLU DIPELAJARI / DIANTISIPASI)
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {(jobDetail.evaluation_report?.C_skills_match?.missing_skills || []).map((s, i) => (
                              <span key={i} style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#DC2626', fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '4px' }}>
                                {s}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Compensation & Red Flags */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <div style={{ padding: '14px', borderRadius: '10px', background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                          <div style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', marginBottom: '4px' }}>
                            E - COMPENSATION & LEVEL REVIEW
                          </div>
                          <div style={{ fontSize: '12.5px', color: '#334155' }}>
                            {jobDetail.evaluation_report?.E_compensation_review || 'Standar industri'}
                          </div>
                        </div>

                        <div style={{ padding: '14px', borderRadius: '10px', background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                          <div style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', marginBottom: '4px' }}>
                            F - RED FLAGS & KULTUR PERUSAHAAN
                          </div>
                          <div style={{ fontSize: '12.5px', color: '#334155' }}>
                            {jobDetail.evaluation_report?.F_red_flags || 'Tidak ada red flag terdeteksi.'}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 3: STAR+R INTERVIEW PREP */}
                  {activeTab === 'star_prep' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      {jobDetail.interview_star_prep && jobDetail.interview_star_prep.length > 0 ? (
                        jobDetail.interview_star_prep.map((prep, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: '16px',
                              borderRadius: '12px',
                              background: '#F8FAFC',
                              border: '1px solid #E2E8F0',
                            }}
                          >
                            <div style={{ fontSize: '14px', fontWeight: 800, color: '#1E293B', marginBottom: '8px' }}>
                              Q{idx + 1}: {prep.question}
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px', marginBottom: '6px' }}>
                              <div style={{ background: '#FFF', padding: '8px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                                <strong>Situation:</strong> {prep.situation}
                              </div>
                              <div style={{ background: '#FFF', padding: '8px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                                <strong>Task:</strong> {prep.task}
                              </div>
                            </div>
                            <div style={{ background: '#FFF', padding: '8px', borderRadius: '6px', border: '1px solid #E2E8F0', fontSize: '12px', marginBottom: '6px' }}>
                              <strong>Action:</strong> {prep.action}
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
                              <div style={{ background: 'rgba(16, 185, 129, 0.08)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                                <strong>Result:</strong> {prep.result}
                              </div>
                              <div style={{ background: 'rgba(53, 74, 96, 0.08)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(53, 74, 96, 0.2)' }}>
                                <strong>Reflection:</strong> {prep.reflection}
                              </div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div style={{ padding: '20px', color: '#94A3B8', fontSize: '13px' }}>
                          Materi latihan STAR+R otomatis dibuat untuk lowongan dengan Fit Score minimal 4/5.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
