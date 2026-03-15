# FastenRun CLI examples

## Python: quick bounded run

```bash
fasten-run run \
  --image python:3.12-slim \
  --timeout-sec 30 \
  --memory 512m \
  --cpus 1.0 \
  -- \
  python -c 'print(2 + 2)'
```

## Rust: compile and run

```bash
fasten-run run \
  --image rust:1.76 \
  --timeout-sec 180 \
  --memory 1g \
  --cpus 1.0 \
  -- \
  bash -lc 'cat <<"RS" > main.rs
fn main() { println!("{}", 2 + 2); }
RS
rustc main.rs -O -o app && ./app'
```

## pytest + coverage JSON for a mounted project

```bash
fasten-run run \
  --image python:3.12-slim \
  --timeout-sec 180 \
  --memory 1g \
  --cpus 1.0 \
  --mount "$PWD:/workspace:rw" \
  --workdir /workspace \
  -- \
  bash -lc 'python -m pip install --quiet pytest coverage && coverage run -m pytest -q && coverage json -o -'
```

## Read-only filesystem + environment variable

```bash
fasten-run run \
  --image alpine:3.20 \
  --read-only-root-fs \
  --env HELLO=world \
  -- \
  sh -lc 'echo "$HELLO"'
```
