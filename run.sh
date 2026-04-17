#!/bin/bash
# Read the first Replit public domain from the REPLIT_DOMAINS environment variable.
# This tells Streamlit's client JavaScript the correct public address for WebSocket.
DOMAIN=$(echo "$REPLIT_DOMAINS" | cut -d',' -f1)

# Run Streamlit with the public domain so WebSocket connections work through Replit's proxy.
streamlit run app.py \
  --server.port 5000 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --browser.serverAddress "$DOMAIN" \
  --browser.serverPort 5000 \
  --browser.gatherUsageStats false
