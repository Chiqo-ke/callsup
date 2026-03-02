# CALLSUP cutover command starter
# Run each block in the corresponding cloned repo directory.

# 1) callsup-specs
# git checkout main
# git pull
# git checkout -b cutover/specs-2026-03-01-baseline
# Copy files from: c:/Users/nyaga/Documents/callsup/consolidated/callsup-specs
# git add .
# git commit -m "feat(specs): baseline contracts + governance gates v0.1.0"
# git push -u origin cutover/specs-2026-03-01-baseline

# 2) callsup-platform
# git checkout main
# git pull
# git checkout -b cutover/platform-2026-03-01-baseline
# Copy files from: c:/Users/nyaga/Documents/callsup/consolidated/callsup-platform
# git add .
# git commit -m "feat(platform): baseline module implementation aligned to callsup-specs"
# git push -u origin cutover/platform-2026-03-01-baseline

# 3) callsup-audio-engine
# git checkout main
# git pull
# git checkout -b cutover/audio-engine-2026-03-01-baseline
# Copy files from: c:/Users/nyaga/Documents/callsup/consolidated/callsup-audio-engine
# git add .
# git commit -m "feat(audio-engine): baseline module implementation with schema-aligned transcript API"
# git push -u origin cutover/audio-engine-2026-03-01-baseline

# 4) callsup-intelligence-engine
# git checkout main
# git pull
# git checkout -b cutover/intelligence-engine-2026-03-01-baseline
# Copy files from: c:/Users/nyaga/Documents/callsup/consolidated/callsup-intelligence-engine
# git add .
# git commit -m "feat(intelligence-engine): baseline module implementation aligned to specs"
# git push -u origin cutover/intelligence-engine-2026-03-01-baseline

# 5) callsup-knowledge-ops
# git checkout main
# git pull
# git checkout -b cutover/knowledge-ops-2026-03-01-baseline
# Copy files from: c:/Users/nyaga/Documents/callsup/consolidated/callsup-knowledge-ops
# git add .
# git commit -m "feat(knowledge-ops): starter baseline scaffold aligned to specs"
# git push -u origin cutover/knowledge-ops-2026-03-01-baseline

# 6) integration repo
# git checkout main
# git pull
# git checkout -b cutover/integration-2026-03-01-baseline
# Add cross-module mock-first integration workflow/tests
# git add .
# git commit -m "chore(integration): baseline cross-module mocked integration"
# git push -u origin cutover/integration-2026-03-01-baseline
