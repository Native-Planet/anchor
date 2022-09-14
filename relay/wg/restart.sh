#!/bin/bash
echo "Restarting WG interface..."
wg-quick down wg0
wg-quick up wg0