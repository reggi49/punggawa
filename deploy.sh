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

echo "🔄 Menentukan jalur supervisorctl..."
if command -v supervisorctl >/dev/null 2>&1; then
    SUPERVISOR_CMD="supervisorctl"
elif [ -x "/www/server/panel/pyenv/bin/supervisorctl" ]; then
    SUPERVISOR_CMD="/www/server/panel/pyenv/bin/supervisorctl"
else
    echo "❌ Error: supervisorctl tidak ditemukan di sistem maupun di aaPanel pyenv!"
    exit 1
fi

echo "🔄 Me-restart worker dan API server via $SUPERVISOR_CMD..."
$SUPERVISOR_CMD restart punggawa-server:* punggawa-worker:*

echo "✅ Deployment selesai! Semua sistem terupdate."