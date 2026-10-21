#!/bin/bash
set -e

echo "📥 Menarik update terbaru dari GitHub..."
git pull origin main

echo "📦 Memeriksa dependensi Python..."
./venv/bin/pip install -r requirements.txt -q

# Cek apakah ada perubahan di folder web
if git diff --name-only HEAD@{1} HEAD | grep -q "^web/"; then
    echo "🎨 Terdeteksi perubahan pada visualizer, melakukan build frontend..."
    cd web
    npm install --prefer-offline --no-audit
    npm run build
    cd ..
else
    echo "⏩ Tidak ada perubahan di frontend, lewati build."
fi

echo "🔄 Me-restart worker dan API server..."
supervisorctl restart punggawa-server punggawa-worker

echo "✅ Deployment selesai! Semua sistem terupdate."