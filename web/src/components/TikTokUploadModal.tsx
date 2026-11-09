import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  UploadCloud,
  X,
  CheckCircle2,
  AlertCircle,
  FileVideo,
  ShieldCheck,
  Lock,
  Layers,
  Sparkles,
  ShoppingBag,
  BookOpen,
  RefreshCw,
  Clock,
  Trash2,
} from 'lucide-react';

interface QueueItem {
  filename: string;
  size_bytes: number;
  size_mb: number;
  modified_at: string;
  has_caption: boolean;
  caption_preview: string | null;
}

interface TikTokUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiBaseUrl?: string;
  adminPassword?: string;
}

export const TikTokUploadModal: React.FC<TikTokUploadModalProps> = ({
  isOpen,
  onClose,
  apiBaseUrl = '',
  adminPassword = '',
}) => {
  const [targetAccount, setTargetAccount] = useState<'berdongeng' | 'kedaidaily' | 'kittengaul'>('berdongeng');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [caption, setCaption] = useState('');
  const [inputPassword, setInputPassword] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Tab: 'upload' vs 'queue'
  const [activeTab, setActiveTab] = useState<'upload' | 'queue'>('upload');
  const [queueData, setQueueData] = useState<{
    berdongeng: QueueItem[];
    kedaidaily: QueueItem[];
    kittengaul: QueueItem[];
  }>({
    berdongeng: [],
    kedaidaily: [],
    kittengaul: [],
  });
  const [loadingQueue, setLoadingQueue] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Fetch current queue when modal opens or tab changes
  const fetchQueue = async () => {
    setLoadingQueue(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/tiktok/queue`);
      if (res.ok) {
        const data = await res.json();
        setQueueData(data.queue || { berdongeng: [], kedaidaily: [], kittengaul: [] });
      }
    } catch (err) {
      console.warn('Gagal memuat antrean video:', err);
    } finally {
      setLoadingQueue(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchQueue();
      setErrorMessage(null);
      setUploadSuccess(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    setErrorMessage(null);
    setUploadSuccess(null);

    const validExtensions = ['.mp4', '.mov', '.webm'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!validExtensions.includes(ext)) {
      setErrorMessage(`Format file ${ext} ditolak. Hanya video MP4, MOV, atau WebM yang diizinkan.`);
      return;
    }

    // Max 250 MB
    if (file.size > 250 * 1024 * 1024) {
      setErrorMessage(`Ukuran file (${(file.size / (1024 * 1024)).toFixed(1)} MB) melebihi batas maksimum 250 MB.`);
      return;
    }

    setSelectedFile(file);
  };

  const handleUploadSubmit = () => {
    if (!selectedFile) {
      setErrorMessage('Silakan pilih file video MP4/MOV terlebih dahulu.');
      return;
    }

    // Resolusi autentikasi
    const storedToken = localStorage.getItem('punggawa_auth_token');
    const effectivePassword = inputPassword || adminPassword;

    if (!storedToken && !effectivePassword) {
      setErrorMessage('Sistem memerlukan otentikasi pengelola. Masukkan password pengelola.');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setErrorMessage(null);
    setUploadSuccess(null);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('account', targetAccount);
    if (title.trim()) formData.append('title', title.trim());
    if (caption.trim()) formData.append('caption', caption.trim());

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${apiBaseUrl}/api/tiktok/upload`);

    if (storedToken) {
      xhr.setRequestHeader('Authorization', `Bearer ${storedToken}`);
    }
    if (effectivePassword) {
      xhr.setRequestHeader('X-Admin-Password', effectivePassword);
    }

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        setUploadProgress(percent);
      }
    };

    xhr.onload = () => {
      setUploading(false);
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const res = JSON.parse(xhr.responseText);
          setUploadSuccess(
            `Video berhasil diunggah ke antrean '${targetAccount}'! (${res.size_mb} MB). Siap dijadwalkan oleh Kang Sosmed.`
          );
          setSelectedFile(null);
          setTitle('');
          setCaption('');
          if (fileInputRef.current) fileInputRef.current.value = '';
          fetchQueue();
        } catch {
          setUploadSuccess('Video berhasil diunggah!');
          fetchQueue();
        }
      } else {
        try {
          const errData = JSON.parse(xhr.responseText);
          setErrorMessage(errData.detail || `Upload gagal (Status ${xhr.status})`);
        } catch {
          setErrorMessage(`Terjadi kesalahan server saat mengunggah (Status ${xhr.status}).`);
        }
      }
    };

    xhr.onerror = () => {
      setUploading(false);
      setErrorMessage('Koneksi jaringan terputus saat mengunggah video.');
    };

    xhr.send(formData);
  };

  const totalVideos =
    (queueData.berdongeng?.length || 0) +
    (queueData.kedaidaily?.length || 0) +
    (queueData.kittengaul?.length || 0);

  return createPortal(
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: 'rgba(15, 23, 42, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        animation: 'fadeIn 0.2s ease-out',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !uploading) onClose();
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '720px',
          maxHeight: '90vh',
          background: 'linear-gradient(135deg, #FAF8F5 0%, #F3EFEA 100%)',
          borderRadius: '20px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.6)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          color: '#1E293B',
          fontFamily: 'system-ui, -apple-system, sans-serif',
        }}
      >
        {/* Header Bar */}
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid rgba(226, 232, 240, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(255, 255, 255, 0.7)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #0284C7 0%, #0369A1 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                boxShadow: '0 4px 10px rgba(2, 132, 199, 0.25)',
              }}
            >
              <UploadCloud size={20} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '17px', fontWeight: 700, color: '#0F172A' }}>
                Unggah Video Antrean Sosmed
              </h2>
              <div style={{ fontSize: '11px', color: '#64748B', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>Kang Sosmed Queue Dispatcher (TikTok & IG)</span>
                <span>•</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', color: '#059669' }}>
                  <ShieldCheck size={12} /> Secure Gateway
                </span>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => setActiveTab(activeTab === 'upload' ? 'queue' : 'upload')}
              style={{
                background: activeTab === 'queue' ? '#0F172A' : 'rgba(241, 245, 249, 0.9)',
                color: activeTab === 'queue' ? '#FFFFFF' : '#334155',
                border: '1px solid rgba(203, 213, 225, 0.8)',
                borderRadius: '8px',
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                transition: 'all 0.15s ease',
              }}
            >
              <Layers size={13} />
              <span>Antrean ({totalVideos})</span>
            </button>
            <button
              onClick={onClose}
              disabled={uploading}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#64748B',
                cursor: uploading ? 'not-allowed' : 'pointer',
                padding: '6px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
          {activeTab === 'queue' ? (
            /* TAB: LIHAT ANTREAN AKTIF */
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: '#334155' }}>
                  Daftar Antrean Video di Server ({totalVideos} video)
                </h3>
                <button
                  onClick={fetchQueue}
                  disabled={loadingQueue}
                  style={{
                    background: 'none',
                    border: '1px solid #CBD5E1',
                    borderRadius: '6px',
                    padding: '4px 8px',
                    fontSize: '11px',
                    color: '#475569',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    cursor: 'pointer',
                  }}
                >
                  <RefreshCw size={11} className={loadingQueue ? 'spin' : ''} />
                  <span>Segarkan</span>
                </button>
              </div>

              {/* Akun Berdongeng Queue */}
              <div style={{ marginBottom: '18px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <BookOpen size={14} color="#0284C7" />
                  <span style={{ fontSize: '13px', fontWeight: 700, color: '#0369A1' }}>
                    DongengIDN (@berdongeng) — {queueData.berdongeng.length} video
                  </span>
                  <span style={{ fontSize: '10px', background: '#E0F2FE', color: '#0284C7', padding: '2px 6px', borderRadius: '4px' }}>
                    Auto-Cover 1.0s
                  </span>
                </div>
                {queueData.berdongeng.length === 0 ? (
                  <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: '8px', fontSize: '12px', color: '#94A3B8', textAlign: 'center' }}>
                    Antrean berdongeng kosong.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {queueData.berdongeng.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '10px 12px',
                          background: '#FFFFFF',
                          borderRadius: '8px',
                          border: '1px solid #E2E8F0',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: '12px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <FileVideo size={16} color="#0284C7" />
                          <div>
                            <div style={{ fontWeight: 600, color: '#1E293B' }}>{item.filename}</div>
                            {item.caption_preview && (
                              <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>
                                "{item.caption_preview}..."
                              </div>
                            )}
                          </div>
                        </div>
                        <span style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>{item.size_mb} MB</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Akun Kedai Daily Queue */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <ShoppingBag size={14} color="#D97706" />
                  <span style={{ fontSize: '13px', fontWeight: 700, color: '#B45309' }}>
                    Kedai Daily Nurul (@nurulzulaikhha) — {queueData.kedaidaily.length} video
                  </span>
                  <span style={{ fontSize: '10px', background: '#FEF3C7', color: '#D97706', padding: '2px 6px', borderRadius: '4px' }}>
                    Draf Keranjang Kuning
                  </span>
                </div>
                {queueData.kedaidaily.length === 0 ? (
                  <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: '8px', fontSize: '12px', color: '#94A3B8', textAlign: 'center' }}>
                    Antrean kedaidaily kosong.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {queueData.kedaidaily.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '10px 12px',
                          background: '#FFFFFF',
                          borderRadius: '8px',
                          border: '1px solid #E2E8F0',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: '12px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <FileVideo size={16} color="#D97706" />
                          <div>
                            <div style={{ fontWeight: 600, color: '#1E293B' }}>{item.filename}</div>
                            {item.caption_preview && (
                              <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>
                                "{item.caption_preview}..."
                              </div>
                            )}
                          </div>
                        </div>
                        <span style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>{item.size_mb} MB</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Akun Kitten Gaul Queue */}
              <div style={{ marginTop: '18px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <Sparkles size={14} color="#E11D48" />
                  <span style={{ fontSize: '13px', fontWeight: 700, color: '#BE123C' }}>
                    Kitten Gaul (@kittengaul) — {queueData.kittengaul?.length || 0} video
                  </span>
                  <span style={{ fontSize: '10px', background: '#FFE4E6', color: '#E11D48', padding: '2px 6px', borderRadius: '4px' }}>
                    Instagram Reels
                  </span>
                </div>
                {!queueData.kittengaul || queueData.kittengaul.length === 0 ? (
                  <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: '8px', fontSize: '12px', color: '#94A3B8', textAlign: 'center' }}>
                    Antrean kittengaul kosong.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {queueData.kittengaul.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '10px 12px',
                          background: '#FFFFFF',
                          borderRadius: '8px',
                          border: '1px solid #E2E8F0',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: '12px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <FileVideo size={16} color="#E11D48" />
                          <div>
                            <div style={{ fontWeight: 600, color: '#1E293B' }}>{item.filename}</div>
                            {item.caption_preview && (
                              <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>
                                "{item.caption_preview}..."
                              </div>
                            )}
                          </div>
                        </div>
                        <span style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>{item.size_mb} MB</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* TAB: UPLOAD FORM */
            <div>
              {/* Alert Feedback */}
              {errorMessage && (
                <div
                  style={{
                    padding: '10px 14px',
                    borderRadius: '8px',
                    background: '#FEF2F2',
                    border: '1px solid #FCA5A5',
                    color: '#991B1B',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '14px',
                  }}
                >
                  <AlertCircle size={16} style={{ flexShrink: 0 }} />
                  <span>{errorMessage}</span>
                </div>
              )}

              {uploadSuccess && (
                <div
                  style={{
                    padding: '10px 14px',
                    borderRadius: '8px',
                    background: '#F0FDF4',
                    border: '1px solid #86EFAC',
                    color: '#166534',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '14px',
                  }}
                >
                  <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
                  <span>{uploadSuccess}</span>
                </div>
              )}

              {/* 1. Target Account Selector */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '8px' }}>
                  PILIH AKUN TUJUAN (TIKTOK & INSTAGRAM)
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
                  {/* Option: Berdongeng */}
                  <div
                    onClick={() => setTargetAccount('berdongeng')}
                    style={{
                      padding: '12px',
                      borderRadius: '12px',
                      border: targetAccount === 'berdongeng' ? '2px solid #0284C7' : '1px solid #CBD5E1',
                      background: targetAccount === 'berdongeng' ? '#F0F9FF' : '#FFFFFF',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <BookOpen size={16} color="#0284C7" />
                        <span style={{ fontSize: '13px', fontWeight: 700, color: '#0F172A' }}>DongengIDN</span>
                      </div>
                      <span style={{ fontSize: '10px', background: '#BAE6FD', color: '#0369A1', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                        @berdongeng
                      </span>
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748B', lineHeight: '1.4' }}>
                      TikTok • Cover 1.0s otomatis • Draf Inbox HP
                    </div>
                  </div>

                  {/* Option: Kedai Daily */}
                  <div
                    onClick={() => setTargetAccount('kedaidaily')}
                    style={{
                      padding: '12px',
                      borderRadius: '12px',
                      border: targetAccount === 'kedaidaily' ? '2px solid #D97706' : '1px solid #CBD5E1',
                      background: targetAccount === 'kedaidaily' ? '#FFFBEB' : '#FFFFFF',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <ShoppingBag size={16} color="#D97706" />
                        <span style={{ fontSize: '13px', fontWeight: 700, color: '#0F172A' }}>Kedai Daily</span>
                      </div>
                      <span style={{ fontSize: '10px', background: '#FED7AA', color: '#9A3412', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                        Affiliate / Toko
                      </span>
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748B', lineHeight: '1.4' }}>
                      TikTok Shop • Draf Inbox HP (Keranjang Kuning)
                    </div>
                  </div>

                  {/* Option: Kitten Gaul */}
                  <div
                    onClick={() => setTargetAccount('kittengaul')}
                    style={{
                      padding: '12px',
                      borderRadius: '12px',
                      border: targetAccount === 'kittengaul' ? '2px solid #E11D48' : '1px solid #CBD5E1',
                      background: targetAccount === 'kittengaul' ? '#FFF1F2' : '#FFFFFF',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Sparkles size={16} color="#E11D48" />
                        <span style={{ fontSize: '13px', fontWeight: 700, color: '#0F172A' }}>Kitten Gaul</span>
                      </div>
                      <span style={{ fontSize: '10px', background: '#FFE4E6', color: '#BE123C', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                        @kittengaul
                      </span>
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748B', lineHeight: '1.4' }}>
                      Instagram Reels & Video • Otomatis via Postiz
                    </div>
                  </div>
                </div>
              </div>

              {/* 2. Drag & Drop File Zone */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '8px' }}>
                  FILE VIDEO (MP4, MOV, WEBM — MAKS 250 MB)
                </label>
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleFileDrop}
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    border: '2px dashed #94A3B8',
                    borderRadius: '14px',
                    padding: selectedFile ? '16px' : '28px 16px',
                    textAlign: 'center',
                    background: selectedFile ? '#F8FAFC' : '#FFFFFF',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/mp4,video/quicktime,video/webm"
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      if (e.target.files && e.target.files.length > 0) {
                        validateAndSetFile(e.target.files[0]);
                      }
                    }}
                  />

                  {selectedFile ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', textAlign: 'left' }}>
                        <div
                          style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '8px',
                            background: '#E2E8F0',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#0284C7',
                          }}
                        >
                          <FileVideo size={24} />
                        </div>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 700, color: '#0F172A' }}>{selectedFile.name}</div>
                          <div style={{ fontSize: '11px', color: '#64748B' }}>
                            {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • {selectedFile.type || 'video/mp4'}
                          </div>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedFile(null);
                          if (fileInputRef.current) fileInputRef.current.value = '';
                        }}
                        style={{
                          background: '#FEE2E2',
                          border: 'none',
                          color: '#DC2626',
                          borderRadius: '6px',
                          padding: '6px',
                          cursor: 'pointer',
                        }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ) : (
                    <div>
                      <UploadCloud size={32} color="#64748B" style={{ margin: '0 auto 8px auto' }} />
                      <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>
                        Klik untuk memilih video atau seret file ke sini
                      </div>
                      <div style={{ fontSize: '11px', color: '#94A3B8', marginTop: '4px' }}>
                        Resolusi 9:16 vertikal (1080x1920) disarankan untuk TikTok
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 3. Title & Caption Inputs */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                    Judul Video (Opsional - Maks 90 Karakter)
                  </label>
                  <input
                    type="text"
                    maxLength={90}
                    placeholder={
                      targetAccount === 'kittengaul'
                        ? 'Kitten Gaul (Otomatis)'
                        : targetAccount === 'berdongeng'
                        ? 'Contoh: Kisah Legenda Malin Kundang #1'
                        : 'Contoh: Promo Kalisha Saira Hijab Instan'
                    }
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '9px 12px',
                      borderRadius: '8px',
                      border: '1px solid #CBD5E1',
                      fontSize: '13px',
                      background: '#FFFFFF',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569' }}>
                      Caption & Hashtags (Opsional)
                    </label>
                    {targetAccount === 'kittengaul' && (
                      <span style={{ fontSize: '11px', color: '#E11D48', fontWeight: 600 }}>
                        Preset Otomatis: #sakura #fyp #viral #sakuraschoolsimulator
                      </span>
                    )}
                  </div>
                  <textarea
                    rows={3}
                    placeholder={
                      targetAccount === 'kittengaul'
                        ? '#sakura\n#fyp\n#viral\n#sakuraschoolsimulator'
                        : 'Tulis deskripsi dan hashtag di sini (otomatis disimpan ke file .txt pendamping)...'
                    }
                    value={caption}
                    onChange={(e) => setCaption(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '9px 12px',
                      borderRadius: '8px',
                      border: '1px solid #CBD5E1',
                      fontSize: '12px',
                      background: '#FFFFFF',
                      boxSizing: 'border-box',
                      resize: 'vertical',
                      fontFamily: 'inherit',
                    }}
                  />
                </div>
              </div>

              {/* 4. Password Security Input (Jika belum login) */}
              {!localStorage.getItem('punggawa_auth_token') && !adminPassword && (
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#B45309', marginBottom: '4px' }}>
                    Password Pengelola (Autentikasi Keamanan)
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type="password"
                      placeholder="Masukkan password admin pengelola..."
                      value={inputPassword}
                      onChange={(e) => setInputPassword(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '9px 12px 9px 34px',
                        borderRadius: '8px',
                        border: '1px solid #F59E0B',
                        fontSize: '13px',
                        background: '#FFFBEB',
                        boxSizing: 'border-box',
                      }}
                    />
                    <Lock size={15} color="#D97706" style={{ position: 'absolute', left: '10px', top: '11px' }} />
                  </div>
                </div>
              )}

              {/* Progress Bar during Upload */}
              {uploading && (
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#0284C7', fontWeight: 600, marginBottom: '6px' }}>
                    <span>Mengunggah video ke server...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: '#E2E8F0', borderRadius: '4px', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${uploadProgress}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, #0284C7 0%, #06B6D4 100%)',
                        transition: 'width 0.2s ease',
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        {activeTab === 'upload' && (
          <div
            style={{
              padding: '14px 24px',
              borderTop: '1px solid rgba(226, 232, 240, 0.8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(255, 255, 255, 0.7)',
            }}
          >
            <div style={{ fontSize: '11px', color: '#64748B', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ShieldCheck size={14} color="#059669" />
              <span>Proteksi Anti-Path Traversal & Magic Bytes Active</span>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={onClose}
                disabled={uploading}
                style={{
                  background: 'none',
                  border: '1px solid #CBD5E1',
                  borderRadius: '8px',
                  padding: '8px 16px',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: '#475569',
                  cursor: uploading ? 'not-allowed' : 'pointer',
                }}
              >
                Batal
              </button>

              <button
                type="button"
                onClick={handleUploadSubmit}
                disabled={uploading || !selectedFile}
                style={{
                  background: uploading || !selectedFile ? '#94A3B8' : 'linear-gradient(135deg, #0284C7 0%, #0369A1 100%)',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '8px 20px',
                  fontSize: '13px',
                  fontWeight: 700,
                  color: '#FFFFFF',
                  cursor: uploading || !selectedFile ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: uploading || !selectedFile ? 'none' : '0 4px 12px rgba(2, 132, 199, 0.3)',
                }}
              >
                {uploading ? (
                  <>
                    <RefreshCw size={14} className="spin" />
                    <span>Mengunggah ({uploadProgress}%)...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud size={15} />
                    <span>Unggah ke Antrean</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
};
