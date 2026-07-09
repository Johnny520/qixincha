#!/usr/bin/env bash
# 企信查 APK 本地一键打包脚本（Linux / macOS / WSL）
set -e
echo "[企信查] 开始打包 APK ..."
python3 -m pip install --upgrade pip
pip install buildozer cython
buildozer android debug --allow-root
echo "[企信查] 打包完成，APK 位于 bin/ 目录"
ls -lh bin/*.apk 2>/dev/null || echo "未生成 APK，请查看上方日志"
