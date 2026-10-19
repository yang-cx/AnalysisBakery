FROM gitlab-registry.cern.ch/atlas/statanalysis:0-4

USER root

ARG NODE_VERSION=22.16.0
ARG CODEX_VERSION=0.142.5
ARG RIPGREP_VERSION=15.1.0

ENV PATH="/opt/node/bin:${PATH}"

RUN set -eux; \
    arch="$(uname -m)"; \
    case "$arch" in \
      x86_64) node_arch="x64"; rg_target="x86_64-unknown-linux-musl" ;; \
      *) echo "Unsupported architecture for preinstalled agent tools: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${node_arch}.tar.xz" -o /tmp/node.tar.xz; \
    mkdir -p /opt/node; \
    tar -xJf /tmp/node.tar.xz -C /opt/node --strip-components=1; \
    npm install -g "@openai/codex@${CODEX_VERSION}"; \
    curl -fsSL "https://github.com/BurntSushi/ripgrep/releases/download/${RIPGREP_VERSION}/ripgrep-${RIPGREP_VERSION}-${rg_target}.tar.gz" -o /tmp/ripgrep.tar.gz; \
    tar -xzf /tmp/ripgrep.tar.gz -C /tmp; \
    cp "/tmp/ripgrep-${RIPGREP_VERSION}-${rg_target}/rg" /usr/local/bin/rg; \
    chmod 0755 /usr/local/bin/rg; \
    node --version; \
    npm --version; \
    codex --version; \
    rg --version; \
    rm -rf /tmp/node.tar.xz /tmp/ripgrep.tar.gz "/tmp/ripgrep-${RIPGREP_VERSION}-${rg_target}" /root/.npm
