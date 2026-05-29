#!/bin/bash
# ==============================================================
# SST ESOCIAL GOV — Push para GitHub
# ==============================================================
# COMO USAR:
#
# OPÇÃO 1 (mais simples) — Com Personal Access Token:
#   export GITHUB_TOKEN=ghp_seu_token_aqui
#   bash push_to_github.sh
#
# OPÇÃO 2 — Com SSH key já configurada:
#   git remote set-url origin git@github.com:taleshack-prog/-Governan-a-SST-eSocial.git
#   git push -u origin main
#
# OPÇÃO 3 — Via GitHub CLI:
#   gh auth login
#   git push -u origin main
# ==============================================================

set -e

REPO_URL="https://github.com/taleshack-prog/-Governan-a-SST-eSocial.git"
BRANCH="main"

if [ -n "$GITHUB_TOKEN" ]; then
  REMOTE_URL="https://${GITHUB_TOKEN}@github.com/taleshack-prog/-Governan-a-SST-eSocial.git"
  git remote set-url origin "$REMOTE_URL"
  echo "✅ Token configurado"
fi

echo "Fazendo push para: $REPO_URL"
git push -u origin $BRANCH

echo ""
echo "✅ Push concluído com sucesso!"
echo "🔗 https://github.com/taleshack-prog/-Governan-a-SST-eSocial"
