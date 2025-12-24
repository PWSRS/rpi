# 1. ESCOLHE A IMAGEM BASE
FROM python:3.12-slim

# 2. INSTALAÇÃO DE FERRAMENTAS E BIBLIOTECAS ESSENCIAIS (WEASYPRINT)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    pkg-config \
    git \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libpango1.0-dev \
    libcairo2-dev \
    libgdk-pixbuf-xlib-2.0-dev \
    libjpeg-dev \
    zlib1g-dev \
    libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# 3. DEFINIÇÃO DE VARIÁVEIS DO POETRY (Instalação no sistema do contêiner)
ENV POETRY_HOME="/opt/poetry"
# Estas duas linhas instruem o Poetry a NÃO criar o .venv na pasta mapeada
ENV POETRY_VIRTUALENVS_IN_PROJECT=false 
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PATH="$POETRY_HOME/bin:$PATH"

# 4. DIRETÓRIO DE TRABALHO
WORKDIR /app

# 5. INSTALAÇÃO DO POETRY E DEPENDÊNCIAS
COPY pyproject.toml poetry.lock /app/

# Instala o Poetry e as dependências (diretamente no PATH do sistema)
RUN curl -sSL https://install.python-poetry.org | python - \
    && poetry install --only main --no-root

# 6. COPIA O CÓDIGO DO PROJETO (ESSENCIAL!)
COPY . /app/

# 7. EXECUÇÃO
EXPOSE 8000
# Usa 'poetry run' para garantir que as dependências sejam encontradas
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]