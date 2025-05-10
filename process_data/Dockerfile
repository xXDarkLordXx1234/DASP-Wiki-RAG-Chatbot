# ----------------------------------
# Stage 1: Build rust-based wheel(s)
# ----------------------------------
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime as build

# Add Rust
RUN apt-get update && apt-get install -y curl build-essential gcc \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Add any additional steps to set up Rust in PATH here...
ENV PATH="/root/.cargo/bin:${PATH}"

# Set the working directory
WORKDIR /code

# Create and activate virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Maturin
RUN pip3 install maturin

# Copy project files
COPY ./src/rust_python_module ./src/rust_python_module

# Build the Rust library as a Python extension
WORKDIR /code/src/rust_python_module
RUN maturin build --release
# ----------------------------------
# Stage 2: Create final CUDA image
# ----------------------------------
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

# Set POLARS_SKIP_CPU_CHECK
ENV POLARS_SKIP_CPU_CHECK=1

WORKDIR /code

# Install runtime dependencies (if any required)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the previously built wheels from "build" stage
COPY --from=build /code/src/rust_python_module/target/wheels /code/wheels

# Copy and install requirements
COPY ./requirements.txt ./
RUN pip install --no-cache-dir /code/wheels/*.whl \
    && pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu118

# Copy the remaining Python application code
COPY ./src ./src

WORKDIR /code/src

# Set default command
CMD ["python", "main.py"]
    