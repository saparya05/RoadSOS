#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  RoadSOS – Launcher  (fully offline)
#
#  Usage:
#    bash run.sh              → Streamlit only  (no API server needed)
#    bash run.sh full         → FastAPI + Streamlit
#    bash run.sh api          → FastAPI only
#    bash run.sh install      → pip install all dependencies
#    bash run.sh download-stt → download Whisper tiny model for offline STT
# ─────────────────────────────────────────────────────────────
set -e

RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'
CYN='\033[0;36m'; BLD='\033[1m'; NC='\033[0m'

MODE=${1:-streamlit}

banner(){
  echo -e "${RED}${BLD}"
  echo "  ██████╗  ██████╗  █████╗ ██████╗ ███████╗ ██████╗ ███████╗"
  echo "  ██╔══██╗██╔═══██╗██╔══██╗██╔══██╗██╔════╝██╔═══██╗██╔════╝"
  echo "  ██████╔╝██║   ██║███████║██║  ██║███████╗██║   ██║███████╗"
  echo "  ██╔══██╗██║   ██║██╔══██║██║  ██║╚════██║██║   ██║╚════██║"
  echo "  ██║  ██║╚██████╔╝██║  ██║██████╔╝███████║╚██████╔╝███████║"
  echo "  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝ ╚══════╝"
  echo -e "${NC}${CYN}  🚨 AI Emergency Assistant · Works 100% Offline${NC}"
  echo ""
}

if [ "$MODE" = "install" ]; then
  banner
  echo -e "${YEL}Installing dependencies...${NC}"
  pip install -r requirements.txt
  echo -e "${GRN}✅ Done!${NC}"
  echo ""
  echo -e "Run the app:  ${CYN}bash run.sh${NC}"
  exit 0
fi

if [ "$MODE" = "download-stt" ]; then
  banner
  echo -e "${YEL}Downloading Whisper tiny model for offline speech-to-text...${NC}"
  python -c "import whisper; whisper.load_model('tiny'); print('✅ Whisper tiny model cached')"
  exit 0
fi

banner

if [ "$MODE" = "api" ]; then
  echo -e "${GRN}▶ FastAPI backend → ${CYN}http://localhost:8000${NC}"
  echo -e "   API docs:  ${CYN}http://localhost:8000/docs${NC}"
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
  exit 0
fi

if [ "$MODE" = "full" ]; then
  echo -e "${GRN}▶ Full Stack${NC}"
  echo -e "   Backend:   ${CYN}http://localhost:8000${NC}"
  echo -e "   Frontend:  ${CYN}http://localhost:8501${NC}"
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
  API_PID=$!
  sleep 2
  streamlit run frontend/app.py \
    --server.port 8501 \
    --theme.base dark \
    --theme.primaryColor "#E53E3E" \
    --theme.backgroundColor "#0D0D14" \
    --theme.secondaryBackgroundColor "#111118" \
    --theme.textColor "#ECECF1"
  kill $API_PID 2>/dev/null
  exit 0
fi

# Default: Streamlit only (embedded mode, no separate API needed)
echo -e "${GRN}▶ Streamlit (embedded offline mode)${NC}"
echo -e "   URL: ${CYN}http://localhost:8501${NC}"
echo -e "   Mode: ${YEL}No internet required${NC}"
echo ""
streamlit run frontend/app.py \
  --server.port 8501 \
  --theme.base dark \
  --theme.primaryColor "#E53E3E" \
  --theme.backgroundColor "#0D0D14" \
  --theme.secondaryBackgroundColor "#111118" \
  --theme.textColor "#ECECF1"
