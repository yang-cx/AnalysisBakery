#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
REPO_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd -P)

IMAGE="${IMAGE:-gitlab-registry.cern.ch/atlas/statanalysis:0-4}"
PLATFORM="${PLATFORM:-linux/amd64}"
SKIP_PREFLIGHT="${SKIP_PREFLIGHT:-0}"
CONFIG="/workdir/hyy/ntuple_hyy_config.config"

usage() {
  cat <<'EOF'
Usage:
  ./build_hyy_histograms.sh

Environment:
  IMAGE=gitlab-registry.cern.ch/atlas/statanalysis:0-4
  PLATFORM=linux/amd64
  SKIP_PREFLIGHT=0|1

This runs:
  trex-fitter n /workdir/hyy/ntuple_hyy_config.config

Container mounts:
  ../datasets   -> /datasets:ro
  ../histograms -> /workdir
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

missing_input=0

require_file() {
  rf_label=$1
  rf_file=$2

  if [ ! -s "$rf_file" ]; then
    if [ -s "${rf_file}.part" ]; then
      echo "incomplete ${rf_label}: ${rf_file}.part" >&2
    else
      echo "missing ${rf_label}: ${rf_file}" >&2
    fi
    missing_input=1
  fi
}

require_url_list_files() {
  rul_label=$1
  rul_target_dir=$2
  rul_url_file=$3

  [ -f "$rul_url_file" ] || die "missing URL list: $rul_url_file"

  while IFS= read -r rul_url; do
    case "$rul_url" in
      ""|\#*) continue ;;
    esac
    rul_filename=${rul_url##*/}
    require_file "$rul_label $rul_filename" "${rul_target_dir}/${rul_filename}"
  done < "$rul_url_file"
}

preflight_inputs() {
  [ -d "${REPO_ROOT}/datasets/GAMGAM_DATA" ] || die "missing datasets/GAMGAM_DATA"
  [ -d "${REPO_ROOT}/datasets/GAMGAM_MC" ] || die "missing datasets/GAMGAM_MC"
  [ -f "${SCRIPT_DIR}/hyy/ntuple_hyy_config.config" ] || die "missing hyy/ntuple_hyy_config.config"

  require_url_list_files "DATA" "${REPO_ROOT}/datasets/GAMGAM_DATA" "${REPO_ROOT}/datasets/GAMGAM_DATA_urls.txt"

  require_file "diphoton MC 364350" "${REPO_ROOT}/datasets/GAMGAM_MC/ODEO_FEB2025_v0_GamGam_mc_364350.Sherpa_224_NNPDF30NNLO_Diphoton_myy_0_50.GamGam.root"
  require_file "diphoton MC 364351" "${REPO_ROOT}/datasets/GAMGAM_MC/ODEO_FEB2025_v0_GamGam_mc_364351.Sherpa_224_NNPDF30NNLO_Diphoton_myy_50_90.GamGam.root"
  require_file "diphoton MC 364352" "${REPO_ROOT}/datasets/GAMGAM_MC/ODEO_FEB2025_v0_GamGam_mc_364352.Sherpa_224_NNPDF30NNLO_Diphoton_myy_90_175.GamGam.root"
  require_file "diphoton MC 364353" "${REPO_ROOT}/datasets/GAMGAM_MC/ODEO_FEB2025_v0_GamGam_mc_364353.Sherpa_224_NNPDF30NNLO_Diphoton_myy_175_2000.GamGam.root"
  require_file "ggH MC" "${REPO_ROOT}/datasets/GAMGAM_MC/ODEO_FEB2025_v0_GamGam_mc_343981.PowhegPythia8EvtGen_NNLOPS_nnlo_30_ggH125_gamgam.GamGam.root"
  require_file "VBFH MC" "${REPO_ROOT}/datasets/GAMGAM_MC/ODEO_FEB2025_v0_GamGam_mc_346214.PowhegPy8EG_NNPDF30_AZNLOCTEQ6L1_VBFH125_gamgam.GamGam.root"
  require_file "WH minus MC" "${REPO_ROOT}/datasets/GAMGAM_MC/ODEO_FEB2025_v0_GamGam_mc_345317.PowhegPythia8EvtGen_NNPDF30_AZNLO_WmH125J_Hyy_Wincl_MINLO.GamGam.root"
  require_file "WH plus MC" "${REPO_ROOT}/datasets/GAMGAM_MC/ODEO_FEB2025_v0_GamGam_mc_345318.PowhegPythia8EvtGen_NNPDF30_AZNLO_WpH125J_Hyy_Wincl_MINLO.GamGam.root"
  require_file "ZH MC" "${REPO_ROOT}/datasets/GAMGAM_MC/ODEO_FEB2025_v0_GamGam_mc_345319.PowhegPythia8EvtGen_NNPDF30_AZNLO_ZH125J_Hyy_Zincl_MINLO.GamGam.root"
  require_file "ttH MC" "${REPO_ROOT}/datasets/GAMGAM_MC/ODEO_FEB2025_v0_GamGam_mc_346525.PowhegPythia8EvtGen_A14NNPDF23_NNPDF30ME_ttH125_gamgam.GamGam.root"

  if [ "$missing_input" -ne 0 ]; then
    die "required ntuple inputs are missing; run datasets/download_gamgam.sh first"
  fi
}

main() {
  case "${1:-}" in
    -h|--help)
      usage
      exit 0
      ;;
    "")
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac

  command -v docker >/dev/null 2>&1 || die "docker not found in PATH"

  case "$SKIP_PREFLIGHT" in
    0) preflight_inputs ;;
    1) ;;
    *) die "SKIP_PREFLIGHT must be 0 or 1" ;;
  esac

  docker run --rm --platform "$PLATFORM" \
    -v "${REPO_ROOT}/datasets:/datasets:ro" \
    -v "${REPO_ROOT}/histograms:/workdir" \
    --workdir /workdir \
    --entrypoint bash \
    "$IMAGE" \
    -lc '
      set -e
      for gcc_setup in /opt/lcg/gcc/13.1.0*/x86_64-*/setup.sh; do
        if [ -f "$gcc_setup" ]; then
          . "$gcc_setup"
          break
        fi
      done
      SETUP=/usr/StatAnalysis/0.4.4/InstallArea/x86_64-el9-gcc13-opt/setup.sh
      if [ -f "$SETUP" ]; then
        . "$SETUP"
      fi
      trex-fitter n '"$CONFIG"'
    '
}

main "$@"
