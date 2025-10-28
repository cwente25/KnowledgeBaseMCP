#!/bin/bash
cd /home/user/KnowledgeBaseMCP
export PYTHONPATH=/home/user/KnowledgeBaseMCP/src
export KNOWLEDGE_BASE_PATH=/home/user/knowledge-base
/usr/local/bin/python -m knowledge_base_mcp.server
