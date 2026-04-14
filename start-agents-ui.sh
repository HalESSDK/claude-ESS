#!/bin/bash
# Start Claude Code Agents UI dashboard
cd /home/victor/claude-code-agents-ui
echo "Starter Agents UI på http://100.119.124.107:3030"
npx nuxt dev --port 3030 --host 0.0.0.0
