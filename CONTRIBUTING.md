# Contributing to ZifyVPN

Thanks for your interest in contributing!

## Development Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/Harsed11/ZifyVPN.git
   cd ZifyVPN
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   source venv/bin/activate  # Linux/macOS
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. Run tests:
   ```bash
   pytest
   ```

## Code Style

- Follow PEP 8
- Use `ruff` for linting: `ruff check .`
- Use `ruff format` for formatting: `ruff format .`
- Type hints are encouraged

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation only
- `test:` adding/fixing tests
- `refactor:` code restructuring

## Pull Request Process

1. Fork the repo and create a branch from `main`
2. Add tests for new functionality
3. Ensure all tests pass: `pytest`
4. Update CHANGELOG.md if applicable
5. Open a PR with a clear description

## Reporting Issues

- Use GitHub Issues
- Include: OS, Python version, steps to reproduce
- Attach logs from `data/logs/app.log` if relevant
