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
  Clock,
  Layers,
  Award,
  Send,
  Mail,
  Sliders,
  TrendingUp,
} from 'lucide-react';

export interface JobOpportunity {
  id: string;
  job_url: string;
  company_name: string;
  role_title: string;
  location: string | null;
  work_mode: string | null;
  salary_range: string | null;
  ats_vendor: string | null;
  fit_score: number;
  job_quality_score: number;
  fit_reasoning: string;
  is_active: boolean;
  status: string;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SkillGapItem {
  skill: string;
  status: 'matched' | 'missing';
  importance?: 'high' | 'medium' | 'low';
  estimated_learning?: string;
}

export interface JobDetail extends JobOpportunity {
  job_description: string;
  ats_vendor: string;
  job_quality_score: number;
  quality_breakdown: {
    company_maturity?: string;
    stability_rating?: string;
    culture_summary?: string;
  };
  skill_gap_analysis: SkillGapItem[];
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
  interview_pack: {
    company_research?: string;
    tech_stack_breakdown?: string[];
    salary_negotiation_notes?: string;
    likely_questions?: string[];
    star_scenarios?: Array<{
      question: string;
      competency_tested?: string;
      situation: string;
      task: string;
      action: string;
      result: string;
      reflection: string;
    }>;
  } | null;
  follow_up_draft: string | null;
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
  const [activeTab, setActiveTab] = useState<'cover_letter' | 'skill_gap' | 'interview_pack' | 'follow_up' | 'report'>('cover_letter');

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
          maxWidth: '1240px',
          height: '90vh',
          background: '#FAF8F5',
          borderRadius: '20px',
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.45)',
          border: '1px solid rgba(13, 148, 136, 0.35)',
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
            background: 'linear-gradient(135deg, #111827, #134E4A)',
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
                background: 'rgba(13, 148, 136, 0.25)',
                border: '1px solid #14B8A6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Briefcase size={20} color="#2DD4BF" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ margin: 0, fontSize: '17px', fontWeight: 800, letterSpacing: '0.01em' }}>
                  Scout • Career Intelligence Command Center
                </h2>
                <span
                  style={{
                    background: 'rgba(20, 184, 166, 0.2)',
                    color: '#5EEAD4',
                    fontSize: '11px',
                    fontWeight: 800,
                    padding: '2px 8px',
                    borderRadius: '6px',
                    border: '1px solid rgba(45, 212, 191, 0.4)',
                  }}
                >
                  Agent: Scout
                </span>
              </div>
              <p style={{ margin: '2px 0 0 0', fontSize: '12px', color: '#CBD5E1' }}>
                Dual Scoring (Fit & Quality) • ATS Intelligence • Skill Gap Heatmap • Full Interview Pack & Follow-Up
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
                background: '#0D9488',
                color: '#FFFFFF',
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

        {/* Modal Body: Split View (List 33% | Detail 67%) */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left Column: Job List */}
          <div
            style={{
              width: '380px',
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
                { id: 'high_fit', label: '⭐ Fit >= 4' },
                { id: 'shortlisted', label: 'Shortlist' },
                { id: 'submitted', label: 'Dilamar' },
                { id: 'interview_technical', label: 'Interview' },
              ].map((f) => (
                <button
                  key={f.id}
                  onClick={() => setStatusFilter(f.id)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    border: statusFilter === f.id ? '1px solid #0D9488' : '1px solid rgba(48, 52, 58, 0.15)',
                    background: statusFilter === f.id ? '#0D9488' : 'rgba(255, 255, 255, 0.7)',
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
                    Kirim link lowongan kerja pertama ke Scout untuk dianalisis.
                  </p>
                  <button
                    onClick={() => {
                      onClose();
                      onOpenDispatch();
                    }}
                    style={{
                      background: '#0D9488',
                      color: '#FFF',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '6px 14px',
                      fontSize: '11.5px',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    + Analisis Loker
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
                        background: isSelected ? 'rgba(13, 148, 136, 0.1)' : '#FFFFFF',
                        border: isSelected ? '1.5px solid #0D9488' : '1px solid rgba(48, 52, 58, 0.1)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>
                          {j.company_name}
                        </span>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          {/* ATS Badge */}
                          <span
                            style={{
                              background: '#F1F5F9',
                              color: '#475569',
                              padding: '1px 5px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 700,
                            }}
                          >
                            {j.ats_vendor || 'ATS'}
                          </span>
                          {/* Fit Score Badge */}
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '2px',
                              background: isHighFit ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                              color: isHighFit ? '#059669' : '#D97706',
                              padding: '1px 6px',
                              borderRadius: '4px',
                              fontSize: '10.5px',
                              fontWeight: 800,
                            }}
                          >
                            <Star size={10} fill={isHighFit ? '#059669' : '#D97706'} />
                            <span>{j.fit_score}/5</span>
                          </div>
                        </div>
                      </div>

                      <div style={{ fontSize: '13px', fontWeight: 800, color: '#1E293B', marginBottom: '6px', lineHeight: 1.3 }}>
                        {j.role_title}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: '#64748B' }}>
                        <span>🌐 {j.work_mode || 'Remote'}</span>
                        <span style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#2563EB', padding: '1px 6px', borderRadius: '4px', fontWeight: 700 }}>
                          {j.status}
                        </span>
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
                Memuat intelligence loker & interview pack...
              </div>
            ) : !jobDetail ? (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8' }}>
                Pilih lowongan di sebelah kiri untuk melihat evaluasi Career Intelligence Scout.
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
                        {/* ATS Tag */}
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 800,
                            padding: '2px 8px',
                            borderRadius: '6px',
                            background: '#E0F2FE',
                            color: '#0284C7',
                          }}
                        >
                          ATS: {jobDetail.ats_vendor || 'Direct'}
                        </span>
                        {/* Active Tag */}
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '6px',
                            background: jobDetail.is_active ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                            color: jobDetail.is_active ? '#059669' : '#DC2626',
                          }}
                        >
                          {jobDetail.is_active ? '✓ Loker Aktif (Block G)' : '⚠️ Kadaluarsa'}
                        </span>
                      </div>
                      <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 800, color: '#1E293B' }}>
                        {jobDetail.role_title}
                      </h1>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {/* Granular Application Lifecycle Status Dropdown */}
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
                        <option value="evaluated">Status: Evaluated 📋</option>
                        <option value="shortlisted">Status: Shortlisted ⭐</option>
                        <option value="tailored">Status: Tailored ✍️</option>
                        <option value="ready_to_apply">Status: Ready to Apply 🚀</option>
                        <option value="submitted">Status: Submitted / Dilamar 📨</option>
                        <option value="assessment">Status: Assessment / Test 💻</option>
                        <option value="interview_hr">Status: HR Interview 🎙️</option>
                        <option value="interview_technical">Status: Technical Interview 🧠</option>
                        <option value="offer">Status: Offer Received 🎉</option>
                        <option value="accepted">Status: Accepted / Hired 🏆</option>
                        <option value="rejected">Status: Rejected ❌</option>
                        <option value="ghosted">Status: Ghosted (No Reply) 👻</option>
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
                          background: '#0D9488',
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

                  {/* Dual Scoring Banner (Fit Score vs Job Quality Score) */}
                  <div
                    style={{
                      marginTop: '14px',
                      display: 'grid',
                      gridTemplateColumns: 'auto auto 1fr',
                      gap: '12px',
                      alignItems: 'center',
                    }}
                  >
                    {/* Fit Score */}
                    <div
                      style={{
                        padding: '6px 12px',
                        borderRadius: '8px',
                        background: jobDetail.fit_score >= 4 ? '#10B981' : '#F59E0B',
                        color: '#FFF',
                        fontSize: '12px',
                        fontWeight: 900,
                      }}
                    >
                      FIT SCORE: {jobDetail.fit_score}/5
                    </div>

                    {/* Job Quality Score */}
                    <div
                      style={{
                        padding: '6px 12px',
                        borderRadius: '8px',
                        background: (jobDetail.job_quality_score || 3) >= 4 ? '#0D9488' : '#64748B',
                        color: '#FFF',
                        fontSize: '12px',
                        fontWeight: 900,
                      }}
                    >
                      JOB QUALITY: {jobDetail.job_quality_score || 3}/5
                    </div>

                    <div style={{ fontSize: '12px', color: '#475569', lineHeight: 1.4 }}>
                      <strong>Analisis Scout:</strong> {jobDetail.fit_reasoning}
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
                    overflowX: 'auto',
                  }}
                >
                  {[
                    { id: 'cover_letter', label: '✍️ Tailored Cover Letter & CV' },
                    { id: 'skill_gap', label: '🔥 Skill Gap Heatmap' },
                    { id: 'interview_pack', label: '🎯 Interview Pack & Gaji' },
                    { id: 'follow_up', label: '📨 Follow-Up Email' },
                    { id: 'report', label: '📊 Laporan Matriks A–H' },
                  ].map((tab) => {
                    const active = activeTab === tab.id;
                    return (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as any)}
                        style={{
                          padding: '12px 16px',
                          border: 'none',
                          borderBottom: active ? '2.5px solid #0D9488' : '2.5px solid transparent',
                          background: 'none',
                          color: active ? '#0F766E' : '#64748B',
                          fontSize: '12.5px',
                          fontWeight: active ? 800 : 600,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                          whiteSpace: 'nowrap',
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
                                  background: 'rgba(13, 148, 136, 0.05)',
                                  border: '1px solid rgba(13, 148, 136, 0.15)',
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

                  {/* TAB 2: SKILL GAP HEATMAP WITH ESTIMATED LEARNING TIME */}
                  {activeTab === 'skill_gap' && (
                    <div>
                      <div style={{ marginBottom: '14px' }}>
                        <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 800, color: '#1E293B' }}>
                          Skill Gap Heatmap & Actionable Learning Roadmap
                        </h3>
                        <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#64748B' }}>
                          Analisis keselarasan skill dan estimasi waktu yang dibutuhkan untuk menutup kekurangan teknis.
                        </p>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {jobDetail.skill_gap_analysis && jobDetail.skill_gap_analysis.length > 0 ? (
                          jobDetail.skill_gap_analysis.map((item, idx) => {
                            const isMatch = item.status === 'matched';
                            return (
                              <div
                                key={idx}
                                style={{
                                  padding: '12px 16px',
                                  borderRadius: '10px',
                                  background: isMatch ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)',
                                  border: `1px solid ${isMatch ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`,
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span style={{ fontSize: '16px' }}>{isMatch ? '✅' : '❌'}</span>
                                  <div>
                                    <div style={{ fontSize: '13px', fontWeight: 800, color: '#1E293B' }}>
                                      {item.skill}
                                    </div>
                                    <div style={{ fontSize: '11px', color: '#64748B' }}>
                                      Prioritas: {item.importance || 'Medium'}
                                    </div>
                                  </div>
                                </div>

                                <div>
                                  {isMatch ? (
                                    <span style={{ background: '#10B981', color: '#FFF', fontSize: '11px', fontWeight: 700, padding: '3px 8px', borderRadius: '6px' }}>
                                      Dikuasai di CV
                                    </span>
                                  ) : (
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <Clock size={12} color="#DC2626" />
                                      <span style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#DC2626', fontSize: '11px', fontWeight: 800, padding: '3px 8px', borderRadius: '6px' }}>
                                        Est. Belajar: {item.estimated_learning || '2 minggu'}
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            );
                          })
                        ) : (
                          <div style={{ padding: '20px', color: '#64748B' }}>
                            Data skill gap tidak tersedia.
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* TAB 3: COMPREHENSIVE INTERVIEW PACK */}
                  {activeTab === 'interview_pack' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                      {/* Company Research */}
                      {jobDetail.interview_pack?.company_research && (
                        <div style={{ padding: '16px', borderRadius: '12px', background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                          <h4 style={{ margin: '0 0 6px', fontSize: '13px', fontWeight: 800, color: '#0F766E' }}>
                            🏢 RISIK & PRODUK PERUSAHAAN (COMPANY DEEP DIVE)
                          </h4>
                          <div style={{ fontSize: '13px', color: '#1E293B', lineHeight: 1.5 }}>
                            {jobDetail.interview_pack.company_research}
                          </div>
                        </div>
                      )}

                      {/* Salary Negotiation Strategy */}
                      {jobDetail.interview_pack?.salary_negotiation_notes && (
                        <div style={{ padding: '16px', borderRadius: '12px', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)' }}>
                          <h4 style={{ margin: '0 0 6px', fontSize: '13px', fontWeight: 800, color: '#D97706' }}>
                            💵 STRATEGI & TAKTIK NEGOSIASI GAJI
                          </h4>
                          <div style={{ fontSize: '12.5px', color: '#1E293B', lineHeight: 1.5 }}>
                            {jobDetail.interview_pack.salary_negotiation_notes}
                          </div>
                        </div>
                      )}

                      {/* Likely Questions */}
                      {jobDetail.interview_pack?.likely_questions && jobDetail.interview_pack.likely_questions.length > 0 && (
                        <div>
                          <h4 style={{ margin: '0 0 8px', fontSize: '13px', fontWeight: 800, color: '#1E293B' }}>
                            🎯 PREDIKSI PERTANYAAN TEKNIS & KULTURAL:
                          </h4>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {jobDetail.interview_pack.likely_questions.map((q, i) => (
                              <div key={i} style={{ padding: '10px 14px', borderRadius: '8px', background: '#F1F5F9', fontSize: '12.5px', color: '#1E293B' }}>
                                <strong>Q{i + 1}:</strong> {q}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* STAR+R Scenarios */}
                      {jobDetail.interview_pack?.star_scenarios && jobDetail.interview_pack.star_scenarios.length > 0 && (
                        <div>
                          <h4 style={{ margin: '0 0 8px', fontSize: '13px', fontWeight: 800, color: '#1E293B' }}>
                            🌟 SKENARIO JAWABAN STAR+R:
                          </h4>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {jobDetail.interview_pack.star_scenarios.map((prep, idx) => (
                              <div key={idx} style={{ padding: '14px', borderRadius: '10px', background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                                <div style={{ fontSize: '13px', fontWeight: 800, color: '#0F766E', marginBottom: '6px' }}>
                                  {prep.question}
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '11.5px', marginBottom: '6px' }}>
                                  <div style={{ background: '#FFF', padding: '6px', borderRadius: '4px', border: '1px solid #E2E8F0' }}>
                                    <strong>Situation:</strong> {prep.situation}
                                  </div>
                                  <div style={{ background: '#FFF', padding: '6px', borderRadius: '4px', border: '1px solid #E2E8F0' }}>
                                    <strong>Task:</strong> {prep.task}
                                  </div>
                                </div>
                                <div style={{ background: '#FFF', padding: '6px', borderRadius: '4px', border: '1px solid #E2E8F0', fontSize: '11.5px', marginBottom: '6px' }}>
                                  <strong>Action:</strong> {prep.action}
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '11.5px' }}>
                                  <div style={{ background: 'rgba(16, 185, 129, 0.08)', padding: '6px', borderRadius: '4px' }}>
                                    <strong>Result:</strong> {prep.result}
                                  </div>
                                  <div style={{ background: 'rgba(13, 148, 136, 0.08)', padding: '6px', borderRadius: '4px' }}>
                                    <strong>Reflection:</strong> {prep.reflection}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 4: AUTOMATED FOLLOW-UP EMAIL */}
                  {activeTab === 'follow_up' && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                        <div>
                          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 800, color: '#1E293B' }}>
                            Draf Email Follow-Up Otomatis (Jika 7–14 Hari Tanpa Respon)
                          </h3>
                          <p style={{ margin: '2px 0 0', fontSize: '11.5px', color: '#64748B' }}>
                            Kirim ke HR/Hiring Manager untuk menanyakan kelanjutan proses aplikasi secara profesional.
                          </p>
                        </div>
                        {jobDetail.follow_up_draft && (
                          <button
                            onClick={() => handleCopy(jobDetail.follow_up_draft!, 'fu')}
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
                            {copiedKey === 'fu' ? <Check size={13} color="#10B981" /> : <Copy size={13} />}
                            <span>{copiedKey === 'fu' ? 'Tersalin!' : 'Salin Follow-Up'}</span>
                          </button>
                        )}
                      </div>

                      {jobDetail.follow_up_draft ? (
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
                          }}
                        >
                          {jobDetail.follow_up_draft}
                        </div>
                      ) : (
                        <div style={{ padding: '20px', color: '#94A3B8', fontSize: '13px' }}>
                          Draf follow-up otomatis siap digunakan setelah lowongan disubmit.
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 5: MATRIKS EVALUASI A-H LENGKAP */}
                  {activeTab === 'report' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      <div style={{ padding: '14px', borderRadius: '10px', background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                        <div style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', marginBottom: '4px' }}>
                          A - ROLE SUMMARY & CORE MISSION
                        </div>
                        <div style={{ fontSize: '13px', color: '#1E293B', lineHeight: 1.5 }}>
                          {jobDetail.evaluation_report?.A_role_summary || 'Tidak ada data'}
                        </div>
                      </div>

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
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
